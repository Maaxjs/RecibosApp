import fitz
import pytesseract
from PIL import Image
import os
import io

def process_pdf_pages(pdf_path):
    """
    Generador que procesa un PDF página por página y 'yields' 
    (devuelve) el texto de cada página junto con su número.
    """

    if not os.path.exists(pdf_path):
        print(f"Error: El archivo PDF '{pdf_path}' no fue encontrado.")
        return 

    doc = None
    try:
        # 1. Abrir el PDF con fitz
        doc = fitz.open(pdf_path)
        print(f"PDF abierto. Se encontraron {len(doc)} páginas. Procesando...")

        # 2. Iterar por cada página
        for i, page in enumerate(doc):
            page_num = i + 1
            print(f"Procesando Página {page_num}...")
            text = "" 
            try:
                # 3. Renderizar la página a una imagen (pixmap)
                pix = page.get_pixmap(dpi=300)

                # 4. Convertir a bytes de imagen (PNG)
                img_bytes = pix.tobytes("png")

                # 5. Abrir como imagen PIL
                page_image = Image.open(io.BytesIO(img_bytes))

                # 6. Aplicar OCR con Tesseract
                text = pytesseract.image_to_string(page_image, lang='spa')

                if not text.strip():
                    print(f"  Página {page_num} no generó texto (posiblemente en blanco).")

                # 7. 'yield' (devolver) el texto y el número de página
                # La ejecución de la función se pausa aquí y vuelve en el siguiente
                # ciclo del 'for' en app.py
                yield text, page_num

            except Exception as e:
                print(f"  Error procesando la página {page_num}: {e}")
                # Devolvemos un error para esta página
                yield f"ERROR_PROCESANDO_PAGINA_{page_num}: {e}", page_num
    
    except Exception as e:
        print(f"--- ¡FALLO CRÍTICO al abrir PDF! ---: {e}")
        # Si el PDF no se puede abrir, simplemente no 'yield' nada
        return
    
    finally:
        # 8. Cerrar el documento al terminar
        if doc:
            doc.close()
            print("Documento PDF cerrado.")