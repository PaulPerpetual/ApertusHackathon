# One container for UI + API + pipeline. Runs on-prem, air-gapped (with a local LLM endpoint)
# or on Azure Container Apps / App Service. Configure via LLM_* environment variables.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY judgements/ judgements/
COPY data/examples.json data/examples.json
ENV SUVA_DB=/app/data/suva.sqlite
WORKDIR /app/src
EXPOSE 8000
CMD ["python", "-m", "suva", "serve", "--host", "0.0.0.0", "--port", "8000"]
