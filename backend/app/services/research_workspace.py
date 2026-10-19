"""Descriptive retrieval and immutable, source-bound hypothetical scenarios.

No scenario changes the registered source. Planning is explicit arithmetic;
retrieval is TF-IDF cosine, never clinical equivalence or an outcome forecast.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..schemas_v4 import ScenarioRequest
from . import pci_service
from .data_service import NUMERIC_FIELDS, json_clean, now
from .phase_service import predict_phase_for_dataset
from .prediction_service import predict

MAX_CACHE_ENTRIES = 3
MAX_INDEX_ROWS = 10_000
MAX_DOCUMENT_WORDS = 100
MAX_TEXT_FEATURES = 4000
MAX_HISTORY_ITEMS = 100
MAX_EVIDENCE_BYTES = 2 * 1024 * 1024
TEXT_FIELDS = ('title', 'brief_summary', 'eligibility_criteria')
SIMILARITY_METHOD = 'TF-IDF cosine similarity over title, brief summary and eligibility criteria; descriptive retrieval, not clinical equivalence.'

# All metadata SQL is constant and parameterized, including the table name.
CREATE_SCENARIOS = '''CREATE TABLE IF NOT EXISTS research_scenarios (
    id VARCHAR(80) PRIMARY KEY,
    dataset_id VARCHAR(80) NOT NULL,
    source_sha256 VARCHAR(64) NOT NULL,
    canonical_sha256 VARCHAR(64) NOT NULL,
    nct_id VARCHAR(100) NOT NULL,
    created_at VARCHAR(80) NOT NULL,
    payload TEXT NOT NULL
)'''
INSERT_SCENARIO = '''INSERT INTO research_scenarios
    (id,dataset_id,source_sha256,canonical_sha256,nct_id,created_at,payload)
    VALUES (:id,:dataset_id,:source_sha256,:canonical_sha256,:nct_id,:created_at,:payload)'''
SELECT_SCENARIOS = '''SELECT payload FROM research_scenarios
    WHERE dataset_id=:dataset_id AND source_sha256=:source_sha256
    AND canonical_sha256=:canonical_sha256 AND nct_id=:nct_id
    ORDER BY created_at DESC, id DESC LIMIT :limit'''
COUNT_SCENARIOS = '''SELECT COUNT(*) FROM research_scenarios
    WHERE dataset_id=:dataset_id AND source_sha256=:source_sha256
    AND canonical_sha256=:canonical_sha256 AND nct_id=:nct_id'''


class ResearchWorkspaceError(ValueError):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def evidence_digest(value: dict) -> str:
    """Digest the exact packet, excluding only its own top-level digest."""
    return hashlib.sha256(canonical_json({key: item for key, item in value.items() if key != 'evidence_sha256'}).encode('utf-8')).hexdigest()


def normalized_phase(value) -> str:
    """Normalize exact registry labels without merging different unknown phases."""
    from src.clinical_trial_intelligence.research import normalize_design_phase
    return normalize_design_phase(value)


def _pci(row: dict) -> dict:
    # The formula service owns the score/rounding; its detail API is additive
    # to the v3 tuple interface. Fall back for a deployment during upgrade.
    details = getattr(pci_service, 'calculate_pci_details', None)
    if details is not None:
        return json_clean(details(row))
    score, category, components = pci_service.calculate_pci(row)
    missing = [field for field in NUMERIC_FIELDS if _finite_number(row.get(field)) is None]
    return {'score': score, 'category': category, 'components': components,
            'methodology': pci_service.METHODOLOGY, 'missing_fields': missing}


def _finite_number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


@dataclass
class SourceSnapshot:
    dataset: dict
    frame: pd.DataFrame
    study: dict
    canonical_sha256: str

    @property
    def fingerprint(self):
        return (self.dataset['id'], self.dataset['sha256'], self.canonical_sha256)

    @property
    def provenance(self):
        return {'dataset_id': self.dataset['id'], 'sha256': self.dataset['sha256'],
                'canonical_sha256': self.canonical_sha256, 'source': self.dataset['source'],
                'is_fixture': self.dataset['is_fixture']}


class ResearchWorkspace:
    def __init__(self, registry):
        self.registry = registry
        self._cache_lock = threading.RLock()
        self._similar_cache = OrderedDict()
        registry._execute(CREATE_SCENARIOS)

    def snapshot(self, dataset_id: str, nct_id: str) -> SourceSnapshot:
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', dataset_id):
            raise ResearchWorkspaceError(422, 'Invalid dataset identifier.')
        if not isinstance(nct_id, str) or not 1 <= len(nct_id) <= 100:
            raise ResearchWorkspaceError(422, 'Invalid study identifier.')
        dataset = self.registry.get_dataset(dataset_id)
        if dataset is None:
            raise ResearchWorkspaceError(404, 'Dataset not found.')
        try:
            before = self.registry.canonical_fingerprint(dataset_id)
            frame = self.registry.frame(dataset_id)
            after = self.registry.canonical_fingerprint(dataset_id)
            if before != after:
                raise OSError('Source changed during reading.')
            selected = frame[frame['nct_id'].astype(str).eq(nct_id)]
        except (OSError, ValueError, KeyError):
            raise ResearchWorkspaceError(503, 'Dataset files are unavailable. Restore server storage from backup.') from None
        if selected.empty:
            raise ResearchWorkspaceError(404, 'Study not found in the selected dataset.')
        return SourceSnapshot(dataset, frame, json_clean(selected.iloc[0].to_dict()), after)

    def _index(self, snapshot):
        key = snapshot.fingerprint
        with self._cache_lock:
            if key in self._similar_cache:
                self._similar_cache.move_to_end(key)
                return self._similar_cache[key]
            selected = snapshot.frame.sort_values('nct_id', kind='stable').head(MAX_INDEX_ROWS)
            # Limiting tokens bounds sparse entries to <=199 per document for
            # unigrams+bigrams. Cached entries store identifiers, not full rows.
            documents = [self._document(row) for row in json_clean(selected.to_dict(orient='records'))]
            vectorizer = TfidfVectorizer(max_features=MAX_TEXT_FEATURES, ngram_range=(1, 2), sublinear_tf=True,
                                         token_pattern=r'(?u)\b\w+\b', norm='l2')
            try:
                matrix = vectorizer.fit_transform(documents)
            except ValueError:
                # Entirely empty text has a zero cosine norm; never create a
                # pretend matching token or a similarity of one for emptiness.
                vectorizer, matrix = None, None
            entry = {'ids': selected['nct_id'].astype(str).tolist(), 'vectorizer': vectorizer, 'matrix': matrix}
            self._similar_cache[key] = entry
            while len(self._similar_cache) > MAX_CACHE_ENTRIES:
                self._similar_cache.popitem(last=False)
            return entry

    @staticmethod
    def _document(row):
        # The registry owns source strings; a bounded prefix is retrieval-only.
        text = ' '.join(str(row.get(field) or '')[:4000] for field in TEXT_FIELDS)
        return ' '.join(re.findall(r'\w+', text)[:MAX_DOCUMENT_WORDS])

    def similar(self, snapshot: SourceSnapshot, same_phase=True, limit=5) -> dict:
        entry = self._index(snapshot)
        if entry['vectorizer'] is None:
            similarities = [0.0] * len(entry['ids'])
        else:
            query = entry['vectorizer'].transform([self._document(snapshot.study)])
            similarities = cosine_similarity(query, entry['matrix']).ravel().tolist()
        wanted_phase = normalized_phase(snapshot.study.get('phase'))
        indexed = snapshot.frame.set_index(snapshot.frame['nct_id'].astype(str), drop=False)
        candidates = []
        for identifier, similarity in zip(entry['ids'], similarities):
            if identifier == str(snapshot.study['nct_id']):
                continue
            if similarity <= 0:
                continue
            row = indexed.loc[identifier]
            if same_phase and normalized_phase(row.get('phase')) != wanted_phase:
                continue
            candidates.append((identifier, max(0.0, min(1.0, float(similarity)))))
        candidates.sort(key=lambda value: (-value[1], value[0]))
        items = [{'study': json_clean(indexed.loc[identifier].to_dict()), 'similarity': similarity}
                 for identifier, similarity in candidates[:limit]]
        return {'items': items, 'method': SIMILARITY_METHOD, 'scope': {
            'dataset_id': snapshot.dataset['id'], 'source_sha256': snapshot.dataset['sha256'],
            'canonical_sha256': snapshot.canonical_sha256, 'source': snapshot.dataset['source'],
            'is_fixture': snapshot.dataset['is_fixture'], 'source_rows': len(snapshot.frame),
            'indexed_rows': len(entry['ids']), 'max_indexed_rows': MAX_INDEX_ROWS,
            'index_selection': 'First study identifiers in ascending order.',
            'text_fields': list(TEXT_FIELDS), 'max_document_words': MAX_DOCUMENT_WORDS,
            'same_phase': same_phase, 'phase': wanted_phase if same_phase else None,
            'self_excluded': True, 'clinical_equivalence': False,
            'zero_norm_policy': 'Zero-norm documents have retrieval cosine zero; zero-score results are omitted.',
            'warning': 'Cosine similarity describes text overlap; no clinical equivalence or outcome probability is established.'}}

    def workspace(self, snapshot: SourceSnapshot) -> dict:
        phase = normalized_phase(snapshot.study.get('phase'))
        peers = snapshot.frame[snapshot.frame['phase'].map(normalized_phase).eq(phase)]
        enrollments = pd.to_numeric(peers['enrollment'], errors='coerce').dropna()
        scores = [_pci(row)['score'] for row in json_clean(peers.to_dict(orient='records'))]
        availability = {'status': 'unavailable', 'probability': None,
                        'reason': 'No curated task labels and validated model are available; planning assumptions do not estimate this risk.'}
        return json_clean({'study': snapshot.study, 'pci': _pci(snapshot.study),
            'duration': predict(snapshot.study, snapshot.dataset, self.registry),
            'phase': predict_phase_for_dataset(snapshot.study, snapshot.dataset, self.registry),
            'similar': self.similar(snapshot), 'phase_context': {
                'phase': phase, 'count': len(peers),
                'median_enrollment': float(enrollments.median()) if len(enrollments) else None,
                'median_pci': float(pd.Series(scores).median()) if scores else None},
            'provenance': snapshot.provenance,
            'risk_availability': {'recruitment': availability.copy(), 'amendment': availability.copy()}})

    @staticmethod
    def _history_params(snapshot):
        return {'dataset_id': snapshot.dataset['id'], 'source_sha256': snapshot.dataset['sha256'],
                'canonical_sha256': snapshot.canonical_sha256, 'nct_id': str(snapshot.study['nct_id']),
                'limit': MAX_HISTORY_ITEMS}

    def scenarios(self, snapshot):
        params = self._history_params(snapshot)
        rows = self.registry._execute(SELECT_SCENARIOS, params, fetch=True)
        count = self.registry._execute(COUNT_SCENARIOS, params, fetch=True)[0][0]
        return {'items': [json.loads(row[0]) for row in rows], 'total': int(count), 'limit': MAX_HISTORY_ITEMS}

    def create_scenario(self, snapshot: SourceSnapshot, request: ScenarioRequest) -> dict:
        overrides = request.overrides.model_dump(exclude_unset=True)
        row = {**snapshot.study, **overrides}
        target = _finite_number(row.get('enrollment'))
        if target is None or target < 0 or target > 10_000_000:
            raise ResearchWorkspaceError(422, 'A finite enrollment target between 0 and 10000000 is required. Supply an enrollment override when source enrollment is missing.')
        planning = request.planning.model_dump()
        recruitment = target / (planning['sites'] * planning['monthly_rate_per_site'])
        total = planning['startup_months'] + recruitment + planning['followup_months']
        base_pci, scenario_pci = _pci(snapshot.study), _pci(row)
        base_duration = json_clean(predict(snapshot.study, snapshot.dataset, self.registry, request.model_name))
        scenario_duration = json_clean(predict(row, snapshot.dataset, self.registry, request.model_name))
        hypothetical_scope = 'Hypothetical protocol query to a source-compatible model; source cohort membership is provenance, not scenario validation.'
        source_scope = scenario_duration.get('prediction_scope')
        scenario_duration = {**scenario_duration, 'hypothetical': True,
                             'source_cohort_membership': scenario_duration.get('cohort_membership'),
                             'source_prediction_scope': source_scope,
                             'prediction_scope': hypothetical_scope}
        if isinstance(scenario_duration.get('uncertainty'), dict):
            scenario_duration['uncertainty'] = {**scenario_duration['uncertainty'],
                'hypothetical': True, 'source_prediction_scope': source_scope,
                'prediction_scope': hypothetical_scope,
                'scenario_coverage': 'No empirical coverage guarantee is established for this altered protocol.'}
        changes = {'pci': round(scenario_pci['score'] - base_pci['score'], 2), 'duration_days': None, 'probability': None}
        for field in ('duration_days', 'probability'):
            original, changed = _finite_number(base_duration.get(field)), _finite_number(scenario_duration.get(field))
            if base_duration.get('status') == 'available' and scenario_duration.get('status') == 'available' and original is not None and changed is not None:
                # Never subtract predictions from different fitted runs/models.
                if (base_duration.get('run_id'), base_duration.get('model_name')) == (scenario_duration.get('run_id'), scenario_duration.get('model_name')):
                    changes[field] = changed - original
        result = json_clean({'id': uuid.uuid4().hex, 'name': request.name, 'created_at': now(),
            'base': {'study': snapshot.study, 'pci': base_pci, 'duration': base_duration},
            'scenario': {'study': row, 'pci': scenario_pci, 'duration': scenario_duration},
            'planning': {**planning, 'target_enrollment': target, 'recruitment_months': recruitment,
                         'total_months': total,
                         'formula': 'recruitment_months = target_enrollment / (sites * monthly_rate_per_site); total_months = startup_months + recruitment_months + followup_months',
                         'assumptions': ['Constant per-site monthly recruitment; all sites recruit throughout the modeled interval.',
                                         'Startup, recruitment and followup are sequential additive assumptions.',
                                         'Planning arithmetic is not a recruitment risk prediction or a causal clinical forecast.']},
            'overrides': overrides, 'changes': changes, 'model_name': request.model_name,
            'warning': 'Hypothetical research scenario. Protocol changes are not causal intervention evidence. Source data remains immutable; model provenance and original cohort membership do not validate the altered design.',
            'provenance': snapshot.provenance})
        result['evidence_sha256'] = evidence_digest(result)
        payload = canonical_json(result)
        if len(payload.encode('utf-8')) > MAX_EVIDENCE_BYTES:
            raise ResearchWorkspaceError(413, 'Scenario evidence exceeds the bounded packet size. Use a source with shorter text fields.')
        self.registry._execute(INSERT_SCENARIO, {**self._history_params(snapshot), 'id': result['id'],
                                              'created_at': result['created_at'], 'payload': payload})
        return result

    def evidence(self, snapshot):
        history = self.scenarios(snapshot)
        result = {'workspace': self.workspace(snapshot), 'scenarios': history['items'], 'generated_at': now(),
                  'scope': {'dataset_id': snapshot.dataset['id'], 'nct_id': snapshot.study['nct_id'],
                            'source_sha256': snapshot.dataset['sha256'], 'canonical_sha256': snapshot.canonical_sha256,
                            'is_fixture': snapshot.dataset['is_fixture'], 'clinical_equivalence': False,
                            'scenarios_included': len(history['items']), 'scenarios_total': history['total'],
                            'max_history_items': MAX_HISTORY_ITEMS, 'max_packet_bytes': MAX_EVIDENCE_BYTES,
                            'digest_method': 'SHA-256 of UTF-8 canonical JSON: sorted keys, compact separators, no NaN; exclude only top-level evidence_sha256.',
                            'warning': 'Research decision support; scenario predictions are hypothetical and similarity is descriptive.'}}
        result['evidence_sha256'] = evidence_digest(result)
        if len(canonical_json(result).encode('utf-8')) > MAX_EVIDENCE_BYTES:
            raise ResearchWorkspaceError(413, 'Evidence exceeds the bounded packet size. Export fewer scenarios or use a source with shorter text fields.')
        return result
