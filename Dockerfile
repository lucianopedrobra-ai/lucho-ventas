# --- CAMBIO OBLIGATORIO: Usamos 3.11 (Si dice 3.9 fallará) ---
FROM python:3.11-slim

# Evitamos archivos basura
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# ACTUALIZAR PIP (Crítico para que no falle la instalación)
RUN pip install --upgrade pip

# Copiamos y e instalamos las librerías
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos TODOS los archivos (app.py, estilos.py, config.py, funciones.py)
COPY . .

# Puerto para Cloud Run
EXPOSE 8080

# Chequeo de salud
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# --- PUNTO FINAL: Apuntamos a "app.py" ---
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
