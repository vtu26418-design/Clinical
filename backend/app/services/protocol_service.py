"""Deterministic document evidence and explicit availability checks, not clinical NLP validation."""
from __future__ import annotations

from datetime import datetime, timezone
import difflib
import hashlib
import io
import math
from pathlib import Path
import re

DOMAIN_NAMES = {
    'design': 'Study design complexity', 'eligibility': 'Eligibility complexity',
    'patient': 'Patient burden', 'site': 'Site / operational burden',
    'endpoint': 'Endpoint / data burden', 'geography': 'Geographic / regulatory burden',
    'intervention': 'Intervention / safety burden',
}
DOMAIN_PATTERNS = {
    'design': r'\b(randomi[sz]|blind|crossover|parallel|adaptive|arm[s]?)\w*\b',
    'eligibility': r'\b(inclusion|exclusion|eligibility)\b',
    'patient': r'\b(visit[s]?|biopsy|patient burden|questionnaire|travel)\b',
    'site': r'\b(site[s]?|operational|monitoring|investigator[s]?)\b',
    'endpoint': r'\b(endpoint[s]?|outcome[s]?|assessment[s]?)\b',
    'geography': r'\b(countries|country|regulatory|jurisdiction|multinational)\b',
    'intervention': r'\b(dose|dosing|safety|adverse|intervention|treatment)\b',
}


def extract_document(raw: bytes, filename: str) -> dict:
    if not raw or len(raw) > 8 * 1024 * 1024:
        raise ValueError('Provide a nonempty protocol up to 8 MB.')
    suffix = Path(filename).suffix.lower()
    if suffix not in {'.txt', '.md', '.pdf'}:
        raise ValueError('Supported protocols: text-based PDF, UTF-8 TXT or Markdown.')
    if suffix == '.pdf':
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            if reader.is_encrypted:
                raise ValueError('Encrypted PDFs are not supported. Export an unlocked text PDF.')
            if len(reader.pages) > 150:
                raise ValueError('Limit the protocol to 150 pages.')
            pages = []
            count = 0
            for number, page in enumerate(reader.pages, 1):
                # Bound decompressed content before text extraction as well as input bytes.
                contents = page.get_contents()
                if contents is not None and len(contents.get_data()) > 4 * 1024 * 1024:
                    raise ValueError('A PDF page is too large to extract safely.')
                text = page.extract_text() or ''
                count += len(text)
                if count > 250_000:
                    raise ValueError('Protocol text exceeds 250,000 characters.')
                pages.append({'page': number, 'text': text})
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError('The PDF could not be read. Use a valid text-based PDF.') from exc
    else:
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError('Text documents must use UTF-8 encoding.') from exc
        if '\x00' in text or len(text) > 250_000:
            raise ValueError('Text is binary or exceeds 250,000 characters.')
        pages = [{'page': 1, 'text': text}]
    text = '\n'.join(p['text'] for p in pages)
    if len(text.strip()) < 20:
        raise ValueError('No usable text was extracted. Scanned PDFs need OCR outside this app first.')
    features, evidence = {}, []
    domains = {key: {'name': name, 'status': 'unknown', 'evidence_count': 0, 'score': None} for key, name in DOMAIN_NAMES.items()}
    phase_map = {'0': 'EARLY_PHASE1', 'I': 'PHASE1', '1': 'PHASE1', 'II': 'PHASE2', '2': 'PHASE2', 'III': 'PHASE3', '3': 'PHASE3', 'IV': 'PHASE4', '4': 'PHASE4'}
    phases, enrollment = set(), set()
    for page in pages:
        section = 'Document text'
        for line in page['text'].splitlines():
            line = line.strip()
            if not line:
                continue
            if len(line) < 100 and (line.isupper() or re.match(r'^\d+(\.\d+)*\s+\w', line)):
                section = line
            candidates = []
            for match in re.finditer(r'\bphase\s+(IV|III|II|I|[0-4])\b', line, re.I):
                value = phase_map[match.group(1).upper()]
                phases.add(value)
                candidates.append(('phase', value))
            match = re.search(r'\b(?:target\s+)?enroll?ment\s*[:=]?\s*(\d[\d,]*)\b', line, re.I)
            if match:
                value = int(match.group(1).replace(',', ''))
                if 0 < value <= 10_000_000:
                    enrollment.add(value)
                    candidates.append(('enrollment', value))
            for field, value in candidates:
                evidence.append({'field': field, 'value': value, 'page': page['page'], 'section': section, 'quote': line[:800], 'method': 'rule_candidate', 'review_required': True})
            for key, pattern in DOMAIN_PATTERNS.items():
                if re.search(pattern, line, re.I):
                    domains[key]['status'] = 'evidence_found'
                    domains[key]['evidence_count'] += 1
                    if sum(x['field'] == key for x in evidence) < 15:
                        evidence.append({'field': key, 'value': None, 'page': page['page'], 'section': section, 'quote': line[:800], 'method': 'keyword_evidence', 'review_required': True})
    if len(phases) == 1:
        features['phase'] = next(iter(phases))
    if len(enrollment) == 1:
        features['enrollment'] = next(iter(enrollment))
    return {'source_sha256': hashlib.sha256(raw).hexdigest(), 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'pages': pages, 'text': text, 'features': features, 'evidence': evidence[:200], 'domains': domains,
            'composite_score': None, 'review_status': 'pending',
            'warnings': ['Rule-extracted candidates require human review. A mentioned phase may refer to a prior study.',
                         'Evidence counts are not burden scores. Unknown domains remain unknown.',
                         'No approved protocol-PDF-specific predictive model is bundled; registry-model performance does not validate PDF extraction.']}


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def availability_audit(prediction_at: str, feature_timestamps: dict) -> dict:
    try:
        cutoff = _timestamp(prediction_at)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Prediction timestamp must be a valid ISO date or timestamp.') from exc
    accepted, late, unknown = [], [], []
    for key, value in feature_timestamps.items():
        try:
            timestamp = _timestamp(value)
        except (ValueError, TypeError, AttributeError):
            unknown.append(key)
            continue
        (accepted if timestamp <= cutoff else late).append(key)
    return {'prediction_at': cutoff.isoformat(), 'eligible': bool(feature_timestamps) and not late and not unknown,
            'accepted': accepted, 'late': late, 'unknown': unknown,
            'scope': 'Availability audit of supplied timestamps only; source verification and model validation are separate.'}


