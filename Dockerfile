FROM ubuntu:latest
LABEL authors="PC"

ENTRYPOINT ["top", "-b"]
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Порт, на котором слушает Flask/FastAPI внутри контейнера
EXPOSE 8000

CMD ["gunicorn", "-w", "1", "-k", "sync", "-b", "0.0.0.0:8000", "bot:flask_app"]