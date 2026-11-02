"""Cross-platform project commands; run `python -m src.cli --help`."""
import argparse
import json
from pathlib import Path
from .data import ROOT, generate_demo, prepare
from .config import DEMO_MODELS, DEMO_REPORTS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('demo', help='Generate explicitly synthetic practice sales')
    demo.add_argument('--output', type=Path, default=ROOT / 'data/raw/demo_sales.csv')
    demo.add_argument('--days', type=int, default=730)
    data = commands.add_parser('prepare', help='Validate CSV, save EDA and raw-source provenance')
    data.add_argument('--input', type=Path, default=ROOT / 'data/raw/demo_sales.csv')
    data.add_argument('--output', type=Path, default=ROOT / 'reports/week01')
    baseline = commands.add_parser('baseline', help='Evaluate naive/seasonal-naive seven-day validation forecasts')
    baseline.add_argument('--input', type=Path, default=ROOT / 'data/raw/demo_sales.csv')
    baseline.add_argument('--output', type=Path, default=ROOT / 'reports/week02')
    training = commands.add_parser('train', help='Compare models, choose on validation, evaluate test and fit serving model')
    training.add_argument('--input', type=Path, default=ROOT / 'data/raw/demo_sales.csv')
    training.add_argument('--output', type=Path, help='Report directory; custom output keeps models inside that run unless --models is supplied')
    training.add_argument('--models', type=Path, help='Explicit directory for fitted pipelines, registry and model card')
    forecast = commands.add_parser('forecast', help='Forecast from a trusted locally generated model')
    forecast.add_argument('--input', type=Path, default=ROOT / 'data/raw/demo_sales.csv')
    forecast.add_argument('--model', type=Path, default=DEMO_MODELS/'selected_model.joblib')
    forecast.add_argument('--output', type=Path, default=DEMO_REPORTS/'new_forecast.csv')
    forecast.add_argument('--horizon', type=int, default=7)
    inventory = commands.add_parser('inventory', help='Compute a clearly assumed inventory scenario for one series')
    inventory.add_argument('--forecast', type=Path, default=DEMO_REPORTS/'forecast.csv')
    inventory.add_argument('--store', required=True)
    inventory.add_argument('--item', required=True)
    inventory.add_argument('--lead-days', type=int, required=True)
    inventory.add_argument('--on-hand', type=float, required=True)
    inventory.add_argument('--daily-std', type=float, required=True)
    inventory.add_argument('--review-days', type=int, default=0)
    sql = commands.add_parser('sql', help='Export measured predictions to SQLite and query MAE by model')
    sql.add_argument('--run', type=Path, default=DEMO_REPORTS)
    args = parser.parse_args()
    try:
        if args.command == 'demo':
            result = generate_demo(args.output, args.days)
        elif args.command == 'baseline':
            from .forecasting import baseline_report
            result = baseline_report(args.input, args.output)
        elif args.command == 'train':
            from .data import read_sales, source_info
            from .modeling import train
            data_frame = read_sales(args.input)
            if args.output is not None:
                reports = args.output
                models = args.models if args.models is not None else reports/'models'
            elif args.models is not None:
                models = args.models
                reports = DEMO_REPORTS if models.resolve() == DEMO_MODELS.resolve() else models/'reports'
            elif args.input.resolve() == (ROOT/'data/raw/demo_sales.csv').resolve():
                reports, models = DEMO_REPORTS, DEMO_MODELS
            else:
                from .artifacts import dataset_signature, run_locations
                models, reports = run_locations(dataset_signature(data_frame), ROOT)
            result = train(data_frame, reports, source_info(args.input), model_directory=models)
            result = {**result, 'saved_to': {'models': str(models), 'reports': str(reports)}}
        elif args.command == 'forecast':
            from .data import read_sales
            from .modeling import load_bundle, forecast_saved
            result_frame = forecast_saved(read_sales(args.input), load_bundle(args.model), args.horizon)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            result_frame.to_csv(args.output, index=False)
            result = {'rows': len(result_frame), 'output': str(args.output)}
        elif args.command == 'inventory':
            import pandas as pd
            from .inventory import inventory_scenario
            forecasts = pd.read_csv(args.forecast, dtype={'store': str, 'item': str})
            selected = forecasts[(forecasts.store == args.store) & (forecasts.item == args.item)].sort_values('date')
            from .data import validate_sales
            selected = validate_sales(selected[['date', 'store', 'item', 'prediction']].rename(columns={'prediction': 'sales'}))
            result = inventory_scenario(selected.sales, lead_days=args.lead_days, on_hand=args.on_hand,
                                        daily_std=args.daily_std, review_days=args.review_days)
        elif args.command == 'sql':
            from .reporting import export_database
            result = export_database(args.run)
        else:
            result = prepare(args.input, args.output)
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f'Input error: {exc}\n')
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
