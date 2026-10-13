"""Build fixture-only preview snapshots through the production workspace service."""
import json
from pathlib import Path
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import Settings
from backend.app.services.data_service import DatasetRegistry,SAMPLE_ID
from backend.app.services.research_workspace import ResearchWorkspace
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='cti-preview-') as folder:
    registry=DatasetRegistry(Settings(storage_dir=folder,database_url='',openai_api_key='',api_bearer_token=''))
    service=ResearchWorkspace(registry)
    rows=registry.frame(SAMPLE_ID)
    snapshots={str(nct):service.workspace(service.snapshot(SAMPLE_ID,str(nct))) for nct in rows.nct_id}
    assert len(snapshots)==5
    assert all(v['duration']['status']=='unavailable' and v['provenance']['is_fixture'] for v in snapshots.values())
    (ROOT/'frontend/src/demoResearch.json').write_text(json.dumps(snapshots,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Five production-computed fixture research snapshots written; no fitted predictions.')
