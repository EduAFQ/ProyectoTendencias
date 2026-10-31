FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PARKING_DATABASE_URL=sqlite:////data/parking.db

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && mkdir -p /data \
    && chown app:app /data

COPY --chown=app:app flaskr ./flaskr

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/', timeout=3)"

CMD ["sh", "-c", "python -m flaskr.inicializarBD && exec gunicorn --bind 0.0.0.0:8000 --workers 2 --access-logfile - --error-logfile - 'flaskr:create_app()'"]
