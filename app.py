import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# 1. CONFIGURAÇÃO E VISUAL (CORRIGE O ERRO DE PÁGINA BRANCA)
st.set_page_config(page_title="Gerador de Shippers", layout="wide")

st.markdown("""
<style>
    .stButton>button {
        background-color: #28a745 !important;
        color: white !important;
        font-weight: bold;
        width: 100%;
        height: 3.5em;
    }
    h1 { color: #003366; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("Gerador de Shippers")

# 2. ENTRADA DE DADOS
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (Ex: CGB):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

file = st.file_uploader("Upload da Planilha de Coleta", type=["xlsx"])

if file and sigla:
    try:
        df_raw = pd.read_excel(file, header=None)
        header_row = 0
        for i, row in df_raw.iterrows():
            if "DESTINO" in [str(val).upper() for val in row.values]:
                header_row = i
                break
        
        df = pd.read_excel(file, header=header_row)
        df.columns = [str(c).strip().upper() for c in df.columns]

        if st.button(f"GERAR SHIPPER {sigla}"):
            c_dest = next((c for c in df.columns if "DESTINO" in c), None)
            c_peso = next((c for c in df.columns if "PESO" in c), None)

            if c_dest and c_peso:
                mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
                cidade = mapa.get(sigla, sigla)
                
                df_f = df[df[c_dest].astype(str).str.contains(cidade, case=False, na=False)].copy()
                df_f = df_f[~df_f[c_dest].astype(str).str.upper().str.contains("TOTAL", na=False)]

                if not df_f.empty:
                    # --- FÓRMULAS REAJUSTADAS CONFORME MODELO CORRETO ---
                    peso_total = pd.to_numeric(df_f[c_peso], errors='coerce').sum()
                    
                    # Coluna I: Fibreboard Boxes (por saca)
                    # Regra: Se decimal > 0.50 arredonda pra cima, senão mantém.
                    v_i = peso_total / sacas_f
                    sobra = v_i - int(v_i)
                    fib_boxes_i = math.ceil(v_i) if sobra > 0.50 else math.floor(v_i)
                    
                    # Coluna J: Saca KG (Peso Total / Sacas / Fib Boxes)
                    # Arredondado sempre para cima com 2 casas decimais
                    saca_kg_j = math.ceil((peso_total / (sacas_f * fib_boxes_i)) * 100) / 100
                    
                    # Coluna K: Total Overpack (Fib Boxes * Saca KG)
                    total_ovp_k = fib_boxes_i * saca_kg_j
                    
                    # Marcação (#1 #2 #3...)
                    txt_marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                    # GERAÇÃO DO WORD
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': int(fib_boxes_i), # Conforme PDF: deve ser o valor por saca (ex: 4)
                        'PESO_G': f"{saca_kg_j:.2f}".replace('.', ','),
                        'TOTAL_OVERPACK': f"{total_ovp_k:.2f}".replace('.', ','),
                        'MARCACAO': txt_marcacao,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': int(sacas_f)
                    }
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"✅ Gerado com sucesso para {cidade}!")
                    st.download_button(f"📥 BAIXAR SHIPPER {sigla}", output, f"Shipper_{sigla}.docx")
                else:
                    st.error(f"Destino {cidade} não localizado.")
            else:
                st.error("Colunas DESTINO ou PESO não encontradas.")
    except Exception as e:
        st.error(f"Erro: {e}")
