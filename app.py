import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# 1. INTERFACE
st.set_page_config(page_title="Gerador New Post", layout="wide")
st.title("Gerador de Shippers - New Post")

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
                    # --- LÓGICA DE PRECISÃO TOTAL ---
                    peso_total_geral = pd.to_numeric(df_f[c_peso], errors='coerce').sum()
                    
                    # 1. TOTAL POR SACA (K) - DIVISÃO DIRETA E ARREDONDADA
                    # Ex: 131,32 / 7 = 18,76 (Travado em 2 casas)
                    valor_saca = round(peso_total_geral / sacas_f, 2)
                    
                    # 2. FIBREBOARD (I)
                    # Regra do 0.50 ou trava para CGB
                    if sigla == "CGB" and sacas_f == 7:
                        fib_boxes = 4
                    else:
                        v_i = valor_saca / 4.5
                        fib_boxes = math.ceil(v_i) if (v_i - int(v_i)) > 0.50 else math.floor(v_i)

                    # 3. PESO G (J) - DIVISÃO DO VALOR DA SACA PELA QTD DE CAIXAS
                    # Ex: 18,76 / 4 = 4,69
                    valor_caixa = round(valor_saca / fib_boxes, 2)
                    
                    # --- CONVERSÃO PARA TEXTO (IMPEDE ARREDONDAMENTO DO WORD) ---
                    txt_saca = "{:.2f}".format(valor_saca).replace('.', ',')
                    txt_caixa = "{:.2f}".format(valor_caixa).replace('.', ',')
                    
                    marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                    # 4. GERAÇÃO
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': int(fib_boxes),
                        'PESO_G': txt_caixa,
                        'TOTAL_OVERPACK': txt_saca,
                        'MARCACAO': marcacao,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': int(sacas_f)
                    }
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"✅ Calculado com Sucesso! Saca: {txt_saca} | Caixa: {txt_caixa}")
                    st.download_button(f"📥 BAIXAR SHIPPER {sigla}", output, f"Shipper_{sigla}.docx")
                else:
                    st.error(f"Destino {cidade} não localizado.")
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
