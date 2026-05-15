import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# 1. CONFIGURAÇÃO (SITE)
st.set_page_config(page_title="Gerador New Post", layout="wide")

st.markdown("""
<style>
    .stButton>button { background-color: #28a745 !important; color: white !important; font-weight: bold; width: 100%; }
    h1 { color: #003366; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("Gerador de Shippers")

# 2. ENTRADA
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla (Ex: CGB):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

file = st.file_uploader("Upload da Planilha", type=["xlsx"])

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
                    # --- CÁLCULO FINAL (PRECISÃO TOTAL) ---
                    peso_total = pd.to_numeric(df_f[c_peso], errors='coerce').sum()
                    
                    # I: FIBREBOARD (Mantido como você aprovou)
                    v_i = peso_total / sacas_f
                    sobra = v_i - int(v_i)
                    fib_boxes = math.ceil(v_i) if sobra > 0.50 else math.floor(v_i)
                    
                    # J: PESO_G (Cálculo direto sem arredondamentos intermediários)
                    # 131,32 / 7 / 4 = 4,69
                    peso_g_bruto = peso_total / (sacas_f * fib_boxes)
                    
                    # Arredonda para cima apenas no final (2 casas)
                    peso_g_final = math.ceil(peso_g_bruto * 100) / 100
                    
                    # K: TOTAL QUANTITY PER OVERPACK
                    # 4 * 4,69 = 18,76
                    total_ovp_final = fib_boxes * peso_g_final
                    
                    marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                    # GERAÇÃO
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': int(fib_boxes),
                        'PESO_G': f"{peso_g_final:.2f}".replace('.', ','),
                        'TOTAL_OVERPACK': f"{total_ovp_final:.2f}".replace('.', ','),
                        'MARCACAO': marcacao,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': int(sacas_f)
                    }
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"✅ Sucesso! Peso G: {peso_g_final} | Total: {total_ovp_final}")
                    st.download_button(f"📥 BAIXAR SHIPPER {sigla}", output, f"Shipper_{sigla}.docx")
                else:
                    st.error(f"Destino {cidade} não encontrado.")
    except Exception as e:
        st.error(f"Erro: {e}")
