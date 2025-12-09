# --- AQUÍ ESTÁ LA CLAVE: TIENE QUE DECIR 3.11 ---
FROM python:3.11-slim

# Evita archivos basura
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# ACTUALIZAMOS PIP (Vital)
RUN pip install --upgrade pip

# Instalamos librerías
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos TODOS los archivos (app.py, estilos.py, config.py, funciones.py)
COPY . .

# Puerto
EXPOSE 8080

# Salud
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# --- CONFIRMACIÓN FINAL: Apuntamos a app.py ---
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
