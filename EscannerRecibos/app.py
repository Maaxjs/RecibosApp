from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_from_directory
import os
import uuid
import json
from werkzeug.utils import secure_filename
import threading
import shutil 
from ocr import process_pdf_pages
from parser import process_ticket
from excel_generator import create_excel_report
from email_sender import send_email_with_attachment

app = Flask(__name__)

# Configuración
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
TEMP_REPORTS_FOLDER = 'temp_reports'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists('temp_reports'):
    os.makedirs('temp_reports')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

# --- ENDPOINT 1: MODIFICADO PARA MÚLTIPLES ARCHIVOS ---config
@app.route('/upload_multiple', methods=['POST'])
def upload_multiple():
    """
    Recibe MÚLTIPLES PDFs, los guarda en una carpeta de lote única
    y devuelve el ID del lote.
    """
    # Usamos request.files.getlist para obtener todos los archivos
    files = request.files.getlist('files[]')

    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'error': 'No se seleccionaron archivos'}), 400

    # Crear un ID de lote único
    batch_id = str(uuid.uuid4())
    batch_dir = os.path.join(app.config['UPLOAD_FOLDER'], batch_id)
    os.makedirs(batch_dir) # Crear la carpeta para el lote

    print(f"Nuevo lote creado: {batch_id}")

    try:
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(batch_dir, filename)
                file.save(file_path)
                print(f"Archivo guardado en lote {batch_id}: {filename}")
        
        # Devolvemos el batch_id para que el frontend sepa a qué conectarse
        return jsonify({'success': True, 'batch_id': batch_id})
    
    except Exception as e:
        print(f"Error al guardar archivos del lote: {e}")
        # Si falla, limpiar la carpeta del lote
        if os.path.exists(batch_dir):
            shutil.rmtree(batch_dir)
        return jsonify({'success': False, 'error': 'Error al guardar archivos en el servidor'}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    """
    Sirve el archivo Excel desde la carpeta 'temp_reports'.
    """
    print(f"Solicitud de descarga para: {filename}")
    return send_from_directory(
        TEMP_REPORTS_FOLDER, 
        filename, 
        as_attachment=True
    )

def _send_email_in_background(excel_path, month, year):
    """
    Función de hilo simplificada: SOLO envía el email.
    """
    print(f"[Hilo BKG] Iniciando envío de email para {excel_path}...")
    try:
        if excel_path:
            send_email_with_attachment(excel_path, month, year)
        print("[Hilo BKG] Email enviado.")
    except Exception as e:
        print(f"[Hilo BKG] Error en el hilo de envío de email: {e}")


@app.route('/process_stream/<batch_id>')
def process_stream(batch_id):
    safe_batch_id = secure_filename(batch_id)
    batch_dir = os.path.join(app.config['UPLOAD_FOLDER'], safe_batch_id)

    if not os.path.isdir(batch_dir):
        return jsonify({'error': 'Lote no encontrado'}), 404

    def generate_events():
        all_recibos = []
        excel_filename = None # Variable para guardar el nombre del archivo
        
        try:
            pdf_files = [f for f in os.listdir(batch_dir) if allowed_file(f)]
            print(f"Procesando lote {batch_id} con {len(pdf_files)} archivo(s)...")

            # Bucle 1: Procesar todos los PDFs
            for pdf_filename in pdf_files:
                pdf_path = os.path.join(batch_dir, pdf_filename)
                for page_text, page_num in process_pdf_pages(pdf_path):
                    progress_data = {
                        'status': 'progress',
                        'message': f'Procesando {pdf_filename}: Página {page_num}...'
                    }
                    yield f"data: {json.dumps(progress_data)}\n\n" 

                    if not page_text or page_text.startswith("ERROR_PROCESANDO_PAGINA"):
                        continue 
                    
                    json_data = process_ticket(page_text)
                    if 'recibos' in json_data and json_data['recibos']:
                        all_recibos.extend(json_data['recibos'])
            
            # --- Lógica de finalización ---
            
            if not all_recibos:
                # No se encontró nada, enviar error
                final_data = {'status': 'error', 'message': 'No se encontraron recibos legibles en los documentos.'}
            else:
                # ¡Se encontraron recibos! Generar Excel ANTES de responder.
                print("Procesamiento de páginas completo. Generando Excel...")
                yield f"data: {json.dumps({'status': 'progress', 'message': 'Generando reporte de Excel...'})}\n\n"
                
                excel_path, month, year = create_excel_report(all_recibos)
                
                if excel_path is None:
                    # Falló la creación del Excel
                    final_data = {'status': 'error', 'message': 'Error al generar el archivo Excel.'}
                else:
                    # ¡Éxito! Obtenemos el nombre del archivo
                    excel_filename = os.path.basename(excel_path)
                    print(f"Excel generado: {excel_filename}. Iniciando hilo de email...")
                    
                    # Iniciar el hilo SOLO para enviar email
                    threading.Thread(
                        target=_send_email_in_background, 
                        args=(excel_path, month, year)
                    ).start()
                    
                    # Preparar la respuesta final para el frontend
                    final_data = {
                        'status': 'complete',
                        'data': {'recibos': all_recibos},
                        'download_filename': os.path.basename(excel_path) 
                    }

            # Enviar el mensaje final (sea de éxito o error)
            print("Stream: Enviando datos completos al frontend.")
            yield f"data: {json.dumps(final_data)}\n\n"

        except Exception as e:
            print(f"Error en el stream del lote: {e}")
            error_data = {'status': 'error', 'message': str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
        
        finally:
            # Limpiar: Borrar la carpeta del LOTE (con los PDFs)
            if os.path.exists(batch_dir):
                try:
                    shutil.rmtree(batch_dir)
                    print(f"Carpeta de lote eliminada: {batch_dir}")
                except Exception as e:
                    print(f"Error al eliminar carpeta de lote {batch_dir}: {e}")
            
            # NOTA: NO borramos el archivo Excel
            print("Stream: Conexión con frontend cerrada.")

    return Response(
    stream_with_context(generate_events()), 
    mimetype='text/event-stream',
    headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)