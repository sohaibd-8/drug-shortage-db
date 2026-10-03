FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir .

CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn webapp.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
