# Single-process image for later Runta experiments. Local dev uses Compose.
FROM python:3.12-slim
WORKDIR /repo
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api ./apps/api
COPY demo-system ./demo-system
ENV PYTHONPATH=/repo/apps/api:/repo/demo-system
ENV ROOTSCOPE_DATABASE=/repo/data/rootscope.db
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
