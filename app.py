import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import zipfile
import math
from datetime import date

# --- LÓGICA DE ARREDONDAMENTO ---
def arredondar_logistica(valor):
    try:
        # Tenta converter para número, tratando casos onde o Excel traz formatos estranhos
        valor_num = float(str(valor).replace(',', '.')) 
        if math.isnan(valor_num) or valor_num <= 0:
            return 0
        return math.ceil(valor_num)
    except:
        return 0

# --- INTERFACE ---
st.set_page_config(page_title="Gerador New Post 📝", layout="wide")
st.title("📝 Gerador de Shippers Automático")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (ex: CWB, POA):").upper().strip()
with col2:
    sacas = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

uploaded_file = st.file_uploader("Upload da Planilha de Coleta (Colunas: DESTINO, QNTDE, PESO, VALOR)", type=["xlsx"])

if uploaded_file and sigla:
    # Lendo a planilha (forçando as colunas que você passou)
    df = pd.read_excel(uploaded_file)
    
    if st.button(f"Gerar TODOS os Shippers para {sigla}"):
        buffer = io.BytesIO()
        try:
            with zipfile.ZipFile(buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for i, row in df.iterrows():
                    # Carrega o modelo da pasta templates
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    
                    # Pegando dados conforme as colunas exatas que você informou
                    destino_nome = str(row.get('DESTINO', 'N-A')).strip()
                    peso_original = row.get('PESO', 0)
                    
                    # Aplica o arredondamento (ex: 10.2 vira 11)
                    peso_final = arredondar_logistica(peso_original)
                    
                    # Preenchimento das etiquetas (Tags {{ }} do seu Word)
                    contexto = {
                        'FIBREBOARD': int(sacas),
                        'PESO_G': peso_final,
                        'QTD_OVERPACK': 1,
                        'MARCACAO': destino_nome.upper(),
                        'TOTAL_OVERPACK': peso_final,
                        'DATA': date.today().strftime('%d/%m/%Y')
                    }
                    
                    doc.render(contexto)
                    doc_io = io.BytesIO()
                    doc.save(doc_io)
                    
                    # Nome do arquivo usando o conteúdo da coluna DESTINO
                    nome_arquivo = f"Shipper_{sigla}_{destino_nome}_{i+1}.docx".replace("/", "-")
                    zip_file.writestr(nome_arquivo, doc_io.getvalue())
            
            st.success(f"Sucesso! Foram gerados {len(df)} arquivos para {sigla}.")
            st.download_button(
                label="📥 Baixar Arquivos ZIP",
                data=buffer.getvalue(),
                file_name=f"shippers_{sigla}.zip",
                mime="application/zip"
            )
            
        except FileNotFoundError:
            st.error(f"Modelo '{sigla}-SHIPPER-t.docx' não encontrado na pasta templates!")
        except Exception as e:
            st.error(f"Erro ao processar: {e}")
