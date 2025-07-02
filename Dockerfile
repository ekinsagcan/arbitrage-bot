# 1. Aşama: Build için temel imaj
FROM python:3.9-slim-buster as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 2. Aşama: Runtime imajı
FROM python:3.9-slim-buster
WORKDIR /app

# 3. Sadece gerekli dosyaları kopyala
COPY --from=builder /root/.local /root/.local
COPY bot.py database.py ./

# 4. PATH ayarı
ENV PATH=/root/.local/bin:$PATH

# 5. Runtime bağımlılıkları
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

CMD ["python", "bot.py"]
