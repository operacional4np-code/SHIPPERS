import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# 1. FUNÇÕES DE APOIO
def arredondar_I(valor):
    fracao = valor - int(valor)
    if fracao > 0.50:
        return math.ceil(valor)
    else:
        return math.floor(valor)

def gerar_sequencia_sacas(n):
    try:
        n_int = int(n)
        return " ".join([f"#{i+1}" for i in range(n_int)])
    except:
        return ""

# 2. CONFIGURAÇÃO VISUAL
st.set_page_config(page_title="Gerador de Shippers", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button {
        background-color: #28a745 !important;
        color: white !important;
        border-radius: 5px;
        width: 100%;
        font-weight: bold;
        height: 3.5em;
        border: none;
    }
    h1 { color: #003366; text-align: center; font-family: sans-serif; }
    </style>
    """, unsafe_allow_index=True)

st.title("Gerador de Shippers")

# 3. ENTRADA DE DADOS
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (Ex: POA):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Upload da Planilha de Coleta", type=["xlsx"])

# 4. LÓGICA DE PROCESSAMENTO
if file and sigla:
    try:
        df_raw = pd.read_excel(file, header=None)
        header_row = None
        for i in range(min(30, len(df_raw))):
            linha = [str(val).upper().strip() for val in df_raw.iloc[i].values]
            if "DESTINO" in linha or "PESO" in linha:
                header_row = i
                break
        
        if header_row is not None:
            df = pd.read_excel(file, header=header_row)
            df.columns = [str(c).strip().upper().replace('\\n', '') for c in df.columns]

            if st.button(f"GERAR SHIPPER {sigla}"):
                col_dest = next((c for c in df.columns if "DESTINO" in c), None)
                col_peso = next((c for c in df.columns if "PESO" in c), None)

                if col_dest and col_peso:
                    mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
                    termo = mapa.get(sigla, sigla)
                    
                    df_f = df[df[col_dest].astype(str).str.contains(termo, na=False, case=False)]
                    df_f = df_f[~df_f[col_dest].astype(str).str.upper().str.contains("TOTAL", na=False)]

                    if not df_f.empty:
                        peso_g = pd.to_numeric(df_f[col_peso], errors='coerce').sum()
                        fib_boxes_i = arredondar_I(peso_g / sacas_f)
                        
                        total_unid = sacas_f * fib_boxes_i
                        saca_kg_j = math.ceil((peso_g / total_unid) * 100) / 100 if total_unid > 0 else 0
                        total_ovp = total_unid * saca_kg_j
                        
                        texto_marcacao = gerar_sequencia_sacas(sacas_f)
                        
                        doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                        contexto = {
                            'FIBREBOARD': int(fib_boxes_i),
                            'PESO_G': f"{saca_kg_j:.2f}".replace('.', ','),
                            'TOTAL_OVERPACK': f"{total_ovp:.2f}".replace('.', ','),
                            'MARCACAO': texto_marcacao,
                            'DATA': date.today().strftime('%d/%m/%Y'),
                            'QTD_OVERPACK': int(sacas_f)
                        }
                        doc.render(contexto)
                        
                        output = io.BytesIO()
                        doc.save(output)
                        output.seek(0)
                        
                        st.success(f"✅ Gerado com sucesso!")
                        st.download_button(f"📥 BAIXAR SHIPPER {sigla}", output, f"Shipper_{sigla}.docx")
                    else:
                        st.error(f"Destino '{termo}' não encontrado.")
                else:
                    st.error("Colunas DESTINO/PESO não identificadas.")
        else:
            st.info("Planilha carregada. Clique no botão acima para gerar.")
    except Exception as e:
        st.error(f"Erro: {e}")
