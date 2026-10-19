"""Shared, read-only training eligibility checks for API and launch."""
from dataclasses import asdict
from importlib.util import find_spec


def preflight(df, source, task, max_rows, *, config=None):
    result = {'task': task, 'ready': False, 'input_rows': len(df), 'eligible_rows': 0, 'splits': {}, 'reason': ''}
    try:
        if source.get('fixture') or source.get('is_fixture'):
            raise ValueError('Software-test fixtures are not research cohorts. Duration needs at least 30 eligible records; phase needs 40.')
        if len(df) > max_rows:
            raise ValueError(f'Local experiment limit is {max_rows} rows.')
        if task == 'phase':
            from src.clinical_trial_intelligence.phase_model import PhaseConfig, prepare_phase_cohort, phase_temporal_split
            config = config or PhaseConfig()
            config.validate()
            result['effective_config'] = asdict(config)
            if config.enable_design_catboost and find_spec('catboost') is None:
                raise ValueError('Design CatBoost was requested but is not installed. Install the release requirements first or disable this candidate.')
            cohort, exclusions = prepare_phase_cohort(df)
            result['eligible_rows'] = len(cohort)
            if len(cohort) < 40:
                raise ValueError(f'At least 40 eligible single-phase trials are required; found {len(cohort)}.')
            splits = phase_temporal_split(cohort)
            if len(splits['train']) < 20 or min(len(splits[k]) for k in ('validation', 'test')) < 5:
                raise ValueError('Temporal phase splitting needs at least 20 train and 5 validation/test trials.')
            if splits['train'].phase.nunique() < 2:
                raise ValueError('Training requires at least two phase classes in the chronological training split.')
        else:
            from src.clinical_trial_intelligence.research import ExperimentConfig, prepare_cohort, temporal_split, partition_validation
            config = config or ExperimentConfig()
            config.validate()
            result['effective_config'] = asdict(config)
            if config.enable_design_catboost and find_spec('catboost') is None:
                raise ValueError('Design CatBoost was requested but is not installed. Install the release requirements first or disable this candidate.')
            if config.enable_catboost and find_spec('catboost') is None:
                raise ValueError('CatBoost was requested but is not installed. Install the release requirements first or disable this candidate.')
            cohort, exclusions = prepare_cohort(df, source_metadata=source)
            result['eligible_rows'] = len(cohort)
            if len(cohort) < 30:
                raise ValueError('At least 30 completed studies with exact ACTUAL outcome dates are required.')
            splits = temporal_split(cohort, config)
            if len(splits['train']) < 12 or min(len(splits[k]) for k in ('validation', 'test')) < 3:
                raise ValueError('Outcome purging needs at least 12 train and 3 validation/test studies. Use more records with sufficient follow-up.')
            splits['validation'], splits['calibration'], result['validation_partition'] = partition_validation(splits['validation'])
        result.update(ready=True, splits={k: len(splits[k]) for k in ('train', 'validation', 'calibration', 'test') if k in splits}, excluded_rows=len(exclusions), reason='Cohort passes the requested training checks. Performance is not guaranteed.')
    except ValueError as exc:
        result['reason'] = str(exc)
    return result
