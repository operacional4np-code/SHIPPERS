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
    """Ex: 3 sacas -> #1 #2 #3"""
    return " ".join([f"#{i+1}" for i in range(int(n))])

# --- CONFIGURAÇÃO VISUAL (PADRÃO NEW POST) ---
st.set_page_config(page_title="Gerador New Post", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button {
        background-color: #28a745;
        color: white;
        border-radius: 5px;
        width: 100%;
        font-weight: bold;
    }
    h1 { color: #003366; text-align: center; font-family: sans-serif; }
    .stTextInput>div>div>input { border-color: #003366; }
    </style>
    """, unsafe_allow_index=True)

st.title("📝 Gerador de Shipper - New Post")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (Ex: POA):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Upload da Planilha de Coleta", type=["xlsx"])

if file and sigla:
    df_raw = pd.read_excel(file, header=None)
    
    # Busca a linha onde os dados começam
    header_row = 0
    for i in range(min(20, len(df_raw))):
        linha = [str(val).upper().strip() for val in df_raw.iloc[i].values]
        if "DESTINO" in linha:
            header_row = i
            break
            
    df = pd.read_excel(file, header=header_row)
    df.columns = [str(c).strip().upper() for c in df.columns]

    if st.button(f"GERAR SHIPPER {sigla}"):
        col_dest = next((c for c in df.columns if "DESTINO" in c), None)
        col_peso = next((c for c in df.columns if "PESO" in c), None)

        if col_dest and col_peso:
            mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
            termo = mapa.get(sigla, sigla)
            
            df_f = df[df[col_dest].astype(str).str.contains(termo, na=False, case=False)]
            df_f = df_f[~df_f[col_dest].astype(str).str.contains("TOTAL", na=False, case=False)]

            if not df_f.empty:
                # 1. Peso Bruto Total (G)
                peso_g = pd.to_numeric(df_f[col_peso], errors='coerce').sum()
                
                # 2. Fib Boxes (I)
                valor_i = peso_g / sacas_f
                fib_boxes_i = arredondar_I(valor_i)
                
                # 3. Saca kg (J) - Arredondamento crítico para 2 casas para cima
                total_unidades = sacas_f * fib_boxes_i
                saca_kg_j = math.ceil((peso_g / total_unidades) * 100) / 100
                
                # 4. Total Overpack (K) - Baseado no J já arredondado
                total_overpack_k = total_unidades * saca_kg_j
                
                # 5. Marcação (#1 #2...)
                texto_marcacao = gerar_sequencia_sacas(sacas_f)
                
                try:
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': int(fib_boxes_i),
                        'PESO_G': f"{saca_kg_j:.2f}".replace('.', ','),
                        'TOTAL_OVERPACK': f"{total_overpack_k:.2f}".replace('.', ','),
                        'MARCACAO': texto_marcacao,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': int(sacas_f)
                    }
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.markdown(f"### ✅ Sucesso para {sigla}")
                    st.write(f"**Fib Boxes:** {fib_boxes_i} | **Saca kg:** {saca_kg_j:.2f} | **Total:** {total_overpack_k:.2f}")
                    
                    st.download_button(
                        label=f"📥 BAIXAR SHIPPER {sigla}",
                        data=output,
                        file_name=f"Shipper_{sigla}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"Erro no Word: {e}")
