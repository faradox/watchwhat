FROM python:3.12-slim

ARG USER_ID=1000
ARG GROUP_ID=1000
# The test tools are in every image, so make test-unit works in production too.
ARG INSTALL_DEV=true

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt requirements-dev.txt ./
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        pip install -r requirements-dev.txt; \
    else \
        pip install -r requirements.txt; \
    fi

COPY . .

RUN groupadd -g ${GROUP_ID} app \
    && useradd --uid ${USER_ID} --gid ${GROUP_ID} --create-home app \
    && mkdir -p /app/data \
    && chown -R app:app /app
USER app

EXPOSE 8000

# Migrations run on every start; they are no-ops when the schema is current.
CMD ["sh", "-c", "alembic upgrade head && python main.py"]
