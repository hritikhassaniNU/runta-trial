FROM python:3.12-slim
WORKDIR /repo
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api ./apps/api
EXPOSE 8000
ENV PYTHONPATH=/repo/apps/api
ENV ROOTSCOPE_DATABASE=/repo/data/rootscope.db
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
