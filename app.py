import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

# 1. INTERFACE
st.set_page_config(page_title="Gerador New Post", layout="wide")
st.title("Gerador de Shippers - New Post (Lógica de Saldo)")

# 2. ENTRADA DE DADOS
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
                    # --- VARIÁVEIS CONFORME A SUA EXPLICAÇÃO ---
                    # Peso Real (Coluna G da planilha)
                    g7_peso_real = Decimal(str(pd.to_numeric(df_f[c_peso], errors='coerce').sum()))
                    f7_qtd_sacas = Decimal(str(sacas_f))
                    
                    # PASSO 1: FIBREBOARD (Coluna I)
                    if sigla == "CGB" and sacas_f == 7:
                        i7_fib = Decimal('4')
                    else:
                        v_i = float(g7_peso_real / f7_qtd_sacas) / 4.5
                        i7_fib = Decimal(str(math.ceil(v_i) if (v_i - int(v_i)) > 0.50 else math.floor(v_i)))

                    # PASSO 2: AJUSTE DO Kg G (Coluna J) ATÉ M >= 0
                    # Iniciamos o J com o cálculo base arredondado
                    j7_kg_g = (g7_peso_real / f7_qtd_sacas / i7_fib).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    # LOOP DE BUSCA DE OBJETIVO (O que você faz manualmente no Excel)
                    while True:
                        # K = J * I (Peso da saca)
                        k7_saca = j7_kg_g * i7_fib
                        # L = K * F (Peso total calculado/simulado)
                        l7_peso_simulado = k7_saca * f7_qtd_sacas
                        # M = L - G (Saldo)
                        m7_saldo = l7_peso_simulado - g7_peso_real
                        
                        if m7_saldo >= 0:
                            # Se a coluna M zerou ou ficou positiva, o Kg G está correto
                            break
                        else:
                            # Se M ainda for negativa, subimos o Kg G em 0.01
                            j7_kg_g += Decimal('0.01')
                    
                    # VALORES FINAIS APÓS AJUSTE
                    txt_kg_g = "{:.2f}".format(j7_kg_g).replace('.', ',')
                    txt_total_k = "{:.2f}".format(j7_kg_g * i7_fib).replace('.', ',')
                    
                    marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                    # 3. GERAÇÃO DO DOCUMENTO
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    contexto = {
                        'FIBREBOARD': int(i7_fib),
                        'PESO_G': txt_kg_g,
                        'TOTAL_OVERPACK': txt_total_k,
                        'MARCACAO': marcacao,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': int(sacas_f)
                    }
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"✅ Lógica Aplicada! Kg G: {txt_kg_g} | Total K: {txt_total_k} | Saldo M: {m7_saldo}")
                    st.download_button(f"📥 BAIXAR SHIPPER {sigla}", output, f"Shipper_{sigla}.docx")
                else:
                    st.error("Destino não localizado.")
    except Exception as e:
        st.error(f"Erro: {e}")
