import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# --- LÓGICA DE CÁLCULO (PADRÃO EXCEL) ---
def arredondar_I(valor):
    """Regra: > 0.50 sobe, <= 0.50 mantém"""
    fracao = valor - int(valor)
    return math.ceil(valor) if fracao > 0.50 else math.floor(valor)

def gerar_sequencia_sacas(n):
    """Gera a sequência #1 #2 #3... conforme a quantidade de sacas"""
    return " ".join([f"#{i+1}" for i in range(int(n))])

# --- INTERFACE VISUAL (PADRÃO NEW POST) ---
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
        height: 3em;
        border: none;
    }
    h1 { color: #003366; text-align: center; font-family: sans-serif; margin-bottom: 30px; }
    </style>
    """, unsafe_allow_index=True)

# Título alterado conforme solicitado
st.title("Gerador de Shippers")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (Ex: POA):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Upload da Planilha de Coleta", type=["xlsx"])

if file and sigla:
    df_raw = pd.read_excel(file, header=None)
    
    # Busca dinâmica da linha de títulos (procura por DESTINO)
    header_row = None
    for i in range(min(30, len(df_raw))):
        linha = [str(val).upper().strip() for val in df_raw.iloc[i].values]
        if "DESTINO" in linha:
            header_row = i
            break
            
    if header_row is not None:
        df = pd.read_excel(file, header=header_row)
        df.columns = [str(c).strip().upper() for c in df.columns]

        # Botão Verde Padrão
        if st.button(f"GERAR SHIPPER {sigla}"):
            col_dest = next((c for c in df.columns if "DESTINO" in c), None)
            col_peso = next((c for c in df.columns if "PESO" in c), None)

            if col_dest and col_peso:
                mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
                termo = mapa.get(sigla, sigla)
                
                # Filtra o destino e remove linhas de total
                df_f = df[df[col_dest].astype(str).str.contains(termo, na=False, case=False)]
                df_f = df_f[~df_f[col_dest].astype(str).str.contains("TOTAL", na=False, case=False)]

                if not df_f.empty:
                    # Execução dos Cálculos
                    peso_g = pd.to_numeric(df_f[col_peso], errors='coerce').sum()
                    
                    # Coluna I
                    valor_i = peso_g / sacas_f
                    fib_boxes_i = arredondar_I(valor_i)
                    
                    # Coluna J (Saca kg) com arredondamento para cima na 2ª casa decimal
                    total_unidades = sacas_f * fib_boxes_i
                    if total_unidades > 0:
                        saca_kg_j = math.ceil((peso_g / total_unidades) * 100) / 100
                    else:
                        saca_kg_j = 0
                    
                    # Coluna K (Total Overpack)
                    total_overpack_k = total_unidades * saca_kg_j
                    
                    # Geração da Marcação (#1 #2...)
                    texto_marcacao = gerar_sequencia_sacas(sacas_f)
                    
                    try:
                        doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                        contexto = {
                            'FIBREBOARD': int(fib_boxes_i),
                            'PESO_G': f"{saca_kg_j:.2f}".replace('.', ','),
                            'TOTAL_OVER
