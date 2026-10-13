# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS ui
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -s /run/secrets/proxy_ca ]; then NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca npm ci --strict-ssl=true; else npm ci --strict-ssl=true; fi
COPY frontend/ ./
COPY configs/ /build/configs/
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=secret,id=proxy_ca \
    if [ -s /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.txt; else pip install --no-cache-dir -r requirements.txt; fi
# Copy runtime sources and the independently compiled UI in one layer. This
# avoids repeating a large Python filesystem on Docker's VFS storage driver.
RUN --mount=type=bind,source=.,target=/source \
    --mount=type=bind,from=ui,source=/build/frontend/dist,target=/built-ui \
    cp -a /source/backend /source/src /source/scripts /source/configs /source/examples /app/ && \
    mkdir -p /app/data /app/frontend/dist && \
    cp -a /source/data/sample /source/data/starter /app/data/ && \
    cp -a /built-ui/. /app/frontend/dist/ && \
    chmod -R a+rX /app/backend /app/src /app/scripts /app/configs /app/examples /app/data/sample /app/data/starter /app/frontend && \
    useradd --create-home --uid 10001 cti && \
    mkdir -p /app/data/workbench /app/results && \
    chown -R cti:cti /app/data/workbench /app/results
USER cti
ENV API_HOST=0.0.0.0
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v5/bootstrap', timeout=4)"
CMD ["python", "scripts/start.py"]
