FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ghostscript \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

ENV PORT=8000
CMD gunicorn -b 0.0.0.0:${PORT} -w 2 --timeout 300 app:app
