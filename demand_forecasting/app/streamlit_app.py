"""Educational dashboard using the same tested functions as the CLI."""
from pathlib import Path
import hashlib
import io
import json
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
import plotly.express as px
import streamlit as st
from src.data import validate_sales, source_info, normalize_identifiers
from src.modeling import train, load_bundle, forecast_saved
from src.inventory import inventory_scenario

st.set_page_config(page_title='Demand Forecasting Lab', page_icon='📦', layout='wide')
st.title('Demand Forecasting & Inventory Lab')
st.caption('Four-week data science project · seven-day forecasts · reproducible evaluation')

with st.sidebar:
    st.header('Dataset')
    mode = st.radio('Data source', ['Configured CSV / bundled practice', 'Upload sales CSV'])
    if mode == 'Configured CSV / bundled practice':
        path = Path(os.environ.get('DEMAND_SALES_CSV', str(ROOT/'data/raw/demo_sales.csv')))
        try:
            raw = pd.read_csv(path, dtype={'store': str, 'item': str})
            provenance = source_info(path)
        except (OSError, ValueError) as exc:
            st.error(f'Configured CSV could not be read: {exc}')
            st.stop()
    else:
        uploaded = st.file_uploader('Sales CSV: date, store, item, sales', type=['csv'])
        st.caption('Use licensed data. Maximum file size: 50 MB. Select a bounded subset below.')
        if uploaded is None:
            st.info('Upload the Kaggle historical train.csv or another compatible sales file.')
            st.stop()
        if uploaded.size > 50*1024*1024:
            st.error('File exceeds 50 MB. Prepare a smaller store/item subset first.')
            st.stop()
        try:
            payload = uploaded.getvalue()
            raw = pd.read_csv(io.BytesIO(payload), dtype={'store': str, 'item': str})
        except Exception as exc:
            st.error(f'CSV could not be read: {exc}')
            st.stop()
        provenance = {'data_kind': 'user upload; provenance not independently verified', 'source_file': uploaded.name,
                      'source_sha256': hashlib.sha256(payload).hexdigest()}
    if not {'date', 'store', 'item', 'sales'}.issubset(raw.columns):
        st.error('Required columns: date, store, item, sales.')
        st.stop()
    try:
        raw = normalize_identifiers(raw)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    stores = sorted(raw.store.dropna().astype(str).unique())
    items = sorted(raw.item.dropna().astype(str).unique())
    selected_stores = st.multiselect('Training stores', stores, default=stores[:2])
    selected_items = st.multiselect('Training items', items, default=items[:4])

try:
    data = validate_sales(raw[raw.store.astype(str).isin(selected_stores) & raw.item.astype(str).isin(selected_items)])
    if data.groupby(['store', 'item']).ngroups > 20 or len(data) > 100_000:
        raise ValueError('For this learning app select at most 20 series and 100,000 rows.')
except ValueError as exc:
    st.error(str(exc))
    st.stop()

if 'synthetic' in provenance['data_kind'].lower():
    st.warning('SYNTHETIC PRACTICE DATA: these generated sales and their metrics are not real retail evidence. Import licensed real sales for your internship analysis.')
else:
    st.info('Uploaded sales: document licensing, source dates, missing periods and any stockout limitations in your report.')

signature = hashlib.sha256(data.to_csv(index=False).encode()).hexdigest()
st.caption(f'{len(data):,} observations · {data.groupby(["store", "item"]).ngroups} series · {data.date.min().date()} to {data.date.max().date()}')
st.caption('Training: all but final 56 days. Validation: next 28 days. Test: final 28 days. Each origin forecasts seven days recursively. Selection uses validation MAE only.')
if st.button('Train / evaluate', type='primary'):
    try:
        with st.spinner('Comparing baselines, linear regression and Random Forest…'):
            if 'run_directory' not in st.session_state:
                st.session_state.run_directory = tempfile.mkdtemp(prefix='demand-lab-')
            output = Path(st.session_state.run_directory)
            manifest = train(data, output, provenance)
            bundle = load_bundle(output/'model.joblib')
            forecasts = forecast_saved(data, bundle)
            st.session_state.result = {'signature': signature, 'manifest': manifest, 'forecasts': forecasts,
                                       'test': pd.read_csv(output/'test_predictions.csv', dtype={'store': str, 'item': str})}
    except ValueError as exc:
        st.error(str(exc))

result = st.session_state.get('result')
if result is not None and result['signature'] != signature:
    st.info('Dataset selection changed. Train again to avoid displaying stale forecasts.')
    result = None

left, right = st.columns(2)
with left:
    store = st.selectbox('Store', sorted(data.store.unique()))
with right:
    item = st.selectbox('Item', sorted(data[data.store == store].item.unique()))
selected = data[(data.store == store) & (data.item == item)]
overview, forecast_tab, inventory_tab, evaluation_tab = st.tabs(['Sales overview', 'Forecasts', 'Inventory scenarios', 'Model performance'])

