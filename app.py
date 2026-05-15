import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# --- NOVAS REGRAS DE CÁLCULO ---

def arredondar_I(valor):
    """Regra: > 0.50 sobe, <= 0.50 desce (Ex: 7.38=7, 8.79=9)"""
    fracao = valor - int(valor)
    return math.ceil(valor) if fracao > 0.50 else math.floor(valor)

def calcular_logistica_otimizada(peso_total, qtd_sacas_input):
    if qtd_sacas_input <= 0: return 0, 0, 0
    
    # 1. Valor inicial da Coluna I (Peso Total / Sacas Digitadas)
    valor_i_inicial = peso_total / qtd_sacas_input
    fib_boxes_arred = arredondar_I(valor_i_inicial)
    
    # 2. Otimização da Coluna J (Saca kg)
    # Buscamos o valor que deixa (L - G) o mais próximo de 0 e positivo
    melhor_saca_kg = 0.001
    menor_sobra_positiva = float('inf')
    
    # Testamos de 0.001 até 30.000 kg (ajuste o limite se necessário)
    for saca_teste in [i/1000 for i in range(1, 30001)]:
        peso_calculado_l = (qtd_sacas_input * fib_boxes_arred) * saca_teste
        sobra_m = peso_calculado_l - peso_total
        
        if sobra_m >= 0 and sobra_m < menor_sobra_positiva:
            menor_sobra_positiva = sobra_m
            melhor_saca_kg = saca_teste
            if sobra_m == 0: break # Perfeito
            
    # 3. Valor da Coluna K (O que vai para a etiqueta)
    total_overpack = (qtd_sacas_input * fib_boxes_arred) * melhor_saca_kg
    
    return fib_boxes_arred, melhor_saca_kg, round(total_overpack, 3)

# --- INTERFACE ---
st.set_page_config(page_title="Gerador New Post 📝", layout="wide")
st.title("📝 Gerador de Shipper (Nova Regra Logística)")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla (Ex: POA):").upper().strip()
with col2:
    sacas_input = st.number_input("Qtd de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Planilha de Coleta", type=["xlsx"])

if file and sigla:
    df = pd.read_excel(file, header=2) # Cabeçalho na linha 3
    df.columns = [str(c).strip().upper() for c in df.columns]

    if st.button(f"Gerar Documento {sigla}"):
        # Mapeamento para buscar na planilha (ex: POA -> PORTO ALEGRE)
        mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
        termo = mapa.get(sigla, sigla)
        
        df_f = df[df['DESTINO'].astype(str).str.contains(termo, na=False, case=False)]
        df_f = df_f[df_f['DESTINO'].astype(str).upper() != 'TOTAL GERAL']

        if not df_f.empty:
            peso_g = df_f['PESO'].sum()
            
            # Aplica os cálculos do vídeo
            fib_boxes, saca_kg, total_overpack = calcular_logistica_otimizada(peso_g, sacas_input)
            
            # Mostra os cálculos para conferência
            st.info(f"📊 Peso Original: {peso_g}kg | Fib Boxes: {fib_boxes} | Saca kg: {saca_kg}")
            
            try:
                doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                contexto = {
                    'FIBREBOARD': fib_boxes,       # Coluna I arredondada
                    'PESO_G': saca_kg,            # Coluna J otimizada
                    'TOTAL_OVERPACK': total_overpack, # Coluna K
                    'MARCACAO': sigla,
                    'DATA': date.today().strftime('%d/%m/%Y'),
                    'QTD_OVERPACK': sacas_input   # Coluna F
                }
                doc.render(contexto)
                
                output = io.BytesIO()
                doc.save(output)
                output.seek(0)
                
                st.success(f"Concluído! Total Overpack: {total_overpack}kg")
                st.download_button("📥 Baixar Shipper", output, f"Shipper_{sigla}.docx")
            except Exception as e:
                st.error(f"Erro no modelo: {e}")
