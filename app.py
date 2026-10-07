import os
import json
import io
import streamlit as st
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
from groq import Groq

# Configuración de página
st.set_page_config(
    page_title="ProtocoloIA - Auditoría Notarial",
    page_icon="⚖️",
    layout="wide"
)

# Estilos visuales
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    </style>
""", unsafe_allow_html=True)

PROMPT_AUDITORIA_NOTARIAL = """
Eres un asistente de Inteligencia Artificial especializado en auditoría de títulos inmobiliarios, derecho notarial y análisis de informes del Registro de la Propiedad Inmueble (RPI) de Argentina.

Tu tarea es analizar minuciosamente el texto extraído del documento cargado (informe de dominio, matrícula del RPI, certificado de anotaciones personales o escritura) y emitir un DICTAMEN DE AUDITORÍA TÉCNICA.

Debes responder EXCLUSIVAMENTE con un objeto JSON válido que cumpla estrictamente la siguiente estructura (sin texto explicativo antes ni después, sin marcas de markdown afuera del JSON):

{
  "estado_dictamen": "APTO" | "REVISION_REQUERIDA" | "RIESGO_DETECTADO",
  "resumen_ejecutivo": "Explicación concisa en 1 a 3 oraciones sobre el estado del título/documento.",
  "datos_inmueble": {
    "matricula_dominio": "Número de matrícula o folio real",
    "nomenclatura_catastral": "Circunscripción, Sección, Manzana, Parcela, etc.",
    "ubicacion_domicilio": "Dirección completa o descripción del inmueble",
    "superficie_medidas": "Superficie total o descripción de linderos"
  },
  "titulares": [
    {
      "nombre_completo": "Nombre y apellido o Razón Social",
      "dni_cuit": "Número de documento o CUIT/CUIL",
      "porcentaje_titularidad": "Porcentaje (ej. 100%, 50%)",
      "estado_civil": "Soltero/a, Casado/a, Divorciado/a, etc.",
      "causa_adquisicion": "Compraventa, Donación, Sucesión, etc."
    }
  ],
  "gravamenes_y_restricciones": [
    {
      "tipo": "Embargo / Hipoteca / Usufructo / Inalienabilidad / Servidumbre / Ninguno",
      "monto": "Monto de la traba si aplica o No especificado",
      "autos_juzgado_escribania": "Juzgado, Fuero, Secretaría o Escribanía interviniente",
      "fecha_inscripcion": "Fecha de inscripción o tomaduría de razón",
      "estado_vigencia": "Vigente / Caduco / Cancelado / Incierto"
    }
  ],
  "observaciones_criticas": [
    "Inconsistencias de DNI/Nombres entre titulares y adquirentes",
    "Embargos u opositores no cancelados formalmente",
    "Falta de datos clave en el documento"
  ],
  "recomendaciones_para_escribano": [
    "Acciones preventivas recomendadas antes de la firma de la escritura"
  ]
}

REGLAS DE AUDITORÍA:
1. Si un dato no figura en el texto, asigna "No especificado".
2. Pon especial atención a los embargos e inhibiciones.
3. Clasifica el estado general como APTO, REVISION_REQUERIDA o RIESGO_DETECTADO.
"""

def extraer_texto_pdf(pdf_bytes: bytes) -> str:
    texto_extraido = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    texto_extraido += text + "\n"
    except Exception as e:
        st.warning(f"Aviso al leer texto nativo: {e}")
    
    if len(texto_extraido.strip()) < 100:
        st.info("🔎 El PDF es escaneado/imagen. Aplicando OCR con Tesseract...")
        texto_extraido = ""
        try:
            images = convert_from_bytes(pdf_bytes)
            for img in images:
                texto_pagina = pytesseract.image_to_string(img, lang="spa")
                texto_extraido += texto_pagina + "\n"
        except Exception as ocr_err:
            st.error(f"Error en OCR: {ocr_err}")
            
    return texto_extraido.strip()

def auditar_con_groq(texto: str, api_key: str) -> dict:
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": PROMPT_AUDITORIA_NOTARIAL},
            {"role": "user", "content": f"DOCUMENTO A AUDITAR:\n\n{texto}"}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# ENCABEZADO
st.title("⚖️ ProtocoloIA")
st.caption("Sistema de Auditoría Inteligente de Títulos Inmobiliarios e Informes Dominiales")

# SIDEBAR PARA LA API KEY
with st.sidebar:
    st.header("🔑 Configuración")
    groq_key = st.text_input("Ingresa tu Groq API Key:", type="password")

# CARGA DE ARCHIVO
uploaded_file = st.file_uploader("Carga el informe de dominio o matrícula (PDF / Imagen)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file and st.button("🚀 Auditar Documento", type="primary"):
    if not groq_key:
        st.error("Por favor, ingresa tu API Key de Groq en la barra lateral.")
    else:
        with st.spinner("Procesando documento y generando el dictamen notarial..."):
            file_bytes = uploaded_file.getvalue()
            texto = extraer_texto_pdf(file_bytes)
            
            if not texto:
                st.error("No se pudo extraer texto del archivo.")
            else:
                try:
                    dictamen = auditar_con_groq(texto, groq_key)
                    
                    st.divider()
                    
                    # Semáforo de Riesgo
                    estado = dictamen.get("estado_dictamen", "REVISION_REQUERIDA")
                    resumen = dictamen.get("resumen_ejecutivo", "")
                    
                    if estado == "APTO":
                        st.success(f"### 🟢 DICTAMEN: APTO\n{resumen}")
                    elif estado == "REVISION_REQUERIDA":
                        st.warning(f"### 🟡 DICTAMEN: REVISIÓN REQUERIDA\n{resumen}")
                    else:
                        st.error(f"### 🔴 DICTAMEN: RIESGO DETECTADO\n{resumen}")
                    
                    # Datos del Inmueble y Titulares
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### 🏢 Datos del Inmueble")
                        datos = dictamen.get("datos_inmueble", {})
                        st.write(f"**Matrícula:** {datos.get('matricula_dominio')}")
                        st.write(f"**Catastro:** {datos.get('nomenclatura_catastral')}")
                        st.write(f"**Ubicación:** {datos.get('ubicacion_domicilio')}")
                        st.write(f"**Superficie:** {datos.get('superficie_medidas')}")

                    with col2:
                        st.markdown("### 👤 Titulares")
                        st.dataframe(dictamen.get("titulares", []), use_container_width=True)

                    # Gravámenes
                    st.markdown("### ⚠️ Gravámenes y Restricciones")
                    st.table(dictamen.get("gravamenes_y_restricciones", []))

                    # Observaciones
                    st.markdown("### 📝 Observaciones y Recomendaciones")
                    for obs in dictamen.get("observaciones_criticas", []):
                        st.write(f"- 🔴 {obs}")
                    for rec in dictamen.get("recomendaciones_para_escribano", []):
                        st.write(f"- 💡 {rec}")
                        
                except Exception as e:
                    st.error(f"Error al analizar con la IA: {e}")
