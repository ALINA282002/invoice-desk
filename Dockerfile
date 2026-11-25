FROM python:3.12-slim

# BOOTSTRAP_DIR: a fresh (empty) disk loads company + vendor master + PO register from demo-config/.
# INBOX_WATCH=0: no mailbox folder in the cloud. Hosts that inject PORT (Render) override 8765.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8765 BOOTSTRAP_DIR=demo-config INBOX_WATCH=0
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Bake OCR models into the image so the first scanned invoice is fast
RUN python -c "from rapidocr import RapidOCR; RapidOCR()"

COPY . .
# Hugging Face Spaces runs the container as a non-root user (uid 1000): data folders must be writable
RUN mkdir -p storage/files inbox/processed && chmod -R 777 storage inbox

EXPOSE 8765
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
