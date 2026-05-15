import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
from datetime import date

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Gerador New Post", layout="wide")
st.title(" 📄 Gerador de Shippers - New post")

# 2. ENTRADA
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (Ex: CGB):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

# Aceita tanto .xlsx quanto .xlsm
file = st.file_uploader("Upload da Planilha de Informações (.xlsx ou .xlsm)", type=["xlsx", "xlsm"])

if file and sigla:
    try:
        # Lendo a planilha (engine='openpyxl' para suportar macros)
        # Lemos sem cabeçalho primeiro para identificar as colunas pela letra
        df = pd.read_excel(file, header=None, engine='openpyxl')
        
        if st.button(f"GERAR SHIPPER {sigla}"):
            # Localiza a linha que contém a Sigla na Coluna A (Índice 0) ou B (Índice 1)
            # Geralmente o destino está nas primeiras colunas
            mask = df.astype(str).apply(lambda x: x.str.contains(sigla, case=False)).any(axis=1)
            linha_destino = df[mask]

            if not linha_destino.empty:
                # Pegamos a primeira ocorrência
                dados = linha_destino.iloc[0]
                
                # MAPEAMENTO PELAS LETRAS DA PLANILHA (Índice começa em 0)
                # I = 8, J = 9, K = 10
                v_fibreboard = dados[8]  # Coluna I
                v_kg_g = dados[9]       # Coluna J
                v_total_overpack = dados[10] # Coluna K

                # Função para garantir o formato 0,00
                def formatar_valor(valor):
                    try:
                        return "{:.2f}".format(float(valor)).replace('.', ',')
                    except:
                        return str(valor).replace('.', ',')

                txt_kg_g = formatar_valor(v_kg_g)
                txt_total_k = formatar_valor(v_total_overpack)
                
                # Etiquetas (#1 #2...)
                marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                # 3. GERAÇÃO
                doc_path = f"templates/{sigla}-SHIPPER-t.docx"
                doc = DocxTemplate(doc_path)
                
                contexto = {
                    'FIBREBOARD': int(v_fibreboard) if v_fibreboard else 0,
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
                
                st.success(f"✅ Dados extraídos das colunas I, J, K para {sigla}!")
                st.download_button(
                    label=f"📥 BAIXAR SHIPPER {sigla}",
                    data=output,
                    file_name=f"Shipper_{sigla}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            else:
                st.error(f"Destino '{sigla}' não encontrado na planilha.")
                
    except Exception as e:
        st.error(f"Erro ao ler planilha com macros: {e}")
