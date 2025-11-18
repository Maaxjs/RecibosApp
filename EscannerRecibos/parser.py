import os
import json
from groq import Groq
from config import GROQ_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

try:
    client = Groq()
except Exception as e:
    print(f"Error: {e}")
    print("Asegurate de poner tu API Key en la variable de entorno GROQ_API_KEY")
    exit()

def create_prompt(sueldo_text):
    return f"""
    Eres un experto en interpretar recibos de sueldo y CORREGIR NOMBRES MAL ESCRITOS. Analiza el texto y devuelve EXCLUSIVAMENTE un único objeto JSON.

    TEXTO DEL RECIBO:
    ```
    {sueldo_text}
    ```

    EXTRAE:
    1. "nombre": Nombre del empleado.
    2. "apellido": Apellido del empleado.
    3. "sueldo": Monto total del sueldo (como número, no string).

    CONSIDERACIONES:
    INSTRUCCIONES CLAVE:
    IMPORTANTE: Es posible que el nombre esté con algún error ortigráfico o alguna letra mal puesta, en tal caso arreglalo al nombre correcto
    0. Pueden haber nombres compuestos y apellidos mal escritos, por ejemplo, Rsm0n Feronandez en lugar de Ramon Fernandez, tenelo en cuenta y arregalos 
    1. Solo extrae el empleado/trabajador, no el empleador. 
    2. El empleado casi siempre aparece después de la etiqueta "Apellido y nombre:.
    3. Si hay varios recibos, devuelve todos en la lista “recibos”.
    4. Corrige errores ortográficos menores en nombres y apellidos.
    5. El sueldo debe ser el monto líquido final si aparece; si no, usa el bruto.
    6. No incluyas datos del empleador ni otros nombres.

    Formato de salida:
    ```json
    {{
      "recibos": [
        {{"nombre": "...", "apellido": "...", "sueldo": 123456.78}}
      ]
    }}
    ```

    DESPUÉS DEL OUTPUT JSON NO ESCRIBAS NADA MÁS.
    """



def process_ticket(sueldo_text):
    """Procesa recibo de sueldo y devuelve el JSON parseado"""
    prompt = create_prompt(sueldo_text)

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant", 
            
            # Forzamos la respuesta a ser un JSON
            response_format={"type": "json_object"},
            
            temperature=0.0
        )

        # OBTENER EL JSON
        response_content = chat_completion.choices[0].message.content
        parsed_json = json.loads(response_content)
        
        return parsed_json

    except Exception as e:
        return {
            'error': str(e),
            'nombre': 'Error',
            'apellido': 'Error',
            'sueldo': 0
        }

    except Exception as e:
        print(f"Error procesando: {e}")
    