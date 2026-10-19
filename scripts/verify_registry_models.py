"""Verify frozen registry artifacts and deterministic prediction replay; never fit."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sys

for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from prepare_registry_training import load_prepared,sha256_file
from train_reference_models import _verify_completed
from src.clinical_trial_intelligence import research,phase_model
from src.clinical_trial_intelligence.model_analysis import analyze_experiment
from backend.app.services.phase_service import normalize_phase_input


def verify_refinement(catalog, prepared, sample_per_split):
    """Replay approved refinement without fitting or relabelling its audit role."""
    import pyarrow.dataset as ds
    entry=next(e for e in catalog if e['id']=='registry-phase-refinement-v5205')
    folder=ROOT/entry['directory']
    for filename,key in (('phase_manifest.json','manifest_sha256'),('phase_models.joblib','artifact_sha256')):
        if sha256_file(folder/filename)!=entry[key]:raise ValueError('Refinement approval checksum differs.')
    manifest=json.loads((folder/'phase_manifest.json').read_text())
    evidence=ROOT/'examples/refinement-v5205-evidence'
    protocol=json.loads((evidence/'phase-refinement-holdout/protocol.json').read_text())
    freeze=evidence/'phase-refinement-holdout/ids.csv'
    if sha256_file(freeze)!=protocol['ids_sha256']:raise ValueError('Audit ID freeze differs.')
    audit_ids=set(pd.read_csv(freeze).nct_id)
    original_roles=pd.read_csv(prepared/'phase_partitions.csv')
    if audit_ids.intersection(original_roles.nct_id):raise ValueError('Audit overlaps original phase roles.')
    if audit_ids!=set(manifest['splits']['test']['nct_ids']):raise ValueError('Audit role differs from freeze.')
    saved=pd.read_csv(folder/'phase_held_out_predictions.csv')
    groups=[]
    for (name,split),rows in saved.groupby(['model_name','split'],sort=False):
        if set(rows.nct_id)!=set(manifest['splits'][split]['nct_ids']):raise ValueError('Refinement split differs.')
        positions=np.unique(np.linspace(0,len(rows)-1,min(sample_per_split,len(rows)),dtype=int))
        groups.append((name,split,rows.iloc[positions]))
    selected_ids=set().union(*(set(rows.nct_id) for _,_,rows in groups))
    prep=json.loads((prepared/'preparation_manifest.json').read_text())
    paths=[]
    for shard in prep['shards']:
        path=prepared/shard['file']
        if sha256_file(path)!=shard['sha256']:raise ValueError('Prepared shard differs.')
        paths.append(str(path))
    source=ds.dataset(paths,format='parquet').to_table(filter=ds.field('nct_id').isin(list(selected_ids)),use_threads=False).to_pandas().set_index('nct_id',drop=False)
    artifact=joblib.load(folder/'phase_models.joblib')
    if artifact['run_id']!=manifest['run_id']:raise ValueError('Refinement run identity mismatch.')
    count=0;maximum=0.
    for name,split,rows in groups:
        raw=source.loc[rows.nct_id].reset_index(drop=True)
        normalized=pd.DataFrame([normalize_phase_input(row,manifest) for row in raw.to_dict('records')])
        features=phase_model._phase_features(normalized,include_design=True)
        model=artifact['models'][name]
        probability=phase_model._probabilities(model,features)
        predicted=np.asarray(model.predict(features)).reshape(-1)
        np.testing.assert_array_equal(predicted,rows.predicted_phase)
        np.testing.assert_array_equal(raw.phase.map(phase_model.normalize_phase),rows.actual_phase)
        expected=rows[['probability_'+label for label in phase_model.PHASE_LABELS]].to_numpy()
        np.testing.assert_allclose(probability,expected,rtol=1e-8,atol=1e-8)
        maximum=max(maximum,float(np.max(np.abs(probability-expected))))
        count+=len(rows)
    analysis=analyze_experiment(folder)
    return {'run_id':manifest['run_id'],'artifact_sha256':entry['artifact_sha256'],
            'manifest_sha256':entry['manifest_sha256'],'audit_rows':len(audit_ids),
            'audit_excludes_all_original_phase_roles':True,
            'audit_role':'ID-disjoint partial-start-date subgroup audit; not chronological/prospective',
            'prediction_rows_replayed':count,'max_absolute_prediction_error':maximum,
            'saved_prediction_rows_validated':len(saved),'all_saved_metrics_recomputed':True,
            'split_counts':analysis['split_counts']}


def verify(sample_per_split=100):
    prepared=ROOT/'data/registry-v5205-training';original=ROOT/'examples/registry-v5205'
    state=json.loads((original/'run_manifest.json').read_text())
    if state['status']!='completed':raise ValueError('The frozen experiment is incomplete.')
    catalog=json.loads((ROOT/'examples/approved-models-v5.json').read_text())['models']
    report={'status':'passed','created_at':datetime.now(timezone.utc).isoformat(),'fitting':False,
            'source':'Verified acquisition/preparation shard lineage and frozen task file inventories.',
            'replay_policy':f'At most {sample_per_split} evenly spaced source rows per model and split. All CSV rows are checked separately for metrics/membership.',
            'tolerance':{'rtol':1e-8,'atol':1e-8},'tasks':{}}
    for task in ('duration','phase'):
        _verify_completed(original/task,state['tasks'][task])
        entry=next(e for e in catalog if e['id']==f'registry-{task}-v5205')
        folder=ROOT/entry['directory'];prefix='' if task=='duration' else 'phase_'
        manifest_path=folder/f'{prefix}manifest.json';artifact_path=folder/f'{prefix}models.joblib'
        for path,key in ((manifest_path,'manifest_sha256'),(artifact_path,'artifact_sha256')):
            if sha256_file(path)!=entry[key]:raise ValueError('Release approval checksum differs.')
        for name,expected in state['tasks'][task]['files_sha256'].items():
            if sha256_file(folder/name)!=expected:raise ValueError('Serving copy differs from frozen evidence.')
        manifest=json.loads(manifest_path.read_text());frame,prepared_manifest=load_prepared(prepared,task=task)
        if manifest['source_metadata']['baseline_provenance'] is not False:raise ValueError('Unexpected baseline provenance.')
        indexed=frame.set_index('nct_id',drop=False)
        artifact=joblib.load(artifact_path)  # Only after exact trusted release approval.
        if artifact['run_id']!=manifest['run_id']:raise ValueError('Run identity mismatch.')
        saved=pd.read_csv(folder/f'{prefix}held_out_predictions.csv')
        count=0;max_error=0.
        for (name,split),predictions in saved.groupby(['model_name','split'],sort=False):
            if set(predictions.nct_id)!=set(manifest['splits'][split]['nct_ids']):raise ValueError('Saved split IDs differ.')
            positions=np.unique(np.linspace(0,len(predictions)-1,min(sample_per_split,len(predictions)),dtype=int))
            chosen=predictions.iloc[positions];rows=indexed.loc[chosen.nct_id].reset_index(drop=True)
            model=artifact['models'][name]
            if task=='duration':
                features=research._features(rows,include_design=True)
                estimate=np.maximum(0,model['regressor'].predict(features))
                probability=research._positive_probability(model['classifier'],features)
                np.testing.assert_allclose(estimate,chosen.predicted_duration_days,rtol=1e-8,atol=1e-8)
                np.testing.assert_allclose(probability,chosen.prolonged_probability,rtol=1e-8,atol=1e-8)
                actual=(pd.to_datetime(rows.completion_date)-pd.to_datetime(rows.start_date)).dt.days
                np.testing.assert_array_equal(actual,chosen.actual_duration_days)
                max_error=max(max_error,float(np.max(np.abs(estimate-chosen.predicted_duration_days))))
            else:
                features=phase_model._phase_features(rows,include_design=True)
                estimate=np.asarray(model.predict(features)).reshape(-1)
                probability=phase_model._probabilities(model,features)
                np.testing.assert_array_equal(estimate,chosen.predicted_phase)
                expected=chosen[['probability_'+label for label in phase_model.PHASE_LABELS]].to_numpy()
                np.testing.assert_allclose(probability,expected,rtol=1e-8,atol=1e-8)
                max_error=max(max_error,float(np.max(np.abs(probability-expected))))
            count+=len(chosen)
        analysis=analyze_experiment(folder)
        report['tasks'][task]={'run_id':manifest['run_id'],'artifact_sha256':entry['artifact_sha256'],
            'manifest_sha256':entry['manifest_sha256'],'all_original_file_hashes_verified':True,
            'all_serving_copies_match':True,'prediction_rows_replayed':count,'max_absolute_prediction_error':max_error,
            'saved_prediction_rows_validated':len(saved),'all_saved_metrics_recomputed':True,
            'split_counts':analysis['split_counts'],'dataset_sha256':prepared_manifest['dataset_sha256']}
        del artifact,frame,indexed,saved
    report['tasks']['phase_refinement']=verify_refinement(catalog,prepared,sample_per_split)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);parser.add_argument('--sample-per-split',type=int,default=100)
    args=parser.parse_args()
    if not 1<=args.sample_per_split<=1000:parser.error('Use 1–1000 replay rows per model/split.')
    with threadpool_limits(limits=1):result=verify(args.sample_per_split)
    payload=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(payload)
    print(payload)


if __name__=='__main__':main()
