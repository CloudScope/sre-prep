# Optional: build a real image on the kind host instead of the ConfigMap approach.
#   docker build -t inventory-api:0.1.0 . && kind load docker-image inventory-api:0.1.0 --name local-k8s
FROM python:3.13.17-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
USER 1000
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
