# --- CAMBIO CRÍTICO: USAR PYTHON 3.11 ---
FROM python:3.11-slim

# Configuraciones
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio
WORKDIR /app

# Actualizar pip (Vital para que no falle la instalación)
RUN pip install --upgrade pip

# Instalar requerimientos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Puerto
EXPOSE 8080

# Salud
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# Arrancar la app (Apuntando a app.py)
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