with overview:
    st.subheader('Observed sales')
    st.plotly_chart(px.line(selected.tail(120), x='date', y='sales', labels={'sales': 'Units sold'}), use_container_width=True)
    weekday = selected.assign(weekday=selected.date.dt.day_name()).groupby('weekday', as_index=False).sales.mean()
    st.dataframe(weekday, hide_index=True)
    st.caption('Missing days are rejected; zeros remain zeros. Observed sales may understate true demand during stockouts.')

with forecast_tab:
    if result is None:
        st.info('Click Train / evaluate to generate forecasts and measured evaluation results.')
    else:
        manifest = result['manifest']
        forecasts = result['forecasts']
        current = forecasts[(forecasts.store == store) & (forecasts.item == item)]
        st.metric('Selected model', manifest['selected_model'])
        st.metric('Seven-day forecast units', f'{current.prediction.sum():.1f}')
        history_chart = selected.tail(45)[['date', 'sales']].rename(columns={'sales': 'units'}).assign(series='History')
        prediction_chart = current[['date', 'prediction']].rename(columns={'prediction': 'units'}).assign(series='Forecast')
        st.plotly_chart(px.line(pd.concat([history_chart, prediction_chart]), x='date', y='units', color='series'), use_container_width=True)
        st.dataframe(current, hide_index=True)
        st.download_button('Download all forecast CSV', forecasts.to_csv(index=False), 'forecast.csv', 'text/csv')
        st.caption('Predictions are nonnegative expected units, not guaranteed sales. The serving model is refitted on all history after held-out evaluation.')

with inventory_tab:
    st.warning('WHAT-IF SCENARIO: the sales dataset supplies no observed stock or supplier lead times. Every input below is an explicit assumption.')
    a, b, c = st.columns(3)
    with a:
        lead = st.number_input('Assumed lead time (days)', min_value=1, max_value=7, value=3)
        review = st.number_input('Assumed review coverage (days)', min_value=0, max_value=7-int(lead), value=0)
        stock = st.number_input('Assumed stock on hand', min_value=0., value=20.)
    with b:
        ordered = st.number_input('Assumed outstanding order units', min_value=0., value=0.)
        backorders = st.number_input('Assumed backorder units', min_value=0., value=0.)
        variability = st.number_input('Assumed daily demand standard deviation', min_value=0., value=5.)
    with c:
        service = st.slider('Assumed service-level target', min_value=.50, max_value=.999, value=.95, step=.001)
        pack = st.number_input('Assumed pack size', min_value=1, value=1)
        minimum = st.number_input('Assumed minimum order units', min_value=0., value=0.)
    if st.button('Calculate scenario'):
        if result is None:
            st.info('Train the model first.')
        else:
            current = result['forecasts']
            current = current[(current.store == store) & (current.item == item)].sort_values('date')
            scenario = inventory_scenario(current.prediction, lead_days=int(lead), review_days=int(review),
                on_hand=stock, on_order=ordered, backorders=backorders, daily_std=variability,
                service_level=service, pack_size=int(pack), minimum_order=minimum)
            st.json(scenario)
            st.download_button('Download scenario JSON', json.dumps(scenario, indent=2), 'inventory_scenario.json', 'application/json')
    st.caption('Safety stock uses a normal approximation and independent daily-demand assumption. This service target is not a validated stockout probability.')

with evaluation_tab:
    if result is None:
        st.info('Train first to see measured validation and held-out test errors.')
    else:
        manifest = result['manifest']
        name = manifest['selected_model']
        columns = st.columns(3)
        columns[0].metric('Validation MAE', f'{manifest["validation_metrics"][name]["mae"]:.3f}')
        columns[1].metric('Test MAE', f'{manifest["test_metrics"][name]["mae"]:.3f}')
        columns[2].metric('Test RMSE', f'{manifest["test_metrics"][name]["rmse"]:.3f}')
        comparison = []
        for phase in ['validation', 'test']:
            for model, scores in manifest[f'{phase}_metrics'].items():
                comparison.append({'phase': phase, 'model': model, **scores})
        st.dataframe(pd.DataFrame(comparison), hide_index=True)
        errors = result['test']
        errors = errors[(errors.model == name) & (errors.store == store) & (errors.item == item)].copy()
        errors['error_units'] = errors.prediction-errors.actual
        st.plotly_chart(px.line(errors, x='date', y=['actual', 'prediction'], title='Selected model: held-out actual versus prediction'), use_container_width=True)
        st.plotly_chart(px.bar(errors, x='date', y='error_units', title='Held-out signed error (prediction − actual)'), use_container_width=True)
        st.download_button('Download evaluation manifest', json.dumps(manifest, indent=2), 'manifest.json', 'application/json')
        st.download_button('Download held-out predictions', result['test'].to_csv(index=False), 'test_predictions.csv', 'text/csv')
        st.caption('MAE/RMSE: units sold. Bias: prediction minus actual. WAPE: percentage, undefined when actual totals are zero. Reported test metrics belong to pre-test evaluation fits. No model can guarantee inventory savings.')
