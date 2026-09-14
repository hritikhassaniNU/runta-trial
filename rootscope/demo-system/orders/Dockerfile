FROM python:3.12-slim
WORKDIR /repo
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY demo-system ./demo-system
EXPOSE 8002
ENV PYTHONPATH=/repo/demo-system
ENV INVENTORY_URL=http://inventory:8001
CMD ["uvicorn", "orders.app:app", "--host", "0.0.0.0", "--port", "8002"]
