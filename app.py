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

# Interface simplificada
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (ex: CWB):").upper().strip()
with col2:
    sacas = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

file = st.file_uploader("Selecione a Planilha de Coleta", type=["xlsx"])

if file and sigla:
    df = pd.read_excel(file)
    df.columns = [str(c).strip().upper() for c in df.columns]

    if st.button(f"Gerar Documento para {sigla}"):
        if 'DESTINO' in df.columns:
            # Filtra apenas o destino digitado e soma os pesos
            df_filtrado = df[df['DESTINO'].astype(str).str.contains(sigla, na=False, case=False)]
            
            if df_filtrado.empty:
                st.error(f"Destino {sigla} não encontrado na planilha.")
            else:
                peso_total = arredondar_logistica(df_filtrado['PESO'].sum())
                
                try:
                    # Busca o modelo na pasta templates/
                    doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                    
                    # Preenche as tags {{ }} do seu Word
                    contexto = {
                        'FIBREBOARD': int(sacas),
                        'PESO_G': peso_total,
                        'MARCACAO': sigla,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'TOTAL_OVERPACK': peso_total,
                        'QTD_OVERPACK': 1
                    }
                    
                    doc.render(contexto)
                    
                    # Prepara o arquivo para download
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"Documento de {sigla} gerado com sucesso!")
                    st.download_button(
                        label="📥 Baixar Arquivo Preenchido",
                        data=output,
                        file_name=f"Shipper_{sigla}_{date.today().strftime('%d%m%Y')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except FileNotFoundError:
                    st.error(f"O modelo '{sigla}-SHIPPER-t.docx' não está na pasta templates.")
        else:
            st.error("A coluna 'DESTINO' não foi encontrada na planilha.")
