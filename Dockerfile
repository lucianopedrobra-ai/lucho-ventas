# Usamos una imagen ligera de Python
FROM python:3.9-slim

# Evita que Python genere archivos .pyc y buffer de salida
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Copiamos los requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código (tu app.py, logo, excel, etc)
COPY . .

# Streamlit usa el puerto 8501 por defecto, pero Cloud Run prefiere el 8080
EXPOSE 8080

# Comando para verificar salud del contenedor (Opcional pero recomendado)
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# Comando de arranque apuntando al puerto 8080
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0"]
