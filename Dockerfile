# Temel imaj (hafif sürüm)
FROM python:3.9-slim-buster

# Çalışma dizini oluştur
WORKDIR /app

# Önce bağımlılıkları kopyala (build cache optimizasyonu)
COPY requirements.txt .

# Bağımlılıkları yükle
RUN pip install --no-cache-dir -r requirements.txt

# Tüm proje dosyalarını kopyala
COPY . .

# Environment variables için gerekli paket
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# PostgreSQL bağlantıları için gerekli kütüphane
RUN apt-get update && apt-get install -y gcc python3-dev

# Uygulamayı çalıştır
CMD ["python", "bot.py"]
