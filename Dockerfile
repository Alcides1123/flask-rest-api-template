FROM python:3.10-slim

WORKDIR /app

# postgresql-client provides psql, used by entrypoint.sh to wait for the database
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Runtime dependencies only (no linters, test tools or notebooks in the image)
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Unprivileged user. uid/gid 1000 so that the ./logs bind mount in
# docker-compose.yml stays writable on a typical single-user host.
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --no-create-home --shell /usr/sbin/nologin app && \
    mkdir -p /app/logs && \
    chown app:app /app /app/logs

COPY --chown=app:app . /app

RUN chmod +x /app/entrypoint.sh

USER app

EXPOSE 5000

ENTRYPOINT ["/app/entrypoint.sh"]
