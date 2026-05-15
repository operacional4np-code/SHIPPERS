import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# --- REGRAS DE CÁLCULO (VÍDEO) ---
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
    for saca_teste in [i/100 for i in range(1, 5000)]:
        peso_calc = (qtd_sacas_input * fib_boxes_arred) * saca_teste
        sobra = peso_calc - peso_total
        if sobra >= 0 and sobra < menor_sobra_positiva:
            menor_sobra_positiva = sobra
            melhor_saca_kg = saca_teste
            if sobra == 0: break
            
    total_overpack = (qtd_sacas_input * fib_boxes_arred) * melhor_saca_kg
    return fib_boxes_arred, melhor_saca_kg, round(total_overpack, 2)

# --- INTERFACE ---
st.set_page_config(page_title="Gerador New Post 📝", layout="wide")
st.title("📝 Gerador de Shipper - Busca Inteligente")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla (Ex: POA, CWB):").upper().strip()
with col2:
    sacas_input = st.number_input("Qtd de Sacas:", min_value=1, step=1)

file = st.file_uploader("Suba sua Planilha", type=["xlsx"])

if file and sigla:
    # Lemos a planilha bruta primeiro
    df_raw = pd.read_excel(file, header=None)
    
    # --- BUSCA DINÂMICA DE COLUNAS ---
    col_destino_idx = None
    col_peso_idx = None
    start_row = 0

    # Varre as primeiras 20 linhas para achar onde estão os títulos
    for i in range(min(20, len(df_raw))):
        linha = [str(val).upper().strip() for val in df_raw.iloc[i].values]
        if "DESTINO" in linha or "PESO" in linha:
            start_row = i
            for idx, val in enumerate(linha):
                if "DESTINO" in val: col_destino_idx = idx
                if "PESO" in val: col_peso_idx = idx
            break

    if col_destino_idx is not None and col_peso_idx is not None:
        # Reconstrói o DataFrame a partir da linha correta
        df = pd.read_excel(file, header=start_row)
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Identifica os nomes reais das colunas após a limpeza
        real_col_destino = df.columns[col_destino_idx]
        real_col_peso = df.columns[col_peso_idx]

        if st.button(f"Gerar Documento {sigla}"):
            mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA", "CGR": "CAMPO GRANDE"}
            termo = mapa.get(sigla, sigla)
            
            # Filtra e remove totais
            df_f = df[df[real_col_destino].astype(str).str.contains(termo, na=False, case=False)]
            df_f = df_f[~df_f[real_col_destino].astype(str).str.contains("TOTAL", na=False, case=False)]

            if not df_f.empty:
                peso_g = pd.to_numeric(df_f[real_col_peso], errors='coerce').sum()
                fib_boxes, saca_kg, total_ovp = calcular_logistica_otimizada(peso_g, sacas_input)
                
                try:
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': fib_boxes,
                        'PESO_G': f"{saca_kg:.2f}".replace('.', ','),
                        'TOTAL_OVERPACK': f"{total_ovp:.2f}".replace('.', ','),
                        'MARCACAO': sigla,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': sacas_input
                    }
                    doc.render(contexto)
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"✅ Encontrado! Peso Total: {peso_g}kg")
                    st.download_button("📥 Baixar Shipper", output, f"Shipper_{sigla}.docx")
                except Exception as e:
                    st.error(f"Erro no modelo Word: {e}")
            else:
                st.error(f"Destino '{termo}' não encontrado abaixo da linha de títulos.")
    else:
        st.error("Não consegui encontrar as colunas 'DESTINO' e 'PESO' na planilha. Verifique os títulos.")
