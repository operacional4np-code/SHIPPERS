import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# --- REGRAS DE CÁLCULO EXATAS ---

def arredondar_I(valor):
    """Regra do vídeo: > 0.50 sobe para o próximo inteiro, <= 0.50 mantém o inteiro atual"""
    fracao = valor - int(valor)
    return math.ceil(valor) if fracao > 0.50 else math.floor(valor)

def gerar_sequencia_sacas(n):
    """Gera a string: #1 #2 #3 ... #n"""
    return " ".join([f"#{i+1}" for i in range(int(n))])

# --- INTERFACE ---
st.set_page_config(page_title="Gerador New Post 📝", layout="wide")
st.title("📝 Ajuste Final: Cálculos e Marcação")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla (Ex: POA):").upper().strip()
with col2:
    sacas_f = st.number_input("Qtd de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Suba sua Planilha de Coleta", type=["xlsx"])

if file and sigla:
    df_raw = pd.read_excel(file, header=None)
    
    # Localização dinâmica da linha de títulos
    start_row = 0
    for i in range(min(20, len(df_raw))):
        linha = [str(val).upper().strip() for val in df_raw.iloc[i].values]
        if "DESTINO" in linha:
            start_row = i
            break
            
    df = pd.read_excel(file, header=start_row)
    df.columns = [str(c).strip().upper() for c in df.columns]

    if st.button(f"Gerar Documento {sigla}"):
        col_dest = next((c for c in df.columns if "DESTINO" in c), None)
        col_peso = next((c for c in df.columns if "PESO" in c), None)

        if col_dest and col_peso:
            mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
            termo = mapa.get(sigla, sigla)
            
            df_f = df[df[col_dest].astype(str).str.contains(termo, na=False, case=False)]
            df_f = df_f[~df_f[col_dest].astype(str).str.contains("TOTAL", na=False, case=False)]

            if not df_f.empty:
                # 1. PESO G (Soma real da planilha)
                peso_real_g = pd.to_numeric(df_f[col_peso], errors='coerce').sum()
                
                # 2. COLUNA I (Fib Boxes) - Fórmula: Peso / Sacas F
                valor_i = peso_real_g / sacas_f
                fib_boxes_i = arredondar_I(valor_i)
                
                # 3. COLUNA J (Saca kg) - Fórmula: (Peso / Sacas F) / Fib Boxes I
                # Usamos a lógica de ajuste para não ser negativo
                if fib_boxes_i > 0:
                    saca_kg_j = (peso_real_g / sacas_f) / fib_boxes_i
                    # Arredondamos para 2 casas para cima para garantir que L >= G
                    saca_kg_j = math.ceil(saca_kg_j * 100) / 100
                else:
                    saca_kg_j = 0
                
                # 4. COLUNA K (Total Overpack) - Fórmula: (Sacas F * Fib Boxes I) * Saca KG J
                total_overpack_k = (sacas_f * fib_boxes_i) * saca_kg_j
                
                # 5. ETIQUETA MARCACAO (Ex: #1 #2 #3...)
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
                    
                    st.success(f"✅ Calculado! Marcação: {texto_marcacao}")
                    st.download_button("📥 Baixar Shipper", output, f"Shipper_{sigla}.docx")
                except Exception as e:
                    st.error(f"Erro no Word: {e}")
