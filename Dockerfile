FROM python:3.11-slim

# Установка системных библиотек для gssapi/kerberos
RUN apt-get update && apt-get install -y --no-install-recommends \
    libkrb5-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "-w", "1", "-k", "sync", "-b", "0.0.0.0:8000", "bot:flask_app"]