import os
import json
import io
import pdfplumber
from pypdf import PdfReader
from pdf2image import convert_from_bytes
import pytesseract
from groq import Groq
from prompts import PROMPT_AUDITORIA_NOTARIAL

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def extraer_texto_pdf(pdf_bytes: bytes) -> str:
    """Extrae texto de un archivo PDF usando pdfplumber y fallback a OCR con Tesseract."""
    texto_extraido = ""
    
    # 1. Intento de extracción de texto nativo
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    texto_extraido += text + "\n"
    except Exception as e:
        print(f"Error extrayendo texto nativo: {e}")
    
    # 2. Si el texto extraído es muy corto, aplicamos OCR (para PDFs escaneados)
    if len(texto_extraido.strip()) < 100:
        print("Texto nativo escaso. Ejecutando OCR (pytesseract)...")
        texto_extraido = ""
        try:
            images = convert_from_bytes(pdf_bytes)
            for img in images:
                texto_pagina = pytesseract.image_to_string(img, lang="spa")
                texto_extraido += texto_pagina + "\n"
        except Exception as ocr_error:
            print(f"Error durante proceso OCR: {ocr_error}")
            
    return texto_extraido.strip()


def auditar_documento_con_groq(texto_documento: str) -> dict:
    """Envía el texto procesado a Groq API para generar el dictamen estructurado en JSON."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY no configurada en las variables de entorno.")

    client = Groq(api_key=GROQ_API_KEY)

    system_message = PROMPT_AUDITORIA_NOTARIAL
    user_content = f"--- TEXTO EXTRAÍDO DEL DOCUMENTO NOTARIAL/MATRÍCULA ---\n\n{texto_documento}"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content}
        ],
        temperature=0.1,  # Baja temperatura para evitar alucinaciones
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    return json.loads(content)
