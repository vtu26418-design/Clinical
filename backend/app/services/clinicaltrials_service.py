"""ClinicalTrials.gov v2 adapter; no generated records and no silent fallback."""
import json
from datetime import datetime, timezone
import httpx
import pandas as pd

ENDPOINT = 'https://clinicaltrials.gov/api/v2/studies'


class RegistryImportError(RuntimeError):
    pass


def _record(study: dict) -> dict:
    protocol = study.get('protocolSection') or {}
    identification = protocol.get('identificationModule') or {}
    design = protocol.get('designModule') or {}
    status = protocol.get('statusModule') or {}
    outcomes = protocol.get('outcomesModule') or {}
    eligibility = protocol.get('eligibilityModule') or {}
    description = protocol.get('descriptionModule') or {}
    arms_module = protocol.get('armsInterventionsModule') or {}
    completion = status.get('completionDateStruct') or {}
    start = status.get('startDateStruct') or {}
    # Counts map directly from source arrays. Eligibility/text metrics need a
    # documented NLP method, so missing metrics stay missing instead of invented.
    return {
        'nct_id': identification.get('nctId'),
        'title': identification.get('briefTitle') or identification.get('officialTitle'),
        'study_type': design.get('studyType', 'Unknown'),
        'phase': '|'.join(design.get('phases') or []) or 'Not reported',
        'enrollment': (design.get('enrollmentInfo') or {}).get('count'),
        'enrollment_type': (design.get('enrollmentInfo') or {}).get('type'),
        'status': status.get('overallStatus', 'Unknown'),
        'start_date': start.get('date'),
        'start_date_type': start.get('type'),
        'completion_date': completion.get('date'),
        'completion_date_type': completion.get('type', 'Not reported'),
        'number_of_arms': len(arms_module['armGroups']) if 'armGroups' in arms_module else None,
        'primary_outcomes': len(outcomes['primaryOutcomes']) if 'primaryOutcomes' in outcomes else None,
        'secondary_outcomes': len(outcomes['secondaryOutcomes']) if 'secondaryOutcomes' in outcomes else None,
        'criteria_count': None,
        'text_complexity': None,
        'brief_summary': description.get('briefSummary', ''),
        'eligibility_criteria': eligibility.get('eligibilityCriteria', ''),
        'source_url': f"https://clinicaltrials.gov/study/{identification.get('nctId', '')}",
        'last_update_posted_date': (status.get('lastUpdatePostDateStruct') or {}).get('date'),
    }


def fetch_trials(query: str, maximum: int, max_bytes: int) -> tuple[bytes, pd.DataFrame, dict]:
    pages = []
    rows = []
    seen_tokens = set()
    token = None
    total_bytes = 0
    try:
        with httpx.Client(timeout=httpx.Timeout(25.0, connect=10.0), follow_redirects=False) as client:
            while len(rows) < maximum:
                params = {'query.term': query, 'format': 'json', 'pageSize': min(100, maximum - len(rows))}
                if token:
                    params['pageToken'] = token
                with client.stream('GET', ENDPOINT, params=params, headers={'Accept': 'application/json'}) as response:
                    response.raise_for_status()
                    chunks = []
                    for chunk in response.iter_bytes():
                        total_bytes += len(chunk)
                        if total_bytes > max_bytes:
                            raise RegistryImportError('Registry response exceeds the upload size limit; narrow your query.')
                        chunks.append(chunk)
                    payload = b''.join(chunks)
                parsed = json.loads(payload)
                if not isinstance(parsed, dict) or not isinstance(parsed.get('studies'), list):
                    raise RegistryImportError('ClinicalTrials.gov returned an unexpected response format.')
                pages.append(payload.decode('utf-8'))
                rows.extend(_record(study) for study in parsed['studies'][:maximum - len(rows)])
                token = parsed.get('nextPageToken')
                if not token:
                    break
                if token in seen_tokens:
                    raise RegistryImportError('ClinicalTrials.gov repeated a page token; import was not saved.')
                seen_tokens.add(token)
    except RegistryImportError:
        raise
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise RegistryImportError('ClinicalTrials.gov import failed. Check connectivity, query syntax, and registry availability; no dataset was saved.') from exc
    if not rows:
        raise RegistryImportError('ClinicalTrials.gov returned no matching studies. Refine the query.')
    # Each page is preserved byte-for-byte inside this JSON envelope; no remote
    # response field is modified. Reconstruct with pages[i].encode("utf-8").
    raw = json.dumps({'raw_response_pages': pages}, ensure_ascii=False).encode('utf-8')
    provenance = {'endpoint': ENDPOINT, 'query': query, 'requested_maximum': maximum, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'snapshot_type': 'latest registry state', 'baseline_provenance': False, 'response_pages': len(pages)}
    return raw, pd.DataFrame(rows), provenance
