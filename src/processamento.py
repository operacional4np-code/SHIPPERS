import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import zipfile
from src.processamento import calcular_dados_shipper
st.set_page_config(page_title="Gerador de Shippers - New Post", layout="wide")
st.title(" Automação de Shippers")
st.markdown("---")
# 1. Upload da Planilha
uploaded_file = st.file_uploader("Upload da Planilha de Coleta (Excel)", type=["xlsx"])
if uploaded_file:
df = pd.read_excel(uploaded_file)
st.write("Visualização dos Dados:", df.head())
# 2. Seleção de Destinos (Manual ou Planilha)
st.subheader("Configurações de Emissão")
opcao = st.radio("Deseja emitir para:", ["Todos da Planilha", "Selecionar Manualmente (Até
8)"])
if st.button("Gerar Shippers"):
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
# Lógica simplificada de geração
for index, row in df.iterrows():
doc = DocxTemplate("templates/modelo_shipper.docx")
contexto = calcular_dados_shipper(row)
doc.render(contexto)
# Salva o doc em memória
doc_io = io.BytesIO()
doc.save(doc_io)
doc_io.seek(0)
# Adiciona ao ZIP
nome_arquivo = f"Shipper_{contexto['cliente']}_{index}.docx"
zip_file.writestr(nome_arquivo, doc_io.getvalue())
st.success("Arquivos gerados com sucesso!")
st.download_button(
label="Baixar Shippers (ZIP)",
data=buffer.getvalue(),
file_name="shippers_processados.zip",
mime="application/zip"
)
