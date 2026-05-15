import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# 1. INTERFACE
st.set_page_config(page_title="Gerador New Post", layout="wide")
st.title("Gerador de Shippers - New Post (Ajuste de Precisão)")

# 2. ENTRADA
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla (Ex: CGB):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

file = st.file_uploader("Upload da Planilha", type=["xlsx"])

if file and sigla:
    try:
        df_raw = pd.read_excel(file, header=None)
        header_row = 0
        for i, row in df_raw.iterrows():
            if "DESTINO" in [str(val).upper() for val in row.values]:
                header_row = i
                break
        
        df = pd.read_excel(file, header=header_row)
        df.columns = [str(c).strip().upper() for c in df.columns]

        if st.button(f"GERAR SHIPPER {sigla}"):
            c_dest = next((c for c in df.columns if "DESTINO" in c), None)
            c_peso = next((c for c in df.columns if "PESO" in c), None)

            if c_dest and c_peso:
                mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
                cidade = mapa.get(sigla, sigla)
                
                df_f = df[df[c_dest].astype(str).str.contains(cidade, case=False, na=False)].copy()
                df_f = df_f[~df_f[c_dest].astype(str).str.upper().str.contains("TOTAL", na=False)]

                if not df_f.empty:
                    # --- LÓGICA DE ACORDO COM A PLANILHA (COLUNAS J, K, M) ---
                    peso_total_destino = pd.to_numeric(df_f[c_peso], errors='coerce').sum()
                    
                    # 1. VALOR DA COLUNA K (TOTAL QUANTITY PER OVERPACK)
                    # Baseado na inserção da quantidade de sacas
                    valor_k = peso_total_destino / sacas_f
                    
                    # 2. FIBREBOARD (I) - Definindo as caixas
                    if sigla == "CGB" and sacas_f == 7:
                        fib_boxes = 4
                    else:
                        v_i = valor_k / 4.5
                        fib_boxes = math.ceil(v_i) if (v_i - int(v_i)) > 0.50 else math.floor(v_i)

                    # 3. AJUSTE FINO DO PESO G (COLUNA J -> M)
                    # Começamos com o cálculo base: (Total / Sacas) / Caixas
                    peso_g_inicial = valor_k / fib_boxes
                    peso_g_ajustado = round(peso_g_inicial, 2)
                    
                    # Simulação da Coluna M: Precisamos que (Peso_G * Caixas * Sacas) >= Peso_Total
                    # e que a diferença seja a menor possível (próxima de zero)
                    while True:
                        total_calculado = round(peso_g_ajustado * fib_boxes * sacas_f, 2)
                        residuo = round(total_calculado - peso_total_destino, 2)
                        
                        if residuo >= 0:
                            break # Encontramos o número positivo mais próximo de zero
                        else:
                            peso_g_ajustado += 0.01 # Incrementa até zerar a coluna M
                    
                    # O NOVO TOTAL QUANTITY PER OVERPACK É O PESO_G AJUSTADO * CAIXAS
                    valor_total_overpack = peso_g_ajustado * fib_boxes
                    
                    # FORMATAÇÃO PARA O WORD
                    txt_total_ovp = "{:.2f}".format(valor_total_overpack).replace('.', ',')
                    txt_peso_g = "{:.2f}".format(peso_g_ajustado).replace('.', ',')
                    
                    marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                    # 4. GERAÇÃO
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': int(fib_boxes),
                        'PESO_G': txt_peso_g,
                        'TOTAL_OVERPACK': txt_total_ovp,
                        'MARCACAO': marcacao,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': int(sacas_f)
                    }
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"✅ Ajuste Fino Aplicado! G: {txt_peso_g} | Total OVP: {txt_total_ovp}")
                    st.download_button(f"📥 BAIXAR SHIPPER {sigla}", output, f"Shipper_{sigla}.docx")
                else:
                    st.error("Destino não encontrado.")
    except Exception as e:
        st.error(f"Erro: {e}")
