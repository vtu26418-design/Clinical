"""Incomplete PCI inputs still produce explicitly partial descriptive graphs."""
import pandas as pd

from backend.app.config import PROJECT_ROOT
from backend.app.services.cohort_graphs import aggregate_graphs, recruitment_summary


def test_partial_pci_inputs_show_computed_distribution_with_missingness():
    frame = pd.read_csv(PROJECT_ROOT / 'data/starter/trials.csv')
    result = aggregate_graphs(frame, ['pci_distribution'], dataset={'id':'authentic-starter','sha256':'test-only-source'})
    graph = result['computed_data']['pci_distribution']
    assert graph['status'] == 'partial'
    assert sum(graph['values']) == len(frame)
    assert graph['reporting_rows'] > 0
    assert graph['incomplete_pci_rows'] > 0


def test_completely_missing_pci_inputs_are_unavailable():
    frame = pd.DataFrame({'nct_id':['SOFTWARE-ONLY-EMPTY'],'title':['Software-only missing field test']})
    result = aggregate_graphs(frame, ['pci_distribution'], dataset={'id':'software-only','sha256':'test-only-source'})
    assert result['computed_data']['pci_distribution']['status'] == 'unavailable'


def test_followup_counts_are_observed_and_absence_is_unknown():
    frame = pd.DataFrame({'nct_id':['SOFTWARE-ONLY-FOLLOWUP'],'followup_count':[12]})
    observed = next(stage for stage in recruitment_summary(frame)['stages'] if stage['stage']=='Follow-up')
    assert observed['count'] == 12
    unknown = next(stage for stage in recruitment_summary(frame.drop(columns=['followup_count']))['stages'] if stage['stage']=='Follow-up')
    assert unknown['count'] is None


def test_partial_components_and_heatmap_retain_source_evidence():
    frame = pd.read_csv(PROJECT_ROOT / 'data/starter/trials.csv')
    graphs = aggregate_graphs(frame, ['pci_components','complexity_heatmap'], dataset={'id':'starter','sha256':'test'})['computed_data']
    assert all(graph['status']=='partial' and graph['reporting_rows']>0 and graph['incomplete_pci_rows']>0 for graph in graphs.values())
    assert any(item['reporting_rows']>0 for item in graphs['pci_components']['dimensions'])
