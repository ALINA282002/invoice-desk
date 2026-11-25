FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8765
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Bake OCR models into the image so the first scanned invoice is fast
RUN python -c "from rapidocr import RapidOCR; RapidOCR()"

COPY . .
# The app ships empty: no vendors, POs or invoices. Configure it in the setup screen on first launch.
RUN mkdir -p storage inbox/processed

EXPOSE 8765
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
