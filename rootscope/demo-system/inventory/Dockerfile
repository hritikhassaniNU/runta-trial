FROM python:3.12-slim
WORKDIR /repo
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY demo-system ./demo-system
EXPOSE 8001
ENV PYTHONPATH=/repo/demo-system
CMD ["uvicorn", "inventory.app:app", "--host", "0.0.0.0", "--port", "8001"]
