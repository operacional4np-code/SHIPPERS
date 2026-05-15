import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import zipfile
import math

# --- LÓGICA DE PROCESSAMENTO ---
def arredondar_logistica(valor):
    if pd.isna(valor) or valor == 0:
        return 0
    return math.ceil(valor)

def calcular_dados_shipper(df_linha):
    return {
        'cliente': df_linha.get('Cliente', 'N/A'),
        'nf': df_linha.get('Nota Fiscal', '000'),
        'peso': arredondar_logistica(df_linha.get('Peso', 0))
    }

# --- INTERFACE DO SITE ---
st.set_page_config(page_title="Gerador New Post 📝", layout="wide")

st.title("📝 Gerador de Shippers por Sigla")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    # O usuário digita apenas CWB, POA, etc.
    sigla = st.text_input("Sigla do Destino (ex: CWB, POA):").upper().strip()
with col2:
    sacas = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

uploaded_file = st.file_uploader("Selecione a Planilha de Coleta", type=["xlsx"])

if uploaded_file and sigla:
    if st.button(f"Gerar Shippers para {sigla}"):
        df = pd.read_excel(uploaded_file)
        buffer = io.BytesIO()
        
        # Ajuste para bater com o nome exato dos seus arquivos no GitHub
        nome_do_modelo = f"templates/{sigla}-SHIPPER-t.docx"
        
        try:
            with zipfile.ZipFile(buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for index, row in df.iterrows():
                    # Carrega o modelo (ex: templates/CWB-SHIPPER-t.docx)
                    doc = DocxTemplate(nome_do_modelo)
                    
                    contexto = calcular_dados_shipper(row)
                    contexto['sacas'] = sacas
                    
                    doc.render(contexto)
                    
                    doc_io = io.BytesIO()
                    doc.save(doc_io)
                    
                    nome_cliente = str(row.get('Cliente', index)).replace("/", "-").strip()
                    zip_file.writestr(f"Shipper_{sigla}_{nome_cliente}.docx", doc_io.getvalue())
            
            st.success(f"Sucesso! Shippers para {sigla} gerados.")
            st.download_button(
                label="📥 Baixar Todos os Shippers (ZIP)",
                data=buffer.getvalue(),
                file_name=f"shippers_{sigla}.zip",
                mime="application/zip"
            )
            
        except FileNotFoundError:
            st.error(f"Erro: O arquivo '{nome_do_modelo}' não foi encontrado. Verifique se a sigla está correta.")
        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")
