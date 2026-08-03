FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    build-essential \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Variables necesarias para Rasterio/GDAL
ENV GDAL_CONFIG=/usr/bin/gdal-config

# Instalar dependencias Python
COPY src/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

# Copiar proyecto
COPY . .

# Crear carpetas requeridas
RUN mkdir -p uploaded_files uploaded_codes

# Entrar al directorio src
WORKDIR /app/src

ENV PYTHONPATH=/app:/app/src

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "app:app"]