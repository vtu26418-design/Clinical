import importlib.util
import pytest


def service():
    assert importlib.util.find_spec('backend.app.services.protocol_service') is not None, 'Protocol evidence service is missing'
    from backend.app.services import protocol_service
    return protocol_service


def test_extracted_evidence_keeps_source_page_and_hash():
    raw = b'PHASE II STUDY\nTarget enrollment: 120 participants\nPrimary endpoint: change in score\nInclusion criteria: adults aged 18 years.\n'
    result = service().extract_document(raw, 'protocol.txt')
    assert result['source_sha256'] and len(result['source_sha256']) == 64
    assert result['features']['phase'] == 'PHASE2'
    assert result['features']['enrollment'] == 120
    assert all(x['page'] == 1 and x['quote'] for x in result['evidence'])
    assert result['review_status'] == 'pending'


def test_missing_domains_stay_unknown():
    result = service().extract_document(b'Purpose of this study is to explore feasibility.', 'note.txt')
    assert len(result['domains']) == 7
    assert result['domains']['patient']['status'] == 'unknown'
    assert result['features'].get('enrollment') is None
    assert result['composite_score'] is None


@pytest.mark.parametrize('raw,name', [(b'abc', 'x.exe'), (b'', 'empty.txt'), (b'%PDF bad', 'x.pdf')])
def test_invalid_documents_rejected(raw, name):
    with pytest.raises(ValueError):
        service().extract_document(raw, name)


def test_pretrial_availability_unknown_and_future_fail_closed():
    audit = service().availability_audit('2025-01-01', {'enrollment': None, 'phase': '2025-01-02', 'title': '2024-12-31'})
    assert audit['eligible'] is False
    assert audit['unknown'] == ['enrollment']
    assert audit['late'] == ['phase']
    assert audit['accepted'] == ['title']


def test_pretrial_availability_empty_does_not_pass():
    assert service().availability_audit('2025-01-01', {})['eligible'] is False


def test_domain_formula_requires_all_domains_and_valid_weights():
    svc = service()
    scores = {k: 40.0 for k in svc.DOMAIN_NAMES}
    weights = {k: 1.0 for k in svc.DOMAIN_NAMES}
    assert svc.domain_score(scores, weights)['score'] == 40.0
    scores['patient'] = None
    assert svc.domain_score(scores, weights)['score'] is None
    weights['site'] = -1
    with pytest.raises(ValueError):
        svc.domain_score(scores, weights)


def test_version_diff_preserves_direction():
    result = service().compare_texts('Enrollment: 100\nOne endpoint', 'Enrollment: 150\nOne endpoint')
    assert 'Enrollment: 100' in result['removed']
    assert 'Enrollment: 150' in result['added']
    assert result['amendment_probability'] is None