def domain_score(scores: dict, weights: dict) -> dict:
    if set(weights) != set(DOMAIN_NAMES) or set(scores) != set(DOMAIN_NAMES):
        raise ValueError('Provide all seven named domains and weights.')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in weights.values()) or sum(weights.values()) <= 0:
        raise ValueError('Weights must be finite non-negative numbers with a positive total.')
    if any(v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 100) for v in scores.values()):
        raise ValueError('Each reviewed domain score must be 0-100 or unknown.')
    missing = [k for k, v in scores.items() if v is None]
    score = None if missing else round(sum(scores[k] * weights[k] for k in scores) / sum(weights.values()), 4)
    return {'score': score, 'missing_domains': missing, 'scores': scores, 'weights': weights,
            'formula': 'sum(domain_score * weight) / sum(weights)', 'method': 'User-scored exploratory seven-domain rubric; not clinically validated.'}


def compare_texts(older: str, newer: str) -> dict:
    lines = list(difflib.ndiff(older.splitlines(), newer.splitlines()))
    return {'added': [x[2:] for x in lines if x.startswith('+ ')][:300],
            'removed': [x[2:] for x in lines if x.startswith('- ')][:300],
            'unchanged_lines': sum(x.startswith('  ') for x in lines), 'amendment_probability': None,
            'warning': 'Text differences are not proof of a substantive amendment or its risk.'}
