"""Compare frozen cohorts for data shift; never retrain or promote a model.

PSI thresholds are operational review heuristics, not clinical validation.
Both inputs remain unchanged. Run from the project root with its .venv Python.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

NUMERIC = ('enrollment','number_of_arms','primary_outcomes','secondary_outcomes','criteria_count','text_complexity')
CATEGORICAL = ('phase','study_type')


def numeric_values(frame, name):
    return pd.to_numeric(frame[name], errors='coerce').replace([np.inf,-np.inf],np.nan)


def compare_cohorts(reference:pd.DataFrame,current:pd.DataFrame)->dict:
    if reference.empty or current.empty:
        raise ValueError('Both cohorts must be nonempty.')
    result={'schema_version':'1.0','generated_at':datetime.now(timezone.utc).isoformat(),
            'reference_rows':len(reference),'current_rows':len(current),
            'numeric':{},'categorical':{},'identity':{},'warnings':[],
            'candidate_approval':'human_review_required',
            'limitations':['Data shift is not measured prediction error or evidence of causality.',
                          'PSI >= 0.2, any out-of-range value, or missingness change >= 0.1 requests review; these are heuristics.',
                          'Labels and prospective/external outcomes are required to assess model performance.',
                          'This command neither trains nor activates a model.']}
    if min(len(reference),len(current))<30:
        result['warnings'].append('At least one cohort has fewer than 30 rows; distribution comparisons are unstable.')
    for name in NUMERIC:
        if name not in reference or name not in current:
            result['numeric'][name]={'status':'missing_column','reference_present':name in reference,'current_present':name in current}
            continue
        a,b=numeric_values(reference,name),numeric_values(current,name)
        av,bv=a.dropna().to_numpy(),b.dropna().to_numpy()
        entry={'reference_missing_fraction':float(a.isna().mean()),'current_missing_fraction':float(b.isna().mean()),
               'reference_median':float(np.median(av)) if len(av) else None,'current_median':float(np.median(bv)) if len(bv) else None}
        if not len(av) or not len(bv):
            entry.update(status='insufficient_values',psi=None,out_of_reference_range_fraction=None,review_required=True)
        else:
            bounds=np.unique(np.quantile(av,np.linspace(0,1,11)))
            # Constant references retain a narrow central bin so novel values are visible.
            if len(bounds)==1:
                epsilon=max(abs(float(bounds[0]))*1e-9,1e-9)
                edges=np.array([-np.inf,bounds[0]-epsilon,bounds[0]+epsilon,np.inf])
            else:
                edges=np.r_[-np.inf,bounds[1:-1],np.inf]
            ac=np.histogram(av,edges)[0].astype(float)+.5
            bc=np.histogram(bv,edges)[0].astype(float)+.5
            ap,bp=ac/ac.sum(),bc/bc.sum()
            psi=float(np.sum((bp-ap)*np.log(bp/ap)))
            outside=float(np.mean((bv<av.min())|(bv>av.max())))
            entry.update(status='compared',psi=psi,out_of_reference_range_fraction=outside,
                         review_required=bool(psi>=.2 or outside>0 or abs(entry['current_missing_fraction']-entry['reference_missing_fraction'])>=.1))
        result['numeric'][name]=entry
    for name in CATEGORICAL:
        if name not in reference or name not in current:
            result['categorical'][name]={'status':'missing_column'}
            continue
        a=reference[name].dropna().astype(str).value_counts(normalize=True)
        b=current[name].dropna().astype(str).value_counts(normalize=True)
        categories=sorted(set(a.index)|set(b.index))
        comparable=not a.empty and not b.empty
        distance=float(sum(abs(float(a.get(k,0))-float(b.get(k,0))) for k in categories)/2) if comparable else None
        unseen=sorted(set(b.index)-set(a.index))
        reference_missing=float(reference[name].isna().mean())
        current_missing=float(current[name].isna().mean())
        result['categorical'][name]={'status':'compared' if comparable else 'insufficient_values','total_variation_distance':distance,
            'unseen_categories':unseen,'reference_distribution':a.to_dict(),'current_distribution':b.to_dict(),
            'review_required':bool(not comparable or unseen or distance>=.2 or abs(current_missing-reference_missing)>=.1),
            'reference_missing_fraction':reference_missing,'current_missing_fraction':current_missing}
    if 'nct_id' in reference and 'nct_id' in current:
        a=reference.nct_id.dropna().astype(str).str.strip();b=current.nct_id.dropna().astype(str).str.strip()
        result['identity']={'overlapping_ids':len(set(a)&set(b)), 'reference_duplicate_ids':int(a.duplicated().sum()),
                            'current_duplicate_ids':int(b.duplicated().sum()),'reference_missing_ids':int(reference.nct_id.isna().sum()+(a=='').sum()),
                            'current_missing_ids':int(current.nct_id.isna().sum()+(b=='').sum())}
        if result['identity']['overlapping_ids']:
            result['warnings'].append('Cohorts share trial identifiers; do not treat these as independent external evaluation sets.')
        if result['identity']['current_duplicate_ids'] or result['identity']['reference_duplicate_ids']:
            result['warnings'].append('Duplicate trial identifiers require reconciliation before training.')
    else:
        result['warnings'].append('nct_id is absent; cohort overlap and identifier uniqueness could not be checked.')
    result['review_required']=bool(result['warnings'] or any(x.get('review_required',True) for family in ('numeric','categorical') for x in result[family].values()))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',required=True,type=Path)
    parser.add_argument('--current',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path,help='New JSON report; existing files are never overwritten')
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; select a new report path.')
    def load(path):
        return pd.read_parquet(path) if path.suffix.lower()=='.parquet' else pd.read_csv(path)
    try:
        report=compare_cohorts(load(args.reference),load(args.current))
    except (ValueError,OSError) as exc:
        parser.exit(2,f'Cohort comparison failed: {exc}\n')
    report['files']={key:{'name':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for key,path in [('reference',args.reference),('current',args.current)]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as out:
        json.dump(report,out,indent=2,allow_nan=False);out.write('\n')
    print(f'Compared {report["reference_rows"]} reference and {report["current_rows"]} current rows. Review required: {report["review_required"]}. No model was changed.')
    print(f'Report: {args.output}')


if __name__=='__main__':
    main()
