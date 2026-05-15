import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# 1. AJUSTE DO SITE (CORRIGE O ERRO DE CARREGAMENTO)
st.set_page_config(page_title="Gerador New Post", layout="wide")

st.markdown("""
<style>
    .stButton>button { background-color: #28a745 !important; color: white !important; font-weight: bold; width: 100%; }
    h1 { color: #003366; text-align: center; }
</style>
""", unsafe_allow_html=True) # Corrigido de unsafe_allow_index para html

st.title("Gerador de Shippers - New Post")

# 2. ENTRADA
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (Ex: CGB):").upper().strip()
with col2:
    sacas_f = st.number_input("Qtd de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Suba a Planilha", type=["xlsx"])

if file and sigla:
    try:
        # Leitura robusta da planilha
        df_raw = pd.read_excel(file, header=None)
        header_row = 0
        for i, row in df_raw.iterrows():
            if "DESTINO" in [str(val).upper() for val in row.values]:
                header_row = i
                break
        
        df = pd.read_excel(file, header=header_row)
        df.columns = [str(c).strip().upper() for c in df.columns]

        if st.button(f"GERAR DOCUMENTO {sigla}"):
            c_dest = next((c for c in df.columns if "DESTINO" in c), None)
            c_peso = next((c for c in df.columns if "PESO" in c), None)

            if c_dest and c_peso:
                mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
                cidade = mapa.get(sigla, sigla)
                
                # Filtro seguro que não causa erro de AttributeError
                df_f = df[df[c_dest].astype(str).str.contains(cidade, case=False, na=False)].copy()
                
                if not df_f.empty:
                    # --- CÁLCULOS EXATOS ---
                    peso_total = pd.to_numeric(df_f[c_peso], errors='coerce').sum()
                    
                    # I: Fibreboard por saca (regra do 0.50)
                    calc_i = peso_total / sacas_f
                    sobra = calc_i - int(calc_i)
                    fib_por_saca = math.ceil(calc_i) if sobra > 0.50 else math.floor(calc_i)
                    
                    # J: Saca KG (Peso Total / Total de Caixas) arredondado p/ cima
                    total_caixas_lote = sacas_f * fib_por_saca
                    saca_kg = math.ceil((peso_total / total_caixas_lote) * 100) / 100
                    
                    # K: Total Overpack
                    total_overpack = total_caixas_lote * saca_kg
                    
                    # Marcação (#1 #2...)
                    txt_marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                    # --- GERAÇÃO DO WORD ---
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': int(total_caixas_lote), # AGORA MULTIPLICADO PELAS SACAS
                        'PESO_G': f"{saca_kg:.2f}".replace('.', ','),
                        'TOTAL_OVERPACK': f"{total_overpack:.2f}".replace('.', ','),
                        'MARCACAO': txt_marcacao,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': int(sacas_f)
                    }
                    doc.render(contexto)
                    
                    out = io.BytesIO()
                    doc.save(out)
                    out.seek(0)
                    
                    st.success(f"✅ Sucesso! Total de Caixas: {total_caixas_lote}")
                    st.download_button("📥 Baixar Arquivo", out, f"Shipper_{sigla}.docx")
                else:
                    st.error(f"Destino {cidade} não encontrado.")
            else:
                st.error("Colunas não encontradas na planilha.")
    except Exception as e:
        st.error(f"Erro: {e}")
