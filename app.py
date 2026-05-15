import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# --- REGRAS DE CÁLCULO ---
def arredondar_I(valor):
    fracao = valor - int(valor)
    return math.ceil(valor) if fracao > 0.50 else math.floor(valor)

def calcular_logistica_otimizada(peso_total, qtd_sacas_input):
    if qtd_sacas_input <= 0 or peso_total <= 0: return 0, 0, 0
    
    valor_i_inicial = peso_total / qtd_sacas_input
    fib_boxes_arred = arredondar_I(valor_i_inicial)
    
    if fib_boxes_arred == 0: return 0, 0, 0
    
    melhor_saca_kg = 0.0
    menor_sobra_positiva = float('inf')
    
    # Busca o ajuste fino (Coluna J)
    for saca_teste in [i/100 for i in range(1, 5000)]:
        peso_calculado_l = (qtd_sacas_input * fib_boxes_arred) * saca_teste
        sobra_m = peso_calculado_l - peso_total
        
        if sobra_m >= 0 and sobra_m < menor_sobra_positiva:
            menor_sobra_positiva = sobra_m
            melhor_saca_kg = saca_teste
            if sobra_m == 0: break
            
    total_overpack = (qtd_sacas_input * fib_boxes_arred) * melhor_saca_kg
    return fib_boxes_arred, melhor_saca_kg, round(total_overpack, 2)

# --- INTERFACE ---
st.set_page_config(page_title="Gerador New Post 📝", layout="wide")
st.title("📝 Gerador de Shipper (Ajuste de Colunas)")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla (Ex: POA, CWB):").upper().strip()
with col2:
    sacas_input = st.number_input("Qtd de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Suba sua Planilha", type=["xlsx"])

if file and sigla:
    df_raw = pd.read_excel(file, header=None)
    
    # Localiza a linha do cabeçalho procurando "DESTINO"
    header_row = 0
    for i, row in df_raw.iterrows():
        row_values = [str(val).upper().strip() for val in row.values]
        if "DESTINO" in row_values:
            header_row = i
            break
    
    df = pd.read_excel(file, header=header_row)
    # Limpeza total dos nomes das colunas
    df.columns = [str(c).strip().upper() for c in df.columns]

    if st.button(f"Gerar Documento {sigla}"):
        # Busca colunas que CONTÉM as palavras chave (mais seguro que busca exata)
        col_destino = next((c for c in df.columns if "DESTINO" in c), None)
        col_peso = next((c for c in df.columns if "PESO" in c), None)

        if col_destino and col_peso:
            mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA", "CGR": "CAMPO GRANDE"}
            termo = mapa.get(sigla, sigla)
            
            df_f = df[df[col_destino].astype(str).str.contains(termo, na=False, case=False)]
            df_f = df_f[df_f[col_destino].astype(str).upper() != 'TOTAL GERAL']

            if not df_f.empty:
                peso_g = pd.to_numeric(df_f[col_peso], errors='coerce').sum()
                fib_boxes, saca_kg, total_overpack = calcular_logistica_otimizada(peso_g, sacas_input)
                
                try:
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': fib_boxes,
                        'PESO_G': f"{saca_kg:.2f}".replace('.', ','),
                        'TOTAL_OVERPACK': f"{total_overpack:.2f}".replace('.', ','),
                        'MARCACAO': sigla,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': sacas_input
                    }
                    doc.render(contexto)
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"✅ Sucesso! Peso: {peso_g}kg")
                    st.download_button("📥 Baixar Shipper", output, f"Shipper_{sigla}.docx")
                except Exception as e:
                    st.error(f"Erro no modelo: {e}")
            else:
                st.error(f"Destino {sigla} não encontrado.")
        else:
            st.error(f"Colunas não encontradas. Detectadas: {list(df.columns)}")
