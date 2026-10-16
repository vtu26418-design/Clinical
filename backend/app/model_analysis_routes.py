"""Project-scoped downloads of independently recomputed saved-model evidence."""
from pathlib import Path
from typing import Literal
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from .config import PROJECT_ROOT


def attach_model_analysis(app, registry, require_token):
    router=APIRouter(dependencies=[Depends(require_token)])
    def render(directory, report_format):
        from src.clinical_trial_intelligence.model_analysis import analyze_experiment, render_analysis_html, render_analysis_csv
        try:
            report = analyze_experiment(directory)
        except (ValueError, OSError, KeyError, TypeError):
            raise HTTPException(409, 'Saved evaluation evidence is incomplete or invalid. Review the experiment before exporting.') from None
        headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                 'Content-Disposition':f'attachment; filename="model-analysis.{report_format}"'}
        if report_format=='html':
            headers['Content-Security-Policy']="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"
            return HTMLResponse(render_analysis_html(report),headers=headers)
        if report_format=='csv':
            return Response(render_analysis_csv(report),media_type='text/csv',headers=headers)
        return Response(json.dumps(report,allow_nan=False),media_type='application/json',headers=headers)

    @router.get('/api/v1/model-analysis')
    def model_analysis(task:Literal['duration','phase']='duration',model_id:str=Query(default='active',min_length=1,max_length=100),format:Literal['json','html','csv']='json'):
        resolver=getattr(registry,'approved_model_resolver',None)
        if callable(resolver):
            selected=resolver(task=task) if model_id=='active' else resolver(task=task,model_id=model_id)
            directory=Path(selected['directory'])
        else:
            # Standalone research API has no platform registry; permit only its
            # explicit trusted release entries, never an arbitrary query path.
            entries=json.loads((PROJECT_ROOT/'examples/approved-models-v5.json').read_text())['models']
            entry=next((value for value in entries if value.get('task')==task and (model_id=='active' or value.get('id')==model_id)),None)
            if not entry:raise HTTPException(404,'Approved saved model not found.')
            relative=Path(entry['directory']);directory=PROJECT_ROOT/relative
            if relative.is_absolute() or directory.is_symlink() or directory.resolve().parent!=(PROJECT_ROOT/'examples').resolve():
                raise HTTPException(409,'Saved model path is invalid.')
        return render(directory,format)

    @router.get('/api/v1/experiments/{experiment_id}/analysis')
    def experiment_analysis(experiment_id:str,format:Literal['json','html','csv']='json'):
        run=registry.get_experiment(experiment_id)
        if not run or run.get('status')!='completed':raise HTTPException(404,'Completed experiment not found in this project.')
        directory=registry.artifact_path(experiment_id)
        if directory.is_symlink() or directory.resolve().parent!=(registry.root/'experiments').resolve():
            raise HTTPException(409,'Saved experiment path is invalid.')
        return render(directory,format)

    app.include_router(router)
