import numpy as np
import pandas as pd
import pytest
from src.data import validate_sales, prepare, generate_demo


def sample():
    return pd.DataFrame({'date': pd.date_range('2024-01-01', periods=4), 'store': [1]*4, 'item': [2]*4, 'sales': [0, 2, 3, 4]})


def test_preserves_zeros_and_normalizes_identifiers():
    result = validate_sales(sample())
    assert result.sales.tolist() == [0, 2, 3, 4]
    assert result.store.tolist() == ['1']*4


def test_duplicate_observation_is_not_silently_summed():
    with pytest.raises(ValueError, match='Duplicate'):
        validate_sales(pd.concat([sample(), sample().iloc[[0]]]))


def test_missing_days_are_not_treated_as_zero_sales():
    with pytest.raises(ValueError, match='Missing daily'):
        validate_sales(sample().drop(index=1))


@pytest.mark.parametrize('bad', [np.nan, np.inf, -1, 'invalid'])
def test_rejects_invalid_sales(bad):
    data = sample().astype({'sales': object})
    data.loc[0, 'sales'] = bad
    with pytest.raises(ValueError, match='sales'):
        validate_sales(data)


@pytest.mark.parametrize('bad', [None, '', '   '])
def test_rejects_missing_identifiers(bad):
    data = sample().astype({'item': object})
    data.loc[0, 'item'] = bad
    with pytest.raises(ValueError, match='identifiers'):
        validate_sales(data)


def test_prepare_records_raw_hash_and_keeps_source_bytes(tmp_path):
    source = tmp_path / 'sales.csv'
    sample().to_csv(source, index=False)
    before = source.read_bytes()
    report = prepare(source, tmp_path / 'out')
    assert report['rows'] == 4
    assert len(report['source_sha256']) == 64
    assert source.read_bytes() == before
    assert (tmp_path / 'out' / 'cleaned.csv').is_file()
    assert (tmp_path / 'out' / 'sales_overview.png').is_file()


def test_demo_is_reproducible_and_labelled(tmp_path):
    first = generate_demo(tmp_path / 'one.csv', days=60)
    second = generate_demo(tmp_path / 'two.csv', days=60)
    assert first['data_kind'] == 'synthetic practice; not observed retail sales'
    assert first['source_sha256'] == second['source_sha256']
