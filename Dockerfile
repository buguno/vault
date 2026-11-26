# syntax=docker/dockerfile:1

# build: install the runtime dependencies into a virtualenv
FROM python:3.14-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# Poetry lives in its own virtualenv, so it does not end up in the final image.
RUN python -m venv /opt/venv \
    && python -m venv /opt/poetry \
    && /opt/poetry/bin/pip install poetry==2.3.3

WORKDIR /app
# Only the dependency files first, so this layer is cached until they change.
COPY pyproject.toml poetry.lock ./
RUN /opt/poetry/bin/poetry install --only main --no-root --no-interaction


# run: a small image with just the app
FROM python:3.14-slim

LABEL org.opencontainers.image.title="V.A.U.L.T" \
      org.opencontainers.image.description="Self-hosted, offline-first inventory manager for food, water, medications, ammunition and preparedness gear." \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    ENVIRONMENT=production

# gnupg is what the encrypted backup (Settings page) uses.
# The app runs as a fixed, unprivileged user (uid/gid 10001): a system account
# with no home directory, no shell and no password.
ARG UID=10001
ARG GID=10001
RUN apt-get update \
    && apt-get install -y --no-install-recommends gnupg \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid ${GID} vault \
    && useradd --system --uid ${UID} --gid ${GID} \
        --no-create-home --home-dir /nonexistent \
        --shell /usr/sbin/nologin vault

COPY --from=build /opt/venv /opt/venv

# The code belongs to root and nobody can write to it: the app user only reads
# it, so a compromised process cannot change the application. The only places
# the app writes are /tmp (backups, in a throwaway directory) and /dev/shm
# (gunicorn heartbeat), which is why the container also runs with a read-only
# filesystem.
WORKDIR /app
COPY manage.py gunicorn.conf.py ./
COPY config ./config
COPY apps ./apps
COPY templates ./templates
COPY static ./static
COPY locale ./locale
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/

# Gather the static files now, so nothing has to run before the first start.
# The values are throwaway: collectstatic never touches the database.
RUN SECRET_KEY=build-only ALLOWED_HOSTS=localhost \
    DATABASE_URL=postgres://build:build@localhost/build \
    python manage.py collectstatic --noinput \
    && chmod -R a+rX,go-w /app

USER vault

EXPOSE 8000

# The app answers on its port (a plain TCP check: no Host header to allow).
# It follows GUNICORN_BIND when the port is changed.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, socket; port = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000').rsplit(':', 1)[1]; socket.create_connection(('127.0.0.1', int(port)), 3)"

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"]
