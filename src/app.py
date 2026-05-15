import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import zipfile
from src.processamento import calcular_dados_shipper

# Configuração da página com o emoji de papel
st.set_page_config(page_title="Gerador New Post 📝", layout="wide")

st.title("📝 Gerador de Shippers por Sigla")
st.markdown("---")

# Campos de entrada
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (ex: CWB, POA):").upper()
with col2:
    sacas = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

# Upload da planilha
uploaded_file = st.file_uploader("Selecione a Planilha de Coleta", type=["xlsx"])

if uploaded_file and sigla:
    if st.button(f"Gerar Shippers para {sigla}"):
        df = pd.read_excel(uploaded_file)
        buffer = io.BytesIO()
        
        try:
            with zipfile.ZipFile(buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for index, row in df.iterrows():
                    # Busca o modelo específico na pasta templates (ex: templates/CWB.docx)
                    doc = DocxTemplate(f"templates/{sigla}.docx")
                    
                    # Realiza os cálculos usando o arquivo da pasta src
                    contexto = calcular_dados_shipper(row)
                    contexto['sacas'] = sacas # Insere a quantidade de sacas no Word
                    
                    doc.render(contexto)
                    
                    # Salva temporariamente em memória para colocar no ZIP
                    doc_io = io.BytesIO()
                    doc.save(doc_io)
                    
                    # Nome do arquivo individual dentro do ZIP
                    nome_cliente = str(row.get('Cliente', index)).replace("/", "-")
                    zip_file.writestr(f"Shipper_{sigla}_{nome_cliente}.docx", doc_io.getvalue())
            
            st.success(f"Sucesso! Todos os shippers para {sigla} foram gerados.")
            st.download_button(
                label="📥 Baixar Todos os Shippers (ZIP)",
                data=buffer.getvalue(),
                file_name=f"shippers_{sigla}.zip",
                mime="application/zip"
            )
            
        except FileNotFoundError:
            st.error(f"Erro: O modelo ' {sigla}.docx ' não foi encontrado na pasta templates. Verifique se o nome está correto no GitHub ou no Drive.")
        except Exception as e:
            st.error(f"Ocorreu um erro inesperado: {e}")
