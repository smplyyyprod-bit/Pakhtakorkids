FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# fonts-dejavu-core supplies the Cyrillic glyphs reportlab needs; without it
# PDF export renders Russian text as empty boxes.
# postgresql-client provides pg_isready for the healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
        postgresql-client \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker/entrypoint.sh \
    && mkdir -p logs \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["/usr/bin/tini", "--", "/app/docker/entrypoint.sh"]
CMD ["python", "main.py"]
