FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /repo

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY services ./services

EXPOSE 8002

CMD ["uvicorn", "services.orders.app:app", "--host", "0.0.0.0", "--port", "8002"]
