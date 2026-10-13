"""Bundle the explicitly fixture-only Vite build into one offline HTML file."""
from pathlib import Path
import base64
import re
root=Path(__file__).resolve().parents[1]
dist=root/'frontend/dist-preview'
page=(dist/'index.html').read_text()
for src in re.findall(r'<script[^>]+src="([^"]+)"[^>]*></script>',page):
    js=(dist/src.lstrip('/')).read_text().replace('</script','<\\/script')
    page=re.sub(r'<script[^>]+src="'+re.escape(src)+r'"[^>]*></script>',lambda _: '<script type="module">'+js+'</script>',page)
for href in re.findall(r'<link[^>]+href="([^"]+\.css)"[^>]*>',page):
    css=(dist/href.lstrip('/')).read_text()
    page=re.sub(r'<link[^>]+href="'+re.escape(href)+r'"[^>]*>',lambda _: '<style>'+css+'</style>',page)
icon=base64.b64encode((dist/'favicon.svg').read_bytes()).decode()
page=page.replace('/favicon.svg','data:image/svg+xml;base64,'+icon)
(root/'preview').mkdir(exist_ok=True)
out=root/'preview/Clinical-Trial-Workbench-Preview.html'
out.write_text(page)
assert not re.search(r'(?:src|href)="/(?:assets|favicon)',page)
print(f'Built self-contained fixture preview: {out.name} ({out.stat().st_size:,} bytes)')
