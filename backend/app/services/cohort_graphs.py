"""Full-cohort descriptive graphs with observed-data denominators.

Date outcomes require completed status, ACTUAL completion and exact calendar
 dates. A partial registry date stays partial; no day or stage is inferred.
"""
from __future__ import annotations

import math
import re
from datetime import date

import pandas as pd

from .data_service import json_clean
from .pci_service import METHODOLOGY, PCI_SPEC, calculate_pci_details

GRAPH_TYPES = [
    {'id': 'phase_distribution', 'label': 'Phase counts', 'type': 'pie', 'units': 'studies'},
    {'id': 'status_distribution', 'label': 'Status counts', 'type': 'pie', 'units': 'studies'},
    {'id': 'enrollment_histogram', 'label': 'Enrollment distribution', 'type': 'histogram', 'units': 'participants'},
    {'id': 'pci_distribution', 'label': 'PCI distribution', 'type': 'histogram', 'units': 'PCI points'},
    {'id': 'pci_scatter', 'label': 'Enrollment versus PCI', 'type': 'scatter', 'units': 'participants / PCI points'},
    {'id': 'duration_box', 'label': 'Observed duration by phase', 'type': 'box', 'units': 'days'},
    {'id': 'enrollment_by_phase', 'label': 'Enrollment by phase', 'type': 'bar', 'units': 'participants'},
    {'id': 'pci_components', 'label': 'PCI component summary', 'type': 'bar', 'units': 'weighted PCI points'},
    {'id': 'timeline_gantt', 'label': 'Reported trial dates', 'type': 'gantt', 'units': 'calendar dates'},
    {'id': 'missingness', 'label': 'Source field missingness', 'type': 'bar', 'units': 'studies'},
    {'id': 'start_year_activity', 'label': 'Studies by start year', 'type': 'bar', 'units': 'studies'},
    {'id': 'model_comparison', 'label': 'Saved model test evidence', 'type': 'bar', 'units': 'task-specific test metrics'},
    {'id': 'complexity_heatmap', 'label': 'Mean PCI by phase and status', 'type': 'heatmap', 'units': 'PCI points'},
    {'id': 'recruitment_funnel', 'label': 'Reported recruitment counts', 'type': 'funnel', 'units': 'participants'},
]
for _graph in GRAPH_TYPES:
    _graph['description'] = ('Saved held-out test evidence; training source may differ from the selected cohort.'
                             if _graph['id'] == 'model_comparison' else
                             'Full selected cohort; missing source measurements are disclosed.')
GRAPH_IDS = {graph['id'] for graph in GRAPH_TYPES} | {'risk_radar'}


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def present(value):
    if value is None or pd.isna(value):
        return False
    return not isinstance(value, str) or value.strip().casefold() not in {'', 'unknown', 'not reported', 'nan'}


def date_info(value):
    """Return the original ISO date and its precision, never pad a date."""
    if not isinstance(value, str):
        return None, None
    value = value.strip()
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            date.fromisoformat(value)
            return value, 'day'
        if re.fullmatch(r'\d{4}-\d{2}', value):
            date.fromisoformat(value + '-01')
            return value, 'month'
        if re.fullmatch(r'\d{4}', value):
            date.fromisoformat(value + '-01-01')
            return value, 'year'
    except ValueError:
        pass
    return None, None


def observed_duration(row):
    start, start_precision = date_info(row.get('start_date'))
    end, end_precision = date_info(row.get('completion_date'))
    if (str(row.get('status', '')).strip().upper() != 'COMPLETED'
            or str(row.get('completion_date_type', '')).strip().upper() != 'ACTUAL'
            or start_precision != 'day' or end_precision != 'day'):
        return None
    duration = (date.fromisoformat(end) - date.fromisoformat(start)).days
    return duration if duration > 0 else None


def timeline_row(row):
    start, start_precision = date_info(row.get('start_date'))
    completion, completion_precision = date_info(row.get('completion_date'))
    return {'nct_id': row.get('nct_id'), 'title': row.get('title'), 'phase': row.get('phase'),
            'start_date': start, 'completion_date': completion, 'start_precision': start_precision,
            'completion_precision': completion_precision,
            'completion_date_type': row.get('completion_date_type') if present(row.get('completion_date_type')) else None,
            'observed_duration_days': observed_duration(row)}


