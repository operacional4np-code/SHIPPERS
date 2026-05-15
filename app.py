import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# --- REGRAS DE CÁLCULO DO VÍDEO ---

def arredondar_I(valor):
    """Regra do vídeo: > 0.50 sobe, <= 0.50 desce"""
    fracao = valor - int(valor)
    return math.ceil(valor) if fracao > 0.50 else math.floor(valor)

def calcular_logistica_otimizada(peso_total, qtd_sacas_input):
    if qtd_sacas_input <= 0: return 0, 0, 0
    
    # 1. Coluna I (Fib Boxes)
    valor_i_inicial = peso_total / qtd_sacas_input
    fib_boxes_arred = arredondar_I(valor_i_inicial)
    
    # 2. Otimização da Coluna J (Saca kg) para que M >= 0
    melhor_saca_kg = 0.0
    menor_sobra_positiva = float('inf')
    
    # Testamos valores de peso unitário para achar o ajuste perfeito
    for saca_teste in [i/100 for i in range(1, 5000)]: # Testa de 0.01 até 50.00 kg
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
st.title("📝 Gerador de Shipper (Ajuste Automático)")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla (Ex: POA, CWB):").upper().strip()
with col2:
    sacas_input = st.number_input("Qtd de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Suba sua Planilha de Coleta", type=["xlsx"])

if file and sigla:
    # Lemos sem fixar a linha (header=None) para procurar os títulos dinamicamente
    df_raw = pd.read_excel(file)
    
    # Tenta localizar a linha que contém "DESTINO"
    header_row = 0
    for i, row in df_raw.iterrows():
        if "DESTINO" in [str(val).upper() for val in row.values]:
            header_row = i + 1
            break
    
    # Re-lemos a planilha agora com o cabeçalho correto
    df = pd.read_excel(file, header=header_row)
    df.columns = [str(c).strip().upper() for c in df.columns]

    if st.button(f"Gerar Documento {sigla}"):
        if 'DESTINO' in df.columns and 'PESO' in df.columns:
            # Filtro de Cidade
            mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA", "CGR": "CAMPO GRANDE"}
            termo = mapa.get(sigla, sigla)
            
            df_f = df[df['DESTINO'].astype(str).str.contains(termo, na=False, case=False)]
            df_f = df_f[df_f['DESTINO'].astype(str).upper() != 'TOTAL GERAL']

            if not df_f.empty:
                peso_g = pd.to_numeric(df_f['PESO'], errors='coerce').sum()
                
                # Cálculos automáticos (Simulando o seu vídeo)
                fib_boxes, saca_kg, total_overpack = calcular_logistica_otimizada(peso_g, sacas_input)
                
                try:
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': fib_boxes,
                        'PESO_G': f"{saca_kg:.2f}".replace('.', ','), # Formato 8,79
                        'TOTAL_OVERPACK': f"{total_overpack:.2f}".replace('.', ','),
                        'MARCACAO': sigla,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': sacas_input
                    }
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"✅ Sucesso! Peso: {peso_g}kg | Fib Boxes: {fib_boxes} | Saca kg: {saca_kg}")
                    st.download_button("📥 Baixar Shipper", output, f"Shipper_{sigla}.docx")
                except Exception as e:
                    st.error(f"Erro ao abrir modelo: {e}")
            else:
                st.error(f"Destino {sigla} não encontrado na planilha.")
        else:
            st.error("Não encontrei as colunas 'DESTINO' e 'PESO'. Verifique a planilha.")
