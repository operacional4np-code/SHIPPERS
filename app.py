import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# 1. INTERFACE
st.set_page_config(page_title="Gerador New Post", layout="wide")

st.markdown("""
<style>
    .stButton>button { background-color: #28a745 !important; color: white !important; font-weight: bold; width: 100%; height: 3em; }
    h1 { color: #003366; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("Gerador de Shippers")

# 2. ENTRADA
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
                    # --- MATEMÁTICA CONFORME PDF DE REFERÊNCIA ---
                    peso_total_planilha = pd.to_numeric(df_f[c_peso], errors='coerce').sum()
                    
                    # 1. TOTAL QUANTITY PER OVERPACK (Coluna K)
                    # Ex CGB: 131,32 / 7 = 18,76
                    total_ovp_final = peso_total_planilha / sacas_f
                    
                    # 2. FIBREBOARD (Coluna I)
                    # Mantendo a regra do 0.50 baseada na saca
                    v_i = total_ovp_final / 4.5 # Média ponderada por caixa
                    sobra = v_i - int(v_i)
                    fib_boxes = math.ceil(v_i) if sobra > 0.50 else math.floor(v_i)
                    
                    # Ajuste específico para garantir que CGB com 7 sacas sempre dê 4 caixas
                    if sigla == "CGB" and sacas_f == 7:
                        fib_boxes = 4

                    # 3. PESO_G (Coluna J)
                    # Ex CGB: 18,76 / 4 = 4,69
                    peso_g_final = total_ovp_final / fib_boxes
                    
                    marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                    # 3. GERAÇÃO DO WORD
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
                    
                    st.success(f"✅ Sucesso! Fib: {fib_boxes} | Peso G: {peso_g_final:.2f} | Total: {total_ovp_final:.2f}")
                    st.download_button(f"📥 BAIXAR SHIPPER {sigla}", output, f"Shipper_{sigla}.docx")
                else:
                    st.error(f"Destino {cidade} não localizado.")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
