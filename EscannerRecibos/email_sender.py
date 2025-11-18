import smtplib
import config
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

def send_email_with_attachment(filepath, month_name, year):
    """
    Envía un email con el archivo de reporte adjunto.
    """
    
    # Comprobar si las credenciales están configuradas
    if not config.MAIL_USERNAME or not config.EMAIL_RECIPIENT_HARDCODED:
        print("Error: Configuración de email no encontrada en config.py. Omitiendo envío.")
        return False

    try:
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = config.MAIL_USERNAME
        msg['To'] = config.EMAIL_RECIPIENT_HARDCODED
        msg['Subject'] = f"Reporte de Sueldos Procesados - {month_name} {year}"
        
        # Cuerpo del email
        body = f"""
        Se ha completado un procesamiento de recibos de sueldo.
        
        Se adjunta el reporte de Excel para {month_name} {year}.
        
        - Este es un mensaje automático -
        """
        msg.attach(MIMEText(body, 'plain'))
        
        # Adjuntar el archivo
        filename = os.path.basename(filepath)
        with open(filepath, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)
        
        # Conectar y enviar
        print(f"Conectando a {config.MAIL_SERVER} para enviar email a {config.EMAIL_RECIPIENT_HARDCODED}...")
        server = smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT, local_hostname="localhost")
        server.starttls()
        server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(config.MAIL_USERNAME, config.EMAIL_RECIPIENT_HARDCODED, text)
        server.quit()
        
        print("Email enviado exitosamente.")
        return True
        
    except Exception as e:
        print(f"Error al enviar email: {e}")
        return False