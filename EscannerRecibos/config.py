import os

# === CONFIGURACIÓN BÁSICA ===
# Clave secreta para sesiones
SECRET_KEY = 'tu_clave_secreta_cambiar_en_produccion'

# === CONFIGURACIÓN DE ARCHIVOS ===
# Carpeta para guardar archivos generados
UPLOAD_FOLDER = 'uploads'

# === CONFIGURACIÓN DE FLASK ===
# Modo de depuración
DEBUG = True
# Host
HOST = '0.0.0.0'
# Puerto
PORT = 5000

# === CONFIGURACIÓN MAIL
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
EMAIL_RECIPIENT_HARDCODED = ''

# === CONFIGURACIÓN APIS
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")