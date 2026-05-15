import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# --- REGRAS DE CÁLCULO PRECISAS ---

def arredondar_I(valor):
    """Regra do vídeo: > 0.50 sobe, <= 0.50 desce"""
    fracao = valor - int(valor)
    return math.ceil(valor) if fracao > 0.50 else math.floor(valor)

def otimizar_saca_kg(peso_alvo, sacas_f, fib_boxes_i):
    """
    Busca o valor da Saca (Coluna J) que resulte no peso 
    mais próximo do original, sem ser menor que ele.
    """
    if sacas_f <= 0 or fib_boxes_i <= 0: return 0.0
    
    total_unidades = sacas_f * fib_boxes_i
    # Valor base da saca (Peso / Total de unidades)
    saca_base = peso_alvo / total_unidades
    
    # Testamos com precisão de duas casas decimais (ex: 0.11, 0.12...)
    # Arredondamos a base para cima para garantir que a sobra comece positiva
    melhor_saca = math.ceil(saca_base * 100) / 100
    
    return melhor_saca

# --- INTERFACE ---
st.set_page_config(page_title="Gerador New Post 📝", layout="wide")
st.title("📝 Ajuste Fino de Cálculos (Versão Anexo)")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla (Ex: POA):").upper().strip()
with col2:
    sacas_f = st.number_input("Qtd de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Suba sua Planilha", type=["xlsx"])

if file and sigla:
    df_raw = pd.read_excel(file, header=None)
    
    # Busca dinâmica da linha de títulos
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
                # 1. PESO G (Soma exata da planilha)
                peso_real_g = pd.to_numeric(df_f[col_peso], errors='coerce').sum()
                
                # 2. COLUNA I (Fib Boxes)
                valor_i = peso_real_g / sacas_f
                fib_boxes_i = arredondar_I(valor_i)
                
                # 3. COLUNA J (Saca kg - Otimizada)
                saca_kg_j = otimizar_saca_kg(peso_real_g, sacas_f, fib_boxes_i)
                
                # 4. COLUNA K (Total Overpack)
                total_overpack_k = (sacas_f * fib_boxes_i) * saca_kg_j
                
                try:
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': fib_boxes_i,
                        'PESO_G': f"{saca_kg_j:.2f}".replace('.', ','),
                        'TOTAL_OVERPACK': f"{total_overpack_k:.2f}".replace('.', ','),
                        'MARCACAO': sigla,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': sacas_f
                    }
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"✅ Calculado! Peso Planilha: {peso_real_g} | Total Etiqueta: {total_overpack_k}")
                    st.download_button("📥 Baixar Shipper", output, f"Shipper_{sigla}.docx")
                except Exception as e:
                    st.error(f"Erro no Word: {e}")
