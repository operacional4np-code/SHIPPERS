import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# --- LÓGICA DE CÁLCULO ---
def arredondar_I(valor):
    fracao = valor - int(valor)
    return math.ceil(valor) if fracao > 0.50 else math.floor(valor)

def gerar_sequencia_sacas(n):
    return " ".join([f"#{i+1}" for i in range(int(n))])

# --- INTERFACE VISUAL ---
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
    h1 { color: #003366; text-align: center; margin-bottom: 25px; }
    </style>
    """, unsafe_allow_index=True)

st.title("Gerador de Shippers")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (Ex: POA):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Upload da Planilha de Coleta", type=["xlsx"])

if file and sigla:
    # Lemos a planilha bruta
    df_raw = pd.read_excel(file, header=None)
    
    # Busca dinâmica da linha de títulos (procura DESTINO ou PESO)
    header_row = None
    for i in range(min(30, len(df_raw))):
        linha = [str(val).upper().strip() for val in df_raw.iloc[i].values]
        if "DESTINO" in linha or "PESO" in linha:
            header_row = i
            break
            
    if header_row is not None:
        # Carrega os dados com o cabeçalho correto
        df = pd.read_excel(file, header=header_row)
        # Limpeza agressiva nos nomes das colunas
        df.columns = [str(c).strip().upper().replace('\n', '').replace('\r', '') for c in df.columns]

        if st.button(f"GERAR SHIPPER {sigla}"):
            # Tenta encontrar as colunas por aproximação
            col_dest = next((c for c in df.columns if "DESTINO" in c), None)
            col_peso = next((c for c in df.columns if "PESO" in c), None)

            if col_dest and col_peso:
                mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
                termo = mapa.get(sigla, sigla)
                
                # Filtra e remove linhas que contenham "TOTAL"
                df_f = df[df[col_dest].astype(str).str.contains(termo, na=False, case=False)]
                df_f = df_f[~df_f[col_dest].astype(str).str.upper().str.contains("TOTAL", na=False)]

                if not df_f.empty:
                    # PESO TOTAL (G)
                    peso_g = pd.to_numeric(df_f[col_peso], errors='coerce').sum()
                    
                    # FIB BOXES (I)
                    valor_i = peso_g / sacas_f
                    fib_boxes_i = arredondar_I(valor_i)
                    
                    # SACA KG (J) - Arredondamento para cima 2 casas
                    total_unid = sacas_f * fib_boxes_i
                    saca_kg_j = math.ceil((peso_g / total_unid) * 100) / 100 if total_unid > 0 else 0
                    
                    # TOTAL OVERPACK (K)
                    total_ovp = total_unid * saca_kg_j
                    
                    # Etiqueta MARCACAO (#1 #2...)
                    texto_marcacao = gerar_sequencia_sacas(sacas_f)
                    
                    try:
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
                        
                        st.success(f"✅ Gerado com sucesso! Peso: {peso_g}kg")
                        st.download_button(f"📥 BAIXAR SHIPPER {sigla}", output, f"Shipper_{sigla}.docx")
                    except Exception as e:
                        st.error(f"Erro no modelo: {e}")
                else:
                    st.error(f"Não encontramos '{termo}' na coluna {col_dest}.")
            else:
                st.error(f"Colunas não identificadas. Colunas lidas: {list(df.columns)}")
    else:
        st.error("Não foi possível localizar os títulos (DESTINO/PESO) na planilha.")
