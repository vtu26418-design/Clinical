"""Resumable acquisition of authentic public registry records, with immutable raw pages.

This never trains a model. It preserves date precision and source enrollment type.
Current registry snapshots do not establish prediction-time feature availability.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from backend.app.services.clinicaltrials_service import _record,ENDPOINT

QUERY='AREA[StudyType]INTERVENTIONAL AND AREA[OverallStatus]COMPLETED AND AREA[InterventionType]DRUG AND (AREA[Phase]PHASE1 OR AREA[Phase]PHASE2 OR AREA[Phase]PHASE3 OR AREA[Phase]PHASE4)'
FIELDS='NCTId,BriefTitle,OfficialTitle,StudyType,Phase,OverallStatus,StartDate,StartDateType,CompletionDate,CompletionDateType,PrimaryCompletionDate,PrimaryCompletionDateType,EnrollmentCount,EnrollmentType,ArmGroupLabel,InterventionType,PrimaryOutcomeMeasure,SecondaryOutcomeMeasure,BriefSummary,EligibilityCriteria,StudyFirstSubmitDate,StudyFirstPostDate,LastUpdatePostDate,DesignAllocation,DesignMasking,DesignPrimaryPurpose,LeadSponsorClass,Condition,LocationFacility,LocationCountry'
SORT='StartDate:asc'
MAX_PAGE_BYTES=64*1024*1024


def digest(data):return hashlib.sha256(data).hexdigest()
def timestamp():return datetime.now(timezone.utc).isoformat()


def canonical_record(study):
    protocol=study.get('protocolSection') or {}
    row=_record(study);design=protocol.get('designModule') or {};status=protocol.get('statusModule') or {}
    interventions=protocol.get('armsInterventionsModule') or {};details=design.get('designInfo') or {}
    phases=design.get('phases') or []
    if not re.fullmatch(r'NCT\d{8}',str(row.get('nct_id') or '')):raise ValueError('Source NCT identifier is invalid.')
    if row['status']!='COMPLETED' or row['study_type']!='INTERVENTIONAL' or not {'PHASE1','PHASE2','PHASE3','PHASE4'}.intersection(phases):raise ValueError('Source record is outside the frozen registry scope.')
    kinds=sorted({item.get('type') for item in interventions.get('interventions',[]) if item.get('type')})
    if 'DRUG' not in kinds:raise ValueError('Source record is outside the DRUG scope.')
    criteria=row.get('eligibility_criteria') or ''
    locations=(protocol.get('contactsLocationsModule') or {}).get('locations')
    countries=sorted({item.get('country') for item in locations or [] if item.get('country')})
    row.update({
        'reported_enrollment':row.get('enrollment'),
        'planned_enrollment':row.get('enrollment') if row.get('enrollment_type')=='ESTIMATED' else None,
        'design_allocation':details.get('allocation'),'design_masking':(details.get('maskingInfo') or {}).get('masking'),
        'primary_purpose':details.get('primaryPurpose'),
        'sponsor_class':((protocol.get('sponsorCollaboratorsModule') or {}).get('leadSponsor') or {}).get('class'),
        'condition_text':' | '.join((protocol.get('conditionsModule') or {}).get('conditions') or []),
        'intervention_types':'|'.join(kinds),
        'intervention_count':len(interventions['interventions']) if 'interventions' in interventions else None,
        'eligibility_line_count':sum(bool(line.strip()) for line in criteria.splitlines()) if criteria.strip() else None,
        'eligibility_word_count':len(re.findall(r'\b\w+\b',criteria)) if criteria.strip() else None,
        'eligibility_char_count':len(criteria) if criteria.strip() else None,
        'study_first_posted_date':(status.get('studyFirstPostDateStruct') or {}).get('date'),
        'study_first_submitted_date':status.get('studyFirstSubmitDate'),
        'primary_completion_date':(status.get('primaryCompletionDateStruct') or {}).get('date'),
        'primary_completion_date_type':(status.get('primaryCompletionDateStruct') or {}).get('type'),
        'reported_sites':len(locations) if locations is not None else None,
        'reported_countries':len(countries) if countries else None,
        'country_names':'|'.join(countries),
    })
    return row


def fetch_response(params,remaining):
    url=ENDPOINT+'?'+urlencode(params)
    request=Request(url,headers={'Accept':'application/json','User-Agent':'CTI-Research-Cohort/5.2.0.5'})
    for attempt in range(5):
        try:
            with urlopen(request,timeout=60) as response:
                if not response.url.startswith(ENDPOINT+'?'):raise ValueError('Unexpected source redirect.')
                payload=response.read(min(MAX_PAGE_BYTES,remaining)+1)
                if len(payload)>min(MAX_PAGE_BYTES,remaining):raise ValueError('Acquisition byte bound reached; no partial page was saved.')
                return payload,response.headers.get('Date','')
        except HTTPError as error:
            if error.code not in (429,500,502,503,504) or attempt==4:raise
        except (URLError,TimeoutError):
            if attempt==4:raise
        time.sleep(min(2**attempt,16))
    raise RuntimeError('Source acquisition did not complete.')


def _write_json(path,value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(path)


def _safe(directory,name,pattern):
    if not isinstance(name,str) or not re.fullmatch(pattern,name):raise ValueError('Unsafe source manifest filename.')
    path=directory/name
    if path.is_symlink() or not path.is_file() or directory.resolve() not in path.resolve().parents:raise ValueError('Source manifest file is unavailable or unsafe.')
    return path


def _read_shards(directory,state,verify):
    frames=[]
    for page in state.get('pages',[]):
        raw=_safe(directory,page['file'],r'raw/page-\d{6}\.json\.gz')
        shard=_safe(directory,page['canonical_file'],r'shards/part-\d{6}\.parquet')
        if verify:
            payload=raw.read_bytes()
            if digest(payload)!=page['gzip_sha256']:raise ValueError('Raw response checksum mismatch.')
            if page['uncompressed_bytes']>MAX_PAGE_BYTES:raise ValueError('Saved source page exceeds the byte bound.')
            data=gzip.decompress(payload)
            if len(data)!=page['uncompressed_bytes'] or digest(data)!=page['response_sha256']:raise ValueError('Raw response checksum mismatch.')
            if digest(shard.read_bytes())!=page['canonical_sha256']:raise ValueError('Canonical shard checksum mismatch.')
        frame=pd.read_parquet(shard)
        if len(frame)!=page['canonical_rows']:raise ValueError('Canonical shard row count differs.')
        frames.append(frame)
    return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()


def load_cohort(directory,verify=True):
    directory=Path(directory)
    state=json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
    if not state.get('acquisition_complete'):raise ValueError('Acquisition is incomplete; no complete-cohort claim is possible.')
    frame=_read_shards(directory,state,verify)
    if len(frame)!=state['rows'] or frame.nct_id.duplicated().any():raise ValueError('Source ID/count reconciliation failed.')
    return frame


def acquire(directory,maximum=120000,page_size=1000,max_bytes=2*1024**3,*,resume=False,fetch=fetch_response,pause_seconds=0.2):
    directory=Path(directory)
    if not 1<=maximum<=1_000_000 or not 1<=page_size<=1000 or max_bytes<1024:raise ValueError('Invalid acquisition bounds.')
    checkpoint=directory/'acquisition.json'
    if resume:
        state=json.loads(checkpoint.read_text(encoding='utf-8'))
        if any(state.get(key)!=value for key,value in {'query':QUERY,'fields':FIELDS,'sort':SORT,'maximum':maximum,'page_size':page_size}.items()):raise ValueError('Resume settings differ from the frozen acquisition.')
        existing=_read_shards(directory,state,True)
        ids=set(existing.nct_id) if len(existing) else set()
        if state.get('acquisition_complete'):return state
    else:
        directory.mkdir(parents=True,exist_ok=False);(directory/'raw').mkdir();(directory/'shards').mkdir()
        state={'dataset_name':'ClinicalTrials.gov completed interventional drug-trial registry cohort','schema_version':1,'source':'ClinicalTrials.gov API v2','endpoint':ENDPOINT,'query':QUERY,'fields':FIELDS,'sort':SORT,'maximum':maximum,'page_size':page_size,'acquisition_started_at':timestamp(),'baseline_provenance':False,'is_fixture':False,'snapshot_type':'latest registry state','acquisition_complete':False,'rows':0,'raw_rows':0,'duplicate_ids':0,'duplicate_nct_ids':[],'pages':[],'next_page_token':None,'uncompressed_bytes':0,'events':[]};ids=set()
        _write_json(checkpoint,state)
    try:
        while len(ids)<maximum:
            number=len(state['pages'])+1
            params={'query.term':QUERY,'fields':FIELDS,'sort':SORT,'format':'json','countTotal':'true','pageSize':min(page_size,maximum-len(ids))}
            if state['next_page_token']:params['pageToken']=state['next_page_token']
            remaining=max_bytes-state['uncompressed_bytes']
            if remaining<=0:raise ValueError('Total acquisition byte bound reached.')
            payload,http_date=fetch(params,remaining)
            if len(payload)>min(MAX_PAGE_BYTES,remaining):raise ValueError('Source response exceeds the byte bound.')
            parsed=json.loads(payload)
            if not isinstance(parsed,dict) or not isinstance(parsed.get('studies'),list):raise ValueError('Unexpected source response schema.')
            studies=parsed['studies'];token=parsed.get('nextPageToken')
            if len(studies)>params['pageSize']:raise ValueError('Source returned more rows than requested.')
            if token and (not studies or token==state['next_page_token'] or any(page.get('next_page_token')==token for page in state['pages'])):raise ValueError('Source pagination did not advance.')
            rows=[];new_ids=set();duplicates=[]
            for study in studies:
                row=canonical_record(study)
                if row['nct_id'] in ids or row['nct_id'] in new_ids:duplicates.append(row['nct_id']);continue
                new_ids.add(row['nct_id']);rows.append(row)
            raw_name=f'raw/page-{number:06d}.json.gz';canonical_name=f'shards/part-{number:06d}.parquet'
            compressed=gzip.compress(payload,mtime=0)
            with (directory/raw_name).open('xb') as stream:stream.write(compressed)
            frame=pd.DataFrame(rows) if rows else pd.DataFrame({'nct_id':pd.Series(dtype=str)})
            with (directory/canonical_name).open('xb') as stream:frame.to_parquet(stream,index=False,compression='zstd')
            page={'file':raw_name,'request_parameters':params,'retrieved_at':timestamp(),'http_date':http_date,'rows':len(studies),'uncompressed_bytes':len(payload),'response_sha256':digest(payload),'gzip_sha256':digest(compressed),'canonical_file':canonical_name,'canonical_rows':len(rows),'canonical_sha256':digest((directory/canonical_name).read_bytes()),'next_page_token':token}
            ids.update(new_ids);state['pages'].append(page);state['rows']=len(ids);state['raw_rows']+=len(studies);state['duplicate_ids']+=len(duplicates);state['duplicate_nct_ids'].extend(duplicates);state['uncompressed_bytes']+=len(payload);state['next_page_token']=token;state['last_reported_total_count']=parsed.get('totalCount',state.get('last_reported_total_count'));state['updated_at']=timestamp();state['acquisition_complete']=not token
            _write_json(checkpoint,state)
            print(f'Page {number}: {len(ids):,} unique authentic records; {state["duplicate_ids"]} duplicate IDs recorded.',flush=True)
            if not token:break
            if pause_seconds:time.sleep(pause_seconds)
        state.update({'retrieved_at':timestamp(),'sampling_method':'All returned records in the frozen official query, ordered by source start date, until pagination ends or declared maximum. Source availability/changes may affect coverage.','date_policy':'Preserve exact/year/month source strings and ACTUAL/ESTIMATED types; no date imputation.','enrollment_policy':'planned_enrollment uses only explicitly ESTIMATED enrollment; reported/current enrollment is not an original plan.','eligibility_feature_method':'Lexical nonempty-line, Unicode-word and character counts from eligibility text; not counts of clinical conditions.','site_policy':'Counts refer to locations/countries present in this current source projection; not planned sites or recruitment performance.','data_use':'Public ClinicalTrials.gov registry records; cite the source and review its terms. No blanket third-party text license is asserted.','source_documentation':'https://clinicaltrials.gov/data-api/api','terms_url':'https://clinicaltrials.gov/about-site/terms-conditions','limitations':['Current snapshots do not prove trial-start feature availability.','Completed-only drug-trial scope omits censored outcomes and does not represent all trials.','No patient-level data, original planned completion, treatment benefit or clinical validation is inferred.','First-registered date is not a timestamp for every current feature.','Counts are an acquisition inventory; training eligibility and temporal purging must be reported separately.']})
        _write_json(checkpoint,state);_write_json(directory/'metadata.json',state)
        return state
    except Exception as error:
        state['events'].append({'at':timestamp(),'status':'interrupted','error_type':type(error).__name__});_write_json(checkpoint,state)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--maximum',type=int,default=120000);parser.add_argument('--page-size',type=int,default=1000);parser.add_argument('--max-bytes',type=int,default=2*1024**3);parser.add_argument('--resume',action='store_true');parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    try:
        if args.verify_only:
            frame=load_cohort(args.output,verify=True);print(f'Verified {len(frame):,} unique source records.');return 0
        state=acquire(args.output,args.maximum,args.page_size,args.max_bytes,resume=args.resume)
        print(json.dumps({'rows':state['rows'],'acquisition_complete':state['acquisition_complete'],'duplicate_ids':state['duplicate_ids'],'raw_pages':len(state['pages'])},indent=2))
        return 0 if state['acquisition_complete'] else 2
    except (OSError,ValueError,KeyError,TypeError) as error:parser.exit(2,f'Acquisition stopped: {error}. Preserved pages can be resumed with the same settings.\n')


if __name__=='__main__':raise SystemExit(main())
