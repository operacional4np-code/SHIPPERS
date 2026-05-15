import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# Lógica de Arredondamento
def arredondar_logistica(valor):
    try:
        # Garante que o valor seja tratado como número
        valor_num = float(valor)
        return math.ceil(valor_num) if valor_num > 0 else 0
    except: return 0

st.set_page_config(page_title="Gerador New Post 📝")
st.title("📝 Gerador de Shipper Direto")

col1, col2 = st.columns(2)
with col1:
    # O usuário digita POA, CWB, MAO, etc.
    sigla_busca = st.text_input("Sigla ou parte do Destino:").upper().strip()
with col2:
    sacas = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

file = st.file_uploader("Selecione a Planilha de Coleta", type=["xlsx"])

if file and sigla_busca:
    # header=2 indica que os títulos estão na linha 3 (index 2)
    df = pd.read_excel(file, header=2)
    
    # Limpa nomes das colunas e remove a linha "Total Geral" se existir
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df[df['DESTINO'].astype(str).upper() != 'TOTAL GERAL']

    if st.button(f"Gerar Documento para {sigla_busca}"):
        if 'DESTINO' in df.columns:
            # MAPEAMENTO: Se digitar POA, procura PORTO ALEGRE. Se digitar CWB, CURITIBA, etc.
            mapa_cidades = {
                "POA": "PORTO ALEGRE",
                "CWB": "CURITIBA",
                "CGB": "CUIABA",
                "CGR": "CAMPO GRANDE",
                "MAO": "MANAUS",
                "GYN": "GOIANIA",
                "FLN": "FLORIANOPOLIS",
                "PVH": "PORTO VELHO"
            }
            
            # Pega o termo de busca real (ex: POA vira PORTO ALEGRE)
            termo_real = mapa_cidades.get(sigla_busca, sigla_busca)
            
            # Filtra a planilha procurando o termo no nome completo do destino
            df_filtrado = df[df['DESTINO'].astype(str).str.contains(termo_real, na=False, case=False)]
            
            if df_filtrado.empty:
                st.error(f"Não encontramos '{termo_real}' na coluna DESTINO.")
                st.write("Destinos lidos na planilha:", df['DESTINO'].tolist())
            else:
                # Soma os pesos das linhas encontradas
                peso_total = arredondar_logistica(df_filtrado['PESO'].sum())
                
                try:
                    doc = DocxTemplate(f"templates/{sigla_busca}-SHIPPER-t.docx")
                    
                    contexto = {
                        'FIBREBOARD': int(sacas),
                        'PESO_G': peso_total,
                        'MARCACAO': sigla_busca, # Mantém a sigla na etiqueta
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'TOTAL_OVERPACK': peso_total,
                        'QTD_OVERPACK': 1
                    }
                    
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"Encontrado: {len(df_filtrado)} linha(s). Peso Total: {peso_total}kg")
                    st.download_button(
                        label=f"📥 Baixar Shipper {sigla_busca}",
                        data=output,
                        file_name=f"Shipper_{sigla_busca}_{date.today().strftime('%d%m%Y')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except FileNotFoundError:
                    st.error(f"Modelo templates/{sigla_busca}-SHIPPER-t.docx não encontrado.")
        else:
            st.error("Coluna 'DESTINO' não encontrada na linha 3.")
