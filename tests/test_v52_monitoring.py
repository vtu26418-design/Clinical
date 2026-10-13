import pandas as pd
import pytest
from scripts.monitor_cohort import compare_cohorts


def cohort(values):
    return pd.DataFrame({'nct_id':[f'NCT{i:08}' for i in range(len(values))], 'enrollment':values, 'phase':['PHASE2']*len(values)})


def test_identical_cohort_has_zero_shift_and_reports_overlap():
    data=cohort(list(range(1,101)))
    report=compare_cohorts(data,data.copy())
    assert report['numeric']['enrollment']['psi'] == pytest.approx(0)
    assert report['identity']['overlapping_ids'] == 100
    assert report['candidate_approval'] == 'human_review_required'


def test_new_values_outside_constant_reference_are_detected():
    report=compare_cohorts(cohort([10]*50),cohort([100]*50))
    assert report['numeric']['enrollment']['out_of_reference_range_fraction'] == 1
    assert report['numeric']['enrollment']['review_required']


def test_missing_and_nonfinite_values_are_not_imputed_as_zero():
    report=compare_cohorts(cohort([10]*40),cohort([None,float('inf')]+[10]*38))
    assert report['numeric']['enrollment']['current_missing_fraction'] == pytest.approx(.05)
    assert report['numeric']['enrollment']['current_median'] == 10


def test_absent_feature_and_empty_input_are_explicit():
    report=compare_cohorts(cohort([1]*35),pd.DataFrame({'nct_id':['OTHER']}))
    assert report['numeric']['enrollment']['status'] == 'missing_column'
    assert report['warnings']
    with pytest.raises(ValueError,match='nonempty'):
        compare_cohorts(cohort([]),cohort([1]))


def test_unseen_categories_and_duplicate_ids_are_reported():
    current=cohort([10]*40)
    current['phase']='PHASE3'
    current.loc[1,'nct_id']=current.loc[0,'nct_id']
    report=compare_cohorts(cohort([10]*40),current)
    assert report['categorical']['phase']['unseen_categories'] == ['PHASE3']
    assert report['identity']['current_duplicate_ids'] == 1


def test_monitoring_does_not_mutate_inputs():
    reference=cohort([1,2,3]);current=cohort([None,4,5])
    before=current.copy(deep=True)
    compare_cohorts(reference,current)
    pd.testing.assert_frame_equal(before,current)


def test_categorical_missingness_change_requests_review_with_same_observed_distribution():
    reference=cohort([10]*100)
    current=cohort([10]*100)
    current.loc[:19,'phase']=None
    entry=compare_cohorts(reference,current)['categorical']['phase']
    assert entry['total_variation_distance'] == 0
    assert entry['current_missing_fraction'] == pytest.approx(.2)
    assert entry['review_required']


@pytest.mark.parametrize('missing_side',['reference','current','both'])
def test_all_missing_categories_cannot_be_compared(missing_side):
    reference=cohort([10]*40)
    current=cohort([10]*40)
    if missing_side in ('reference','both'):
        reference['phase']=None
    if missing_side in ('current','both'):
        current['phase']=None
    entry=compare_cohorts(reference,current)['categorical']['phase']
    assert entry['status'] == 'insufficient_values'
    assert entry['total_variation_distance'] is None
    assert entry['review_required']
