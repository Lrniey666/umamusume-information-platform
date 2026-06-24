FROM python:3.12-slim-bookworm

WORKDIR /app

# 安裝系統依賴（FAISS 需要 gcc、libgomp）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgomp1 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY docker-files-poa/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
