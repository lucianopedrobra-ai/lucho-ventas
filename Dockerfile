FROM python:3.9-slim

# Evitar que Python genere archivos .pyc y buffer de salida
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Crear directorio de trabajo
WORKDIR /app

# Copiar los requisitos e instalarlos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar EL RESTO de los archivos (app.py, config.py, etc)
COPY . .

# Exponer el puerto que usa Cloud Run (8080)
EXPOSE 8080

# Comando para iniciar la app
CMD streamlit run app.py --server.port=8080 --server.address=0.0.0.0
