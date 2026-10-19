"""Portable entry to the preserved refinement probes; defaults to a dry run.

Only output locations are adapted. Frozen candidate grids, source hashes, role
IDs and original scripts stay unchanged. Existing release evidence is read-only.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task',choices=['phase','risk','phase-audit','risk-audit'],default='phase')
    parser.add_argument('--output',type=Path,default=ROOT/'results/refinement-dev')
    parser.add_argument('--development',type=Path,help='Use a previously completed development folder for audit')
    parser.add_argument('--execute',action='store_true',help='Explicitly fit or replay the selected research operation')
    args=parser.parse_args()
    output=args.output.resolve()
    if output==ROOT or ROOT in output.parents and output.parts[len(ROOT.parts)] != 'results':
        parser.error('Choose a new output under results/ or outside the release evidence.')
    evidence=ROOT/'examples/refinement-v5205-evidence'
    plan={'task':args.task,'execute':args.execute,'output':str(output),
          'source':str(ROOT/'data/registry-v5205-training'),
          'policy':'Frozen methods and original evidence are preserved; path overrides only. Audit cohorts are already inspected research evidence, not a new untouched test.'}
    if not args.execute:
        print(json.dumps(plan,indent=2));return 0
    from scripts import phase_accuracy_probe as phase
    from scripts import risk_accuracy_probe as risk
    from threadpoolctl import threadpool_limits
    phase.OUTPUT_ROOT=output;risk.OUTPUT_ROOT=output
    prepared=ROOT/'data/registry-v5205-training'
    with threadpool_limits(limits=1):
        if args.task=='phase':result=phase.run(prepared,output/'phase-v1',execute=True)
        elif args.task=='risk':result=risk.run(prepared,output/'risk-v1',execute=True)
        elif args.task=='phase-audit':
            from scripts import audit_phase_refinement as audit
            audit.OUTPUT_ROOT=output
            # The frozen exporter only writes a dedicated example directory.
            # Supply an isolated layout so the shipped approved bundle is never
            # overwritten. These are copies of public research artifacts.
            staging=output/'phase-export-layout'
            staging.mkdir(parents=True,exist_ok=False)
            shutil.copytree(ROOT/'examples/registry-v5205/phase',staging/'examples/registry-v5205/phase')
            helper=Path('src/clinical_trial_intelligence/models/phase_refinement.py')
            (staging/helper).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/helper,staging/helper)
            audit.ROOT=staging
            result=audit.run(args.development or evidence/'phase-v1',evidence/'phase-refinement-holdout',output/'phase-audit-v1',
                             prepared=prepared,export_dir=staging/'examples/registry-phase-refinement-v5205')
        else:
            from scripts import audit_risk_refinement as audit
            audit.OUTPUT_ROOT=output
            result=audit.run(args.development or evidence/'risk-v1',evidence/'risk-refinement-holdout',prepared,output/'risk-audit-v1')
    print(json.dumps(result,indent=2,allow_nan=False));return 0


if __name__=='__main__':raise SystemExit(main())
