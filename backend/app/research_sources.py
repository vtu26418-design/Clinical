"""Bounded read-only public evidence adapters; callers never choose an upstream URL."""
from __future__ import annotations

import html
import json
import re
import time
from typing import Literal
from urllib.parse import quote

import httpx

from .services.data_service import now

Source = Literal['clinicaltrials', 'pubmed', 'openfda']
MAX_RESPONSE_BYTES = 2_000_000
SOURCES = {'clinicaltrials':'ClinicalTrials.gov', 'pubmed':'PubMed', 'openfda':'openFDA drug labels'}


class SourceUnavailable(Exception):
    """Safe upstream failure that contains neither raw provider bodies nor URLs."""


def clean_text(value, limit=4000):
    if not isinstance(value, str):
        return ''
    value = html.unescape(value[:limit * 4])
    value = re.sub(r'<[^>]*>', ' ', value)
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
    return re.sub(r'\s+', ' ', value).strip()[:limit]


def citation_url(source, identifier):
    patterns = {'clinicaltrials':r'NCT\d{8}', 'pubmed':r'\d{1,12}', 'openfda':r'[a-zA-Z0-9_-]{1,100}'}
    if source not in patterns or not re.fullmatch(patterns[source], identifier):
        raise ValueError('Invalid evidence identifier.')
    if source == 'clinicaltrials':
        return 'https://clinicaltrials.gov/study/' + identifier
    if source == 'pubmed':
        return 'https://pubmed.ncbi.nlm.nih.gov/' + identifier + '/'
    return 'https://api.fda.gov/drug/label.json?search=id:' + quote('"' + identifier + '"', safe='')


def _get(client, url, params, *, empty_404=False):
    started = time.monotonic()
    with client.stream('GET', url, params=params, follow_redirects=False) as response:
        no_matches = empty_404 and response.status_code == 404
        if not no_matches:
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError('Unexpected upstream status.')
        raw = bytearray()
        for chunk in response.iter_bytes(chunk_size=65536):
            raw.extend(chunk)
            if len(raw) > MAX_RESPONSE_BYTES or time.monotonic() - started > 12:
                raise ValueError('Upstream response limit reached.')
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError('Expected upstream object.')
        if no_matches:
            # Distinguish the documented openFDA empty search from routing/errors.
            error = result.get('error', {})
            if not isinstance(error,dict) or error.get('code') != 'NOT_FOUND' or error.get('message') != 'No matches found!':
                raise ValueError('Unexpected upstream 404.')
            return {'results':[], 'meta':{'results':{'total':0}}}
        return result


def _total(value):
    try:
        number = int(value)
        return number if number >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _item(source, identifier, title, summary, published, stamp):
    return {'source':source, 'id':identifier, 'title':clean_text(title, 500) or identifier,
            'summary':clean_text(summary), 'url':citation_url(source, identifier),
            'citation':SOURCES[source] + ' · ' + identifier,
            'published_at':clean_text(published, 80) or None, 'retrieved_at':stamp}


def search(source: Source, query: str, limit: int = 10, *, client=None):
    if source not in SOURCES or not 1 <= limit <= 20 or not query.strip() or len(query) > 300:
        raise ValueError('Invalid source, query or limit.')
    if client is None:
        with httpx.Client(timeout=httpx.Timeout(10, connect=5), follow_redirects=False,
                          headers={'Accept':'application/json','User-Agent':'CTI-Research-Workbench/5.2'}) as upstream:
            return search(source, query, limit, client=upstream)
    stamp = now()
    try:
        if source == 'clinicaltrials':
            data = _get(client, 'https://clinicaltrials.gov/api/v2/studies',
                        {'query.term':query,'pageSize':limit,'countTotal':'true','format':'json'})
            records = data['studies']
            if not isinstance(records, list):
                raise ValueError('Invalid studies.')
            items = []
            for record in records[:limit]:
                protocol = record['protocolSection']
                identification = protocol['identificationModule']
                identifier = identification['nctId']
                published = protocol.get('statusModule', {}).get('lastUpdatePostDateStruct', {}).get('date')
                items.append(_item(source, identifier, identification.get('briefTitle'),
                    protocol.get('descriptionModule', {}).get('briefSummary'), published, stamp))
            total = _total(data.get('totalCount'))
        elif source == 'pubmed':
            found = _get(client, 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi',
                {'db':'pubmed','term':query,'retmode':'json','retmax':limit,'sort':'relevance'})['esearchresult']
            ids = found['idlist']
            if not isinstance(ids, list) or any(not isinstance(i,str) or not re.fullmatch(r'\d{1,12}', i) for i in ids[:limit]):
                raise ValueError('Invalid PubMed identifiers.')
            ids = ids[:limit]
            items = []
            if ids:
                summaries = _get(client, 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi',
                    {'db':'pubmed','id':','.join(ids),'retmode':'json'})['result']
                for identifier in ids:
                    record = summaries[identifier]
                    # ESummary supplies bibliographic metadata, not an article abstract.
                    authors = ', '.join(clean_text(a.get('name'),100) for a in record.get('authors', [])[:6])
                    summary = ' · '.join(filter(None,[clean_text(record.get('fulljournalname'),300),authors]))
                    items.append(_item(source, identifier, record.get('title'),summary,record.get('pubdate'),stamp))
            total = _total(found.get('count'))
        else:
            # Quote user text as a literal phrase; never accept an openFDA query expression.
            phrase = query.replace('\\','\\\\').replace('"','\\"')
            data = _get(client, 'https://api.fda.gov/drug/label.json',
                {'search':'(openfda.brand_name:"'+phrase+'" OR indications_and_usage:"'+phrase+'")','limit':limit}, empty_404=True)
            records = data['results']
            if not isinstance(records, list):
                raise ValueError('Invalid drug labels.')
            items = []
            for record in records[:limit]:
                brands = record.get('openfda',{}).get('brand_name',[])
                indications = record.get('indications_and_usage',[])
                if not isinstance(brands,list) or not isinstance(indications,list):
                    raise ValueError('Invalid label content.')
                items.append(_item(source,record['id'],', '.join(clean_text(b,100) for b in brands[:5]),
                    ' '.join(clean_text(v,2000) for v in indications[:2]),record.get('effective_time'),stamp))
            total = _total(data.get('meta',{}).get('results',{}).get('total'))
        return {'source':source,'query':query,'items':items,'total':total,'retrieved_at':stamp,'limit':limit}
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        raise SourceUnavailable(SOURCES[source] + ' is unavailable or returned an invalid response. Retry later.') from None
