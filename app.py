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
                    # --- INÍCIO DA LÓGICA DA PLANILHA ---
                    peso_total_planilha = pd.to_numeric(df_f[c_peso], errors='coerce').sum()
                    
                    # PASSO 1: DEFINIR FIBREBOARD (I)
                    # Valor base para decidir as caixas (Coluna K provisória)
                    k_base = peso_total_planilha / sacas_f
                    
                    if sigla == "CGB" and sacas_f == 7:
                        fib_boxes = 4
                    else:
                        v_i = k_base / 4.5
                        sobra = v_i - int(v_i)
                        fib_boxes = math.ceil(v_i) if sobra > 0.50 else math.floor(v_i)

                    # PASSO 2: AJUSTE DO Kg G (Coluna J) ATÉ M >= 0
                    # Começamos com o cálculo exato e arredondamos
                    peso_g_ajustado = round((peso_total_planilha / sacas_f) / fib_boxes, 2)
                    
                    # LOOP DE OTIMIZAÇÃO (Simula o ajuste manual da coluna J)
                    while True:
                        # Cálculo do Total que esse Peso G geraria no final
                        # (J * I * Sacas)
                        total_simulado = round(peso_g_ajustado * fib_boxes * sacas_f, 2)
                        
                        # Coluna M (Saldo)
                        saldo_m = round(total_simulado - peso_total_planilha, 2)
                        
                        if saldo_m >= 0:
                            # Encontramos o valor positivo mais próximo de zero!
                            break
                        else:
                            # Se saldo for negativo (ex: -1,27), subimos 0,01 no Kg G
                            peso_g_ajustado = round(peso_g_ajustado + 0.01, 2)
                    
                    # PASSO 3: DEFINIR O TOTAL QUANTITY PER OVERPACK (K) FINAL
                    # É o Peso G ajustado multiplicado pelas caixas (J * I)
                    valor_k_final = round(peso_g_ajustado * fib_boxes, 2)
                    
                    # FORMATAÇÃO PARA O WORD
                    txt_total_k = "{:.2f}".format(valor_k_final).replace('.', ',')
                    txt_peso_g = "{:.2f}".format(peso_g_ajustado).replace('.', ',')
                    
                    marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                    # 3. GERAÇÃO DO DOC
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
                    
                    st.success(f"✅ Otimização Concluída! G: {txt_peso_g} | Total K: {txt_total_k}")
                    st.download_button(f"📥 BAIXAR SHIPPER {sigla}", output, f"Shipper_{sigla}.docx")
                else:
                    st.error("Destino não encontrado.")
    except Exception as e:
        st.error(f"Erro: {e}")
