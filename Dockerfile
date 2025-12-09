# USAMOS PYTHON 3.11 (Obligatorio para la IA nueva)
FROM python:3.11-slim

# Configuraciones para que Python no guarde basura
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# ACTUALIZAMOS PIP (Clave para evitar errores de instalación)
RUN pip install --upgrade pip

# Copiamos requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código
COPY . .

# Puerto 8080 para Google Cloud Run
EXPOSE 8080

# Chequeo de salud
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# --- OJO AQUÍ ABAJO ---
# Si tu archivo se llama "main.py", deja "main.py". 
# Si ya lo cambiaste a "app.py" como te sugerí antes, pon "app.py".
# En la foto vi que todavía tienes "main.py", así que lo dejo así para que te funcione YA:
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0"]