def metadata(n, reported, *, method, units, **extra):
    return {'status': 'unavailable' if not reported else 'available' if reported == n else 'partial',
            'denominator': n, 'reporting_rows': reported, 'missing_rows': n - reported,
            'method': method, 'units': units, **extra}


RECRUITMENT_FIELDS = [
    ('Screening', ('screened_count', 'screened')),
    ('Eligibility', ('eligible_count', 'eligible')),
    ('Enrollment', ('enrolled_count', 'enrolled')),
    ('Follow-up', ('followup_count', 'follow_up_count', 'followed_up')),
    ('Completion', ('completed_count', 'completed_participants')),
]


def recruitment_summary(frame):
    rows = json_clean(frame.to_dict(orient='records'))
    n = len(rows)
    stages = []
    for stage, candidates in RECRUITMENT_FIELDS:
        field = next((field for field in candidates if field in frame and any(number(row.get(field)) is not None for row in rows)), None)
        values = [number(row.get(field)) for row in rows] if field else []
        values = [value for value in values if value is not None]
        if stage == 'Enrollment' and not field:
            values = [number(row.get('enrollment')) for row in rows
                      if str(row.get('enrollment_type', '')).strip().upper() == 'ACTUAL']
            values = [value for value in values if value is not None]
            field = 'enrollment (ACTUAL)' if values else None
        stages.append({'stage': stage, 'count': sum(values) if values else None,
                       'source_field': field, 'availability': 'available' if len(values) == n and n else 'partial' if values else 'unavailable',
                       'reporting_rows': len(values), 'conversion_rate': None, 'drop_rate': None})
    site_field = next((field for field in ('number_of_sites', 'site_count') if field in frame), None)
    sites = [number(row.get(site_field)) for row in rows] if site_field else []
    sites = [value for value in sites if value is not None]
    targets = [number(row.get('enrollment')) for row in rows
               if str(row.get('enrollment_type', '')).strip().upper() == 'ESTIMATED']
    targets = [value for value in targets if value is not None]
    reported_stages = sum(stage['count'] is not None for stage in stages)
    return {'status': 'unavailable' if not reported_stages else 'available' if all(stage['availability'] == 'available' for stage in stages) else 'partial',
            'total_studies': n, 'stages': stages, 'total_enrolled': stages[2]['count'],
            'target_enrollment': sum(targets) if targets else None,
            'target_reporting_rows': len(targets), 'sites': sum(sites) if sites else None,
            'site_source_field': site_field, 'site_reporting_rows': len(sites),
            'site_interpretation': 'Sum of reported study site counts; sites may overlap between studies.',
            'average_retention_rate': None,
            'reason': 'Only reported participant-stage counts are shown. Planned enrollment is separate; absent stages and conversion rates are unknown.'}


def _histogram(values, edges, labels):
    valid = pd.Series([value for value in values if value is not None], dtype=float)
    counts = pd.cut(valid, bins=edges, labels=labels, right=False, include_lowest=True).value_counts(sort=False)
    return {'labels': labels, 'values': counts.tolist(),
            'bins': [{'lower': lower, 'upper': upper if math.isfinite(upper) else None,
                      'lower_inclusive': True, 'upper_inclusive': False} for lower, upper in zip(edges, edges[1:])]}


