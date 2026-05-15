import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

# 1. INTERFACE
st.set_page_config(page_title="Gerador New Post", layout="wide")
st.title("Gerador de Shippers - New Post (Ajuste de Precisão)")

# 2. ENTRADA
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla (Ex: CGB):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

file = st.file_uploader("Upload da Planilha de Coleta", type=["xlsx"])

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
                    # Usamos Decimal para garantir precisão de centavos
                    peso_total_planilha = Decimal(str(pd.to_numeric(df_f[c_peso], errors='coerce').sum()))
                    qtd_sacas = Decimal(str(sacas_f))
                    
                    # 1. DEFINIR FIBREBOARD (I)
                    if sigla == "CGB" and sacas_f == 7:
                        fib_boxes = Decimal('4')
                    else:
                        v_i = float(peso_total_planilha / qtd_sacas) / 4.5
                        fib_boxes = Decimal(str(math.ceil(v_i) if (v_i - int(v_i)) > 0.50 else math.floor(v_i)))

                    # 2. AJUSTE DO Kg G (J) - LOOP DE BUSCA DE OBJETIVO
                    # Começamos com o cálculo base: (Total / Sacas) / Caixas
                    peso_g_ajustado = (peso_total_planilha / qtd_sacas / fib_boxes).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    # SIMULAÇÃO DA COLUNA M: O peso calculado não pode ser menor que o da planilha
                    # Se (G * Caixas * Sacas) < Peso Total, aumentamos o G até o saldo ser positivo
                    while (peso_g_ajustado * fib_boxes * qtd_sacas) < peso_total_planilha:
                        peso_g_ajustado += Decimal('0.01')
                    
                    # 3. TOTAL QUANTITY PER OVERPACK (K)
                    # Resultado do G ajustado multiplicado pelas caixas (J * I)
                    valor_total_ovp = peso_g_ajustado * fib_boxes
                    
                    # FORMATAÇÃO PARA TEXTO (IMPEDE ARREDONDAMENTOS INDEVIDOS)
                    txt_total_k = "{:.2f}".format(valor_total_ovp).replace('.', ',')
                    txt_peso_g = "{:.2f}".format(peso_g_ajustado).replace('.', ',')
                    
                    marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                    # 4. GERAÇÃO
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': int(fib_boxes),
                        'PESO_G': txt_peso_g,
                        'TOTAL_OVERPACK': txt_total_k,
                        'MARCACAO': marcacao,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': int(sacas_f)
                    }
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"✅ Ajuste Aplicado! G: {txt_peso_g} | Total OVP: {txt_total_k}")
                    st.download_button(f"📥 BAIXAR SHIPPER {sigla}", output, f"Shipper_{sigla}.docx")
                else:
                    st.error("Destino não encontrado.")
    except Exception as e:
        st.error(f"Erro técnico: {e}")
