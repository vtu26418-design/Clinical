"""Artificial records verify ingestion mechanics only; never training evidence."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]


def module():
    path=ROOT/'scripts/acquire_registry_cohort.py'
    assert path.is_file(),'The resumable acquisition implementation is missing'
    spec=importlib.util.spec_from_file_location('registry_acquisition',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def record(identifier='NCT00000001',enrollment_type='ACTUAL'):
    return {'protocolSection':{'identificationModule':{'nctId':identifier,'briefTitle':'Software ingestion fixture'},'statusModule':{'overallStatus':'COMPLETED','startDateStruct':{'date':'2010-01','type':'ACTUAL'},'completionDateStruct':{'date':'2011-02-03','type':'ACTUAL'},'studyFirstPostDateStruct':{'date':'2009-12-02'}},'designModule':{'studyType':'INTERVENTIONAL','phases':['PHASE1','PHASE2'],'enrollmentInfo':{'count':40,'type':enrollment_type},'designInfo':{'allocation':'RANDOMIZED','maskingInfo':{'masking':'DOUBLE'},'primaryPurpose':'TREATMENT'}},'armsInterventionsModule':{'armGroups':[{'label':'Arm1'}],'interventions':[{'type':'DRUG'}]},'eligibilityModule':{'eligibilityCriteria':'Inclusion Criteria:\n- Age over18\nExclusion Criteria:\n- Active infection'},'sponsorCollaboratorsModule':{'leadSponsor':{'class':'INDUSTRY'}},'conditionsModule':{'conditions':['ConditionA']}}}


def test_canonical_source_fields_do_not_turn_actual_enrollment_into_planned():
    m=module();actual=m.canonical_record(record());planned=m.canonical_record(record(enrollment_type='ESTIMATED'))
    assert actual['enrollment']==40 and actual['planned_enrollment'] is None
    assert planned['planned_enrollment']==40
    assert actual['start_date']=='2010-01' and actual['phase']=='PHASE1|PHASE2'
    assert actual['study_first_posted_date']=='2009-12-02'
    assert actual['criteria_count'] is None
    assert actual['eligibility_line_count']==4
    assert actual['sponsor_class']=='INDUSTRY' and actual['design_masking']=='DOUBLE'
    assert actual['reported_sites'] is None


def test_resumable_raw_preservation_explicit_deduplication_and_replay(tmp_path):
    m=module();calls=[]
    first={'studies':[record()], 'nextPageToken':'next-public-page','totalCount':2}
    second={'studies':[record(),record('NCT00000002')]}
    def fetch(params,remaining):
        calls.append(params.copy())
        if len(calls)==2:raise OSError('test transport interruption')
        return json.dumps(first if not params.get('pageToken') else second).encode(),'fixture-http-date'
    folder=tmp_path/'source'
    with pytest.raises(OSError):m.acquire(folder,maximum=10,page_size=2,fetch=fetch,pause_seconds=0)
    raw=(folder/'raw/page-000001.json.gz').read_bytes()
    result=m.acquire(folder,maximum=10,page_size=2,fetch=fetch,pause_seconds=0,resume=True)
    assert result['rows']==2 and result['duplicate_ids']==1 and result['acquisition_complete']
    assert (folder/'raw/page-000001.json.gz').read_bytes()==raw
    replay=m.load_cohort(folder,verify=True)
    assert list(replay.nct_id)==['NCT00000001','NCT00000002']
    assert not result['baseline_provenance']
    (folder/'raw/page-000001.json.gz').write_bytes(b'tampered')
    with pytest.raises(ValueError,match='checksum'):m.load_cohort(folder,verify=True)
