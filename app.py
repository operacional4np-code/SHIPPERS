import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Shippers", layout="wide")

# 2. VISUAL (BOTÃO VERDE E TÍTULO AZUL)
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
h1 { color: #003366; text-align: center; }
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

# 4. PROCESSAMENTO
if file and sigla:
    try:
        # Busca o cabeçalho
        df_raw = pd.read_excel(file, header=None)
        header_row = None
        for i in range(min(30, len(df_raw))):
            linha = [str(val).upper().strip() for val in df_raw.iloc[i].values]
            if "DESTINO" in linha or "PESO" in linha:
                header_row = i
                break
        
        if header_row is not None:
            df = pd.read_excel(file, header=header_row)
            df.columns = [str(c).strip().upper() for c in df.columns]

            if st.button(f"GERAR SHIPPER {sigla}"):
                c_dest = next((c for c in df.columns if "DESTINO" in c), None)
                c_peso = next((c for c in df.columns if "PESO" in c), None)

                if c_dest and c_peso:
                    # Mapa de Destinos
                    mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
                    termo = mapa.get(sigla, sigla)
                    
                    df_f = df[df[c_dest].astype(str).str.contains(termo, na=False, case=False)]
                    df_f = df_f[~df_f[c_dest].astype(str).str.upper().str.contains("TOTAL", na=False)]

                    if not df_f.empty:
                        # Cálculos Exatos
                        peso_g = pd.to_numeric(df_f[c_peso], errors='coerce').sum()
                        
                        # Fib Boxes (I)
                        v_i = peso_g / sacas_f
                        fib_i = math.ceil(v_i) if (v_i - int(v_i)) > 0.50 else math.floor(v_i)
                        
                        # Saca kg (J)
                        t_unid = sacas_f * fib_i
                        s_kg_j = math.ceil((peso_g / t_unid) * 100) / 100 if t_unid > 0 else 0
                        
                        # Total Overpack (K)
                        t_ovp = t_unid * s_kg_j
                        
                        # Marcação (#1 #2...)
                        txt_m = " ".join([f"#{i+1}" for i in range(int(sacas_f))])
                        
                        # Gerar Word
                        doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                        ctx = {
                            'FIBREBOARD': int(fib_i),
                            'PESO_G': f"{s_kg_j:.2f}".replace('.', ','),
                            'TOTAL_OVERPACK': f"{t_ovp:.2f}".replace('.', ','),
                            'MARCACAO': txt_m,
                            'DATA': date.today().strftime('%d/%m/%Y'),
                            'QTD_OVERPACK': int(sacas_f)
                        }
                        doc.render(ctx)
                        
                        out = io.BytesIO()
                        doc.save(out)
                        out.seek(0)
                        
                        st.success("✅ Gerado com sucesso!")
                        st.download_button(f"📥 BAIXAR SHIPPER {sigla}", out, f"Shipper_{sigla}.docx")
                    else:
                        st.error(f"Destino '{termo}' não encontrado.")
                else:
                    st.error("Colunas não identificadas.")
        else:
            st.warning("Palavra 'DESTINO' não encontrada na planilha.")
    except Exception as e:
        st.error(f"Erro: {e}")
