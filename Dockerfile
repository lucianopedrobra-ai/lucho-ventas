# USAMOS PYTHON 3.11 (Obligatorio para la IA nueva y compatible con streamlit)
FROM python:3.11-slim

# Configuraciones para que Python no guarde basura y el log sea fluido
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# ACTUALIZAMOS PIP (Clave para evitar errores de instalación de librerías modernas)
RUN pip install --upgrade pip

# Copiamos requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código (app.py, config.py, estilos.py, funciones.py)
COPY . .

# Puerto 8080 para Google Cloud Run
EXPOSE 8080

# Chequeo de salud (opcional pero recomendado)
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# --- PUNTO CLAVE ---
# Aquí apuntamos a "app.py" porque ya confirmaste que cambiaste el nombre
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