def aggregate_graphs(frame, graph_ids, *, dataset, source_rows=None, filters=None, experiments=()):
    rows = json_clean(frame.to_dict(orient='records'))
    n = len(rows)
    from src.clinical_trial_intelligence.research import normalize_design_phase
    phases = [normalize_design_phase(row.get('phase')) for row in rows]
    statuses = [str(row.get('status')) if present(row.get('status')) else 'Unknown' for row in rows]
    enrollment = [number(row.get('enrollment')) for row in rows]
    pci = [calculate_pci_details(row) for row in rows]
    scores = [item['score'] for item in pci]
    computed = {}
    for identifier in graph_ids:
        graph = {}
        reported, units, method = n, 'studies', 'Full-cohort source counts.'
        if identifier in {'phase_distribution', 'status_distribution'}:
            values = phases if identifier == 'phase_distribution' else statuses
            counts = pd.Series(values, dtype=str).value_counts(sort=False).sort_index()
            graph = {'labels': counts.index.tolist(), 'values': counts.tolist()}
            field = 'phase' if identifier == 'phase_distribution' else 'status'
            reported = sum(present(row.get(field)) for row in rows)
        elif identifier == 'enrollment_histogram':
            graph = _histogram(enrollment, [0, 50, 100, 250, 500, 1000, 5000, math.inf],
                               ['0–<50', '50–<100', '100–<250', '250–<500', '500–<1000', '1000–<5000', '5000+'])
            reported, units = sum(value is not None for value in enrollment), 'participants'
        elif identifier == 'pci_distribution':
            graph = _histogram(scores, [0, 20, 40, 60, 80, math.inf], ['0–<20', '20–<40', '40–<60', '60–<80', '80–100'])
            complete = sum(not item['missing_fields'] for item in pci)
            # The fixed-reference index remains computable with its documented
            # zero-burden missing-component policy. Distinguish computed scores
            # from complete inputs; do not hide every score for a missing optional field.
            reported = sum(any(present(row.get(part['key'])) for part in PCI_SPEC['components']) for row in rows)
            graph.update(incomplete_pci_rows=n-complete, complete_input_rows=complete,
                         status='unavailable' if not reported else 'partial' if complete<n else 'available')
            units, method = 'PCI points', METHODOLOGY
        elif identifier == 'pci_scatter':
            graph = {'points': [{'nct_id': row['nct_id'], 'enrollment': enrollment[i], 'pci': scores[i],
                                 'phase': phases[i], 'pci_missing_fields': pci[i]['missing_fields']} for i, row in enumerate(rows)]}
            reported = sum(value is not None for value in enrollment)
            units, method = 'participants / PCI points', METHODOLOGY
        elif identifier == 'duration_box':
            groups = {}
            for row, phase in zip(rows, phases):
                duration = observed_duration(row)
                if duration is not None:
                    groups.setdefault(phase, []).append(duration)
            graph = {'groups': [{'phase': phase, 'values': values, 'n': len(values),
                                 'median': float(pd.Series(values).median()), 'q1': float(pd.Series(values).quantile(.25)),
                                 'q3': float(pd.Series(values).quantile(.75))} for phase, values in sorted(groups.items())]}
            reported = sum(len(values) for values in groups.values())
            units, method = 'days', 'Positive completion minus start date; completed status, ACTUAL completion and exact day precision required.'
        elif identifier == 'enrollment_by_phase':
            values = {phase: [] for phase in sorted(set(phases))}
            for phase, value in zip(phases, enrollment):
                if value is not None:
                    values[phase].append(value)
            graph = {'labels': list(values), 'values': [sum(value) if value else None for value in values.values()],
                     'reporting_counts': [len(value) for value in values.values()],
                     'study_counts': [phases.count(phase) for phase in values]}
            reported, units = sum(value is not None for value in enrollment), 'participants'
        elif identifier in {'pci_components', 'risk_radar'}:
            dimensions = []
            for component in PCI_SPEC['components']:
                values = [item['components'][component['label']] for item in pci if component['key'] not in item['missing_fields']]
                dimensions.append({'dimension': component['label'], 'field': component['key'],
                                   'mean': float(pd.Series(values).mean()) if values else None,
                                   'median': float(pd.Series(values).median()) if values else None,
                                   'reporting_rows': len(values), 'missing_rows': n - len(values), 'weight': component['weight']})
            graph = {'dimensions': dimensions, 'methodology': METHODOLOGY, 'risk_prediction': False}
            complete = sum(not item['missing_fields'] for item in pci)
            reported = sum(any(present(row.get(part['key'])) for part in PCI_SPEC['components']) for row in rows)
            graph.update(complete_input_rows=complete, incomplete_pci_rows=n-complete,
                         status='unavailable' if not reported else 'partial' if complete<n else 'available')
            units, method = 'weighted PCI points', METHODOLOGY
        elif identifier == 'timeline_gantt':
            trials = [timeline_row(row) for row in rows]
            graph = {'trials': trials}
            reported = sum(item['start_date'] is not None and item['completion_date'] is not None for item in trials)
            units, method = 'calendar dates', 'Reported source dates with original precision and completion date type; no missing dates inferred.'
        elif identifier == 'missingness':
            graph = {'fields': [{'field': field, 'missing_rows': sum(not present(row.get(field)) for row in rows),
                                 'reported_rows': sum(present(row.get(field)) for row in rows),
                                 'missing_fraction': sum(not present(row.get(field)) for row in rows) / n if n else None}
                                for field in frame.columns]}
            method = 'Missing, empty and Unknown / Not reported source values; zero is a reported numeric value.'
        elif identifier == 'start_year_activity':
            years = [value[:4] for row in rows if (value := date_info(row.get('start_date'))[0])]
            counts = pd.Series(years, dtype=str).value_counts(sort=False).sort_index()
            graph = {'labels': counts.index.tolist(), 'values': counts.tolist()}
            reported, method = len(years), 'Reported start year; year and month precision are sufficient for year counts.'
        elif identifier == 'complexity_heatmap':
            grouped = {}
            for phase, status, score in zip(phases, statuses, scores):
                grouped.setdefault((phase, status), []).append(score)
            graph = {'cells': [{'phase': phase, 'status': status, 'avg_pci': sum(values) / len(values), 'n': len(values)}
                               for (phase, status), values in sorted(grouped.items())]}
            complete = sum(not item['missing_fields'] for item in pci)
            reported = sum(any(present(row.get(part['key'])) for part in PCI_SPEC['components']) for row in rows)
            graph.update(complete_input_rows=complete, incomplete_pci_rows=n-complete,
                         status='unavailable' if not reported else 'partial' if complete<n else 'available')
            units, method = 'PCI points', METHODOLOGY
        elif identifier == 'recruitment_funnel':
            graph = recruitment_summary(frame)
            reported = max((stage['reporting_rows'] for stage in graph['stages']), default=0)
            units, method = 'participants', 'Only supported source recruitment counts; ACTUAL enrollment is distinct from planned targets.'
        elif identifier == 'model_comparison':
            models = []
            for experiment in experiments:
                if experiment.get('status') != 'completed':
                    continue
                manifest = experiment.get('manifest') or {}
                model_data = manifest.get('models', {})
                if not model_data:
                    model_data = {name: {'metrics': value} for name, value in (experiment.get('metrics') or {}).items()}
                for name, item in model_data.items():
                    test = (item.get('metrics') or {}).get('test')
                    if isinstance(test, dict) and test:
                        models.append({'experiment_id': experiment['id'], 'run_id': manifest.get('run_id'),
                                       'model_name': name, 'task': experiment.get('task', manifest.get('task', 'duration')),
                                       'split': 'test', 'n': test.get('n', manifest.get('splits', {}).get('test', {}).get('rows')),
                                       'metrics': test, 'source_sha256': experiment.get('dataset_sha256')})
            evidence_rows = sum(number(model.get('n')) or 0 for model in models)
            graph = {'models': models, 'evidence_count': len(models),
                     'denominator': evidence_rows, 'reporting_rows': evidence_rows, 'missing_rows': 0,
                     'denominator_unit': 'held-out predictions', 'selected_cohort_rows': n,
                     'status': 'available' if models and all(number(model.get('n')) is not None for model in models)
                               else 'partial' if models else 'unavailable'}
            reported = 0
            units, method = 'task-specific test metrics', 'Saved completed experiment test metrics; no generated comparisons.'
        computed[identifier] = {**metadata(n, reported, method=method, units=units), **graph}
    return json_clean({'dataset_id': dataset['id'], 'source_sha256': dataset['sha256'],
                       'source_rows': source_rows if source_rows is not None else n, 'row_count': n,
                       'is_fixture': dataset.get('is_fixture', False), 'filters': filters or {'phase': None, 'status': None},
                       'selected_graphs': list(graph_ids), 'computed_data': computed})
