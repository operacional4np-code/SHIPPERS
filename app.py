import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# Lógica de Arredondamento para Logística
def arredondar_logistica(valor):
    try:
        # Converte para string, troca vírgula por ponto e vira número
        valor_limpo = str(valor).replace(',', '.').strip()
        valor_num = float(valor_limpo)
        return math.ceil(valor_num) if valor_num > 0 else 0
    except:
        return 0

st.set_page_config(page_title="Gerador New Post 📝", layout="wide")
st.title("📝 Gerador de Shipper")

col1, col2 = st.columns(2)
with col1:
    # O que você digita (Ex: POA, CWB, MAO)
    sigla_busca = st.text_input("Sigla do Destino (Ex: POA, CWB):").upper().strip()
with col2:
    sacas = st.number_input("Quantidade de Sacas (Fibreboard):", min_value=1, step=1)

file = st.file_uploader("Selecione a Planilha de Coleta", type=["xlsx"])

if file and sigla_busca:
    # header=2 lê a partir da linha 3 (onde estão os títulos DESTINO, PESO...)
    df = pd.read_excel(file, header=2)
    
    # Padroniza nomes das colunas: remove espaços e deixa em maiúsculo
    df.columns = [str(c).strip().upper() for c in df.columns]

    if st.button(f"Gerar Documento {sigla_busca}"):
        if 'DESTINO' in df.columns:
            # Tradução de Sigla para Nome na Planilha
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
            
            termo_real = mapa_cidades.get(sigla_busca, sigla_busca)
            
            # FILTRAGEM SEGURA:
            # 1. Transforma a coluna DESTINO em texto
            # 2. Remove a linha 'Total Geral'
            # 3. Procura o termo (ex: PORTO ALEGRE) dentro do nome completo
            df['DESTINO_STR'] = df['DESTINO'].astype(str).str.upper()
            df_limpo = df[df['DESTINO_STR'] != 'TOTAL GERAL']
            df_filtrado = df_limpo[df_limpo['DESTINO_STR'].str.contains(termo_real, na=False)]
            
            if df_filtrado.empty:
                st.error(f"Destino '{termo_real}' não encontrado na planilha.")
                st.write("Destinos detectados:", df_limpo['DESTINO'].unique().tolist())
            else:
                # Soma os pesos das linhas encontradas (ex: AGF + PRIME)
                peso_bruto_total = df_filtrado['PESO'].sum()
                peso_final = arredondar_logistica(peso_bruto_total)
                
                try:
                    # Carrega o modelo Word
                    doc = DocxTemplate(f"templates/{sigla_busca}-SHIPPER-t.docx")
                    
                    contexto = {
                        'FIBREBOARD': int(sacas),
                        'PESO_G': peso_final,
                        'MARCACAO': sigla_busca,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'TOTAL_OVERPACK': peso_final,
                        'QTD_OVERPACK': 1
                    }
                    
                    doc.render(contexto)
                    
                    # Prepara o download
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"Sucesso! {len(df_filtrado)} linha(s) somada(s). Peso: {peso_final}kg")
                    st.download_button(
                        label="📥 Baixar Shipper Preenchido",
                        data=output,
                        file_name=f"Shipper_{sigla_busca}_{date.today().strftime('%d%m%Y')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"Erro ao carregar o modelo: {e}")
        else:
            st.error("Coluna 'DESTINO' não encontrada na linha 3.")
