import os
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from services import extraer_texto_pdf, auditar_documento_con_groq

load_dotenv()

app = FastAPI(
    title="ProtocoloIA - API de Auditoría Notarial",
    description="Backend para la extracción y análisis automatizado de títulos de propiedad e informes dominiales.",
    version="1.0.0"
)

# Permitir solicitudes CORS para el frontend (React / Next.js / Streamlit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "app": "ProtocoloIA API",
        "status": "online",
        "version": "1.0.0"
    }

@app.post("/api/v1/auditar-titulo")
async def auditar_titulo(file: UploadFile = File(...)):
    """
    Endpoint principal: Recibe un archivo PDF (matrícula/informe de dominio),
    extrae el texto (con OCR si es un escaneo) y retorna la auditoría notarial en JSON.
    """
    if not file.filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de archivo no soportado. Por favor sube un PDF o imagen."
        )

    try:
        contenido_bytes = await file.read()
        
        # 1. Extraer texto del PDF
        texto_extraido = extraer_texto_pdf(contenido_bytes)
        
        if not texto_extraido or len(texto_extraido) < 30:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No se pudo extraer texto claro del documento. Verifica que la imagen o PDF sea legible."
            )

        # 2. Procesar con la IA para generar el dictamen
        dictamen = auditar_documento_con_groq(texto_extraido)

        return {
            "exito": True,
            "nombre_archivo": file.filename,
            "caracteres_procesados": len(texto_extraido),
            "dictamen": dictamen
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el procesamiento del documento: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
