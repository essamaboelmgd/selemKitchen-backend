# Dockerfile
FROM python:3.11-slim

# منع مشاكل الـ buffering في اللوج
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# تثبيت أدوات ضرورية لـ bcrypt وغيره
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مجلد العمل
WORKDIR /app

# نسخ requirements أولاً عشان يستفيد من الـ cache
COPY requirements.txt .

# تثبيت المتطلبات (كل حاجة هتتنصب من wheels جاهزة)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# نسخ باقي كود المشروع
COPY . .

# المنفذ الافتراضي لـ FastAPI
EXPOSE 8000

# تشغيل السيرفر
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]