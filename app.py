import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# Lógica de Arredondamento
def arredondar_logistica(valor):
    try:
        valor_num = float(str(valor).replace(',', '.'))
        return math.ceil(valor_num) if valor_num > 0 else 0
    except: return 0

st.set_page_config(page_title="Gerador New Post 📝")
st.title("📝 Gerador de Shipper Direto")

col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (ex: CWB):").upper().strip()
with col2:
    sacas = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

file = st.file_uploader("Selecione a Planilha de Coleta", type=["xlsx"])

if file and sigla:
    # O ajuste 'header=2' faz o código ler a partir da linha 3 do Excel
    df = pd.read_excel(file, header=2)
    
    # Limpa os nomes das colunas para evitar erros com espaços ou letras minúsculas
    df.columns = [str(c).strip().upper() for c in df.columns]

    if st.button(f"Gerar Documento para {sigla}"):
        if 'DESTINO' in df.columns:
            # Filtra apenas o destino digitado
            df_filtrado = df[df['DESTINO'].astype(str).str.contains(sigla, na=False, case=False)]
            
            if df_filtrado.empty:
                st.error(f"Destino {sigla} não encontrado na coluna DESTINO (Linha 3).")
                st.write("Colunas lidas pelo sistema:", list(df.columns))
            else:
                peso_total = arredondar_logistica(df_filtrado['PESO'].sum())
                
                try:
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    
                    contexto = {
                        'FIBREBOARD': int(sacas),
                        'PESO_G': peso_total,
                        'MARCACAO': sigla,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'TOTAL_OVERPACK': peso_total,
                        'QTD_OVERPACK': 1
                    }
                    
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"Documento de {sigla} gerado! Peso total somado: {peso_total}kg")
                    st.download_button(
                        label="📥 Baixar Arquivo Preenchido",
                        data=output,
                        file_name=f"Shipper_{sigla}_{date.today().strftime('%d%m%Y')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except FileNotFoundError:
                    st.error(f"Modelo '{sigla}-SHIPPER-t.docx' não encontrado na pasta templates.")
        else:
            st.error("A coluna 'DESTINO' não foi encontrada na linha 3 da planilha.")
            st.write("Colunas detectadas:", list(df.columns))
