import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import zipfile
import math
from datetime import date

# --- LÓGICA DE ARREDONDAMENTO ---
def arredondar_logistica(valor):
    if pd.isna(valor) or valor == 0:
        return 0
    return math.ceil(valor)

# --- INTERFACE ---
st.set_page_config(page_title="Gerador New Post 📝", layout="wide")
st.title("📝 Gerador de Shippers")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (ex: CWB):").upper().strip()
with col2:
    sacas = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

uploaded_file = st.file_uploader("Upload da Planilha de Coleta", type=["xlsx"])

if uploaded_file and sigla:
    df = pd.read_excel(uploaded_file)
    
    st.info("Selecione abaixo quais clientes você quer gerar agora:")
    # Seletor para evitar gerar a planilha toda de uma vez
    selecao = st.multiselect("Clientes disponíveis:", 
                             options=df.index, 
                             format_func=lambda x: f"{df.iloc[x].get('Cliente', 'N/A')} (NF: {df.iloc[x].get('Nota Fiscal', 'S/N')})")

    if st.button(f"Gerar Documentos para {sigla}"):
        if not selecao:
            st.error("Selecione pelo menos um cliente na lista acima!")
        else:
            buffer = io.BytesIO()
            try:
                with zipfile.ZipFile(buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for i in selecao:
                        row = df.iloc[i]
                        doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                        
                        # --- MAPEAMENTO DAS SUAS ETIQUETAS ---
                        # Aqui ligamos a coluna do Excel com a tag {{ }} do seu Word
                        peso_bruto = row.get('Peso', 0)
                        peso_arredondado = arredondar_logistica(peso_bruto)
                        
                        contexto = {
                            'FIBREBOARD': sacas,
                            'PESO_G': peso_arredondado,
                            'QTD_OVERPACK': 1, # Exemplo, você pode mudar se quiser
                            'MARCACAO': row.get('Cliente', 'N/A'),
                            'TOTAL_OVERPACK': peso_arredondado,
                            'DATA': date.today().strftime('%d/%m/%Y')
                        }
                        
                        doc.render(contexto)
                        doc_io = io.BytesIO()
                        doc.save(doc_io)
                        
                        nome_cliente = str(row.get('Cliente', i)).replace("/", "-")
                        zip_file.writestr(f"Shipper_{sigla}_{nome_cliente}.docx", doc_io.getvalue())
                
                st.success("Documentos prontos!")
                st.download_button("📥 Baixar Arquivos (ZIP)", buffer.getvalue(), f"shippers_{sigla}.zip")
            except FileNotFoundError:
                st.error(f"Modelo {sigla}-SHIPPER-t.docx não encontrado na pasta templates!")
