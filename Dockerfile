# CAMBIO IMPORTANTE: Usamos Python 3.11 en lugar de 3.9 para compatibilidad con IA
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y buffer de salida
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Actualizamos pip para evitar advertencias
RUN pip install --upgrade pip

# Copiamos los requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# Cloud Run espera tráfico en el puerto 8080
EXPOSE 8080

# Comando para verificar salud del contenedor
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# EJECUCIÓN
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
