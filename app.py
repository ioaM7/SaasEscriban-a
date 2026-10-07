import streamlit as st
import requests
import json

# Configuración de página
st.set_page_config(
    page_title="ProtocoloIA - Auditoría Notarial",
    page_icon="⚖️",
    layout="wide"
)

# Estilo personalizado mínimo
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .status-card { padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

st.title("⚖️ ProtocoloIA")
st.subheader("Auditoría Inteligente de Títulos de Propiedad e Informes Dominiales")

# Sidebar para configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    api_url = st.text_input("URL del Backend (Ngrok):", value="http://localhost:8000")
    st.info("Ingresa la URL pública que te generó ngrok (ejemplo: https://xxxx.ngrok-free.app)")

# Carga de archivos
uploaded_file = st.file_uploader("Sube el documento a auditar (PDF / Matrícula / Informe RPI)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    st.success(f"📄 Archivo cargado: **{uploaded_file.name}**")
    
    if st.button("🔍 Auditar Documento Ahora", type="primary"):
        with st.spinner("Procesando OCR, analizando gravámenes y generando dictamen..."):
            try:
                # Enviar archivo al backend en FastAPI
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                endpoint = f"{api_url.rstrip('/')}/api/v1/auditar-titulo"
                
                response = requests.post(endpoint, files=files)
                
                if response.status_code == 200:
                    data = response.json()
                    dictamen = data.get("dictamen", {})
                    
                    st.divider()
                    
                    # 1. Semáforo de Estado
                    estado = dictamen.get("estado_dictamen", "REVISION_REQUERIDA")
                    resumen = dictamen.get("resumen_ejecutivo", "Sin resumen.")
                    
                    if estado == "APTO":
                        st.success(f"### 🟢 DICTAMEN: APTO\n{resumen}")
                    elif estado == "REVISION_REQUERIDA":
                        st.warning(f"### 🟡 DICTAMEN: REVISIÓN REQUERIDA\n{resumen}")
                    else:
                        st.error(f"### 🔴 DICTAMEN: RIESGO DETECTADO\n{resumen}")
                        
                    # 2. Métricas y Datos del Inmueble
                    col1, col2 = st.columns(2)
                    
                    datos = dictamen.get("datos_inmueble", {})
                    with col1:
                        st.markdown("### 🏢 Datos del Inmueble")
                        st.write(f"**Matrícula / Dominio:** {datos.get('matricula_dominio')}")
                        st.write(f"**Nomenclatura Catastral:** {datos.get('nomenclatura_catastral')}")
                        st.write(f"**Ubicación:** {datos.get('ubicacion_domicilio')}")
                        st.write(f"**Superficie:** {datos.get('superficie_medidas')}")

                    with col2:
                        st.markdown("### 👤 Titulares de Dominio")
                        titulares = dictamen.get("titulares", [])
                        if titulares:
                            st.dataframe(titulares, use_container_width=True)
                        else:
                            st.write("No se identificaron titulares.")

                    # 3. Gravámenes y Observaciones
                    st.divider()
                    st.markdown("### ⚠️ Gravámenes y Anotaciones Personales")
                    gravamenes = dictamen.get("gravamenes_y_restricciones", [])
                    if gravamenes:
                        st.table(gravamenes)
                    else:
                        st.info("Sin gravámenes registrados.")
                        
                    # 4. Observaciones y Recomendaciones
                    col3, col4 = st.columns(2)
                    with col3:
                        st.markdown("### 🚨 Observaciones Críticas")
                        for obs in dictamen.get("observaciones_criticas", []):
                            st.write(f"- {obs}")
                            
                    with col4:
                        st.markdown("### 📝 Recomendaciones Notariales")
                        for rec in dictamen.get("recomendaciones_para_escribano", []):
                            st.write(f"- {rec}")
                            
                    # Exportar Dictamen JSON/PDF
                    st.download_button(
                        label="📥 Descargar Dictamen (JSON)",
                        data=json.dumps(dictamen, indent=2, ensure_ascii=False),
                        file_name=f"dictamen_{uploaded_file.name}.json",
                        mime="application/json"
                    )

                else:
                    st.error(f"Error en la API ({response.status_code}): {response.text}")
                    
            except Exception as e:
                st.error(f"No se pudo conectar con el backend: {str(e)}")
