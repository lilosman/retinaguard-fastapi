# ── Backend Dockerfile ──────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# تثبيت المكتبات النظامية المطلوبة لـ TensorFlow و matplotlib
RUN apt-get update && apt-get install -y \
    libgomp1 \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# نسخ requirements أولاً للاستفادة من Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ جميع ملفات المشروع
COPY . .

# متغير بيئة لمسار الموديل داخل الحاوية
ENV MODEL_PATH=/app/output/efficientnetb0_blindness_model.keras
ENV VECTORSTORE_PATH=/app/vectorstore
ENV TF_CPP_MIN_LOG_LEVEL=3
ENV TF_ENABLE_ONEDNN_OPTS=0

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
