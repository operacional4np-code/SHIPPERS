import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# 1. CONFIGURAÇÃO (CORREÇÃO DO ERRO DE CARREGAMENTO)
st.set_page_config(page_title="Gerador de Shippers New Post", layout="wide")

# Estilo CSS corrigido para as versões novas do Streamlit
st.markdown("""
<style>
    .stButton>button {
        background-color: #28a745 !important;
        color: white !important;
        font-weight: bold;
        width: 100%;
        height: 3em;
    }
    h1 { color: #003366; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("Gerador de Shippers - New Post")

# 2. ENTRADA
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (Ex: POA):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Suba sua Planilha de Coleta", type=["xlsx"])

if file and sigla:
    try:
        # Lógica para achar o cabeçalho dinamicamente
        df_raw = pd.read_excel(file, header=None)
        header_row = 0
        for i, row in df_raw.iterrows():
            if "DESTINO" in [str(val).upper() for val in row.values]:
                header_row = i
                break
        
        df = pd.read_excel(file, header=header_row)
        df.columns = [str(c).strip().upper() for c in df.columns]

        if st.button(f"Gerar Documento {sigla}"):
            col_d = next((c for c in df.columns if "DESTINO" in c), None)
            col_p = next((c for c in df.columns if "PESO" in c), None)

            if col_d and col_p:
                mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
                cidade = mapa.get(sigla, sigla)
                
                # Filtragem sem o erro de 'TOTAL GERAL'
                df_f = df[df[col_d].astype(str).str.contains(cidade, case=False, na=False)].copy()
                df_f = df_f[~df_f[col_d].astype(str).str.upper().str.contains("TOTAL", na=False)]

                if not df_f.empty:
                    # --- FÓRMULAS NEW POST ---
                    peso_total_g = pd.to_numeric(df_f[col_p], errors='coerce').sum()
                    
                    # 1. FIBREBOARD BOXES (Coluna I)
                    # Regra: Se a sobra for > 0.50 arredonda pra cima, senão pra baixo.
                    calculo_i = peso_total_g / sacas_f
                    sobra = calculo_i - int(calculo_i)
                    fib_boxes = math.ceil(calculo_i) if sobra > 0.50 else math.floor(calculo_i)
                    
                    # 2. SACA KG (Coluna J)
                    # Regra: Peso Total / (Sacas * Fib Boxes). Arredonda sempre pra cima (2 casas).
                    total_unidades = sacas_f * fib_boxes
                    saca_kg = math.ceil((peso_total_g / total_unidades) * 100) / 100 if total_unidades > 0 else 0
                    
                    # 3. TOTAL QUANTITY PER OVERPACK (Coluna K)
                    # Regra: Total Unidades * Saca KG
                    total_overpack = total_unidades * saca_kg
                    
                    # 4. MARCAÇÃO SEQUENCIAL
                    marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                    # GERAÇÃO DO WORD
                    try:
                        doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                        contexto = {
                            'FIBREBOARD': int(fib_boxes * sacas_f), # Total de caixas no lote
                            'PESO_G': f"{saca_kg:.2f}".replace('.', ','),
                            'TOTAL_OVERPACK': f"{total_overpack:.2f}".replace('.', ','),
                            'MARCACAO': marcacao,
                            'DATA': date.today().strftime('%d/%m/%Y'),
                            'QTD_OVERPACK': int(sacas_f)
                        }
                        doc.render(contexto)
                        
                        output = io.BytesIO()
                        doc.save(output)
                        output.seek(0)
                        
                        st.success(f"✅ Calculado! Marcação: {marcacao}")
                        st.download_button(f"📥 Baixar Shipper {sigla}", output, f"Shipper_{sigla}.docx")
                    except Exception as e:
                        st.error(f"Erro no Template: Verifique se o arquivo {sigla}-SHIPPER-t.docx existe na pasta templates.")
                else:
                    st.error(f"Destino {cidade} não encontrado.")
            else:
                st.error("Colunas DESTINO ou PESO não encontradas.")
    except Exception as e:
        st.error(f"Erro crítico: {e}")
