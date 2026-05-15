import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
import math
from datetime import date

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gerador de Shippers", layout="wide")

# ESTILO VISUAL (BOTÃO VERDE E TÍTULO AZUL)
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button {
        background-color: #28a745 !important;
        color: white !important;
        border-radius: 5px;
        width: 100%;
        font-weight: bold;
        height: 3.5em;
        border: none;
    }
    h1 { color: #003366; text-align: center; }
    </style>
    """, unsafe_allow_index=True)

st.title("Gerador de Shippers")

# ENTRADA DE DADOS
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (Ex: POA):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas (Coluna F):", min_value=1, step=1)

file = st.file_uploader("Upload da Planilha de Coleta", type=["xlsx"])

# LÓGICA DE PROCESSAMENTO
if file and sigla:
    try:
        # 1. Leitura da Planilha e Localização do Cabeçalho
        df_raw = pd.read_excel(file, header=None)
        header_row = None
        for i in range(min(30, len(df_raw))):
            linha = [str(val).upper().strip() for val in df_raw.iloc[i].values]
            if "DESTINO" in linha or "PESO" in linha:
                header_row = i
                break
        
        if header_row is not None:
            df = pd.read_excel(file, header=header_row)
            df.columns = [str(c).strip().upper().replace('\\n', '') for c in df.columns]

            # 2. Botão de Geração
            if st.button(f"GERAR SHIPPER {sigla}"):
                col_dest = next((c for c in df.columns if "DESTINO" in c), None)
                col_peso = next((c for c in df.columns if "PESO" in c), None)

                if col_dest and col_peso:
                    # Filtro do Destino
                    mapa = {"POA": "PORTO ALEGRE", "CWB": "CURITIBA", "MAO": "MANAUS", "CGB": "CUIABA"}
                    termo = mapa.get(sigla, sigla)
                    df_f = df[df[col_dest].astype(str).str.contains(termo, na=False, case=False)]
                    df_f = df_f[~df_f[col_dest].astype(str).str.upper().str.contains("TOTAL", na=False)]

                    if not df_f.empty:
                        # 3. Cálculos (Lógica exata do seu Excel)
                        peso_g = pd.to_numeric(df_f[col_peso], errors='coerce').sum()
                        
                        # Coluna I (Fib Boxes)
                        valor_div_i = peso_g / sacas_f
                        fracao_i = valor_div_i - int(valor_div_i)
                        fib_boxes_i = math.ceil(valor_div_i) if fracao_i > 0.50 else math.floor(valor_div_i)
                        
                        # Coluna J (Saca kg) - Arredonda pra cima na 2ª casa
                        total_unid = sacas_f * fib_boxes_i
                        saca_kg_j = math.ceil((peso_g / total_unid) * 100) / 100 if total_unid > 0 else 0
                        
                        # Coluna K (Total Overpack)
                        total_ovp = total_unid * saca_kg_j
                        
                        # Marcação (#1 #2...)
                        texto_marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])
                        
                        # 4. Geração do Documento Word
                        doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                        contexto = {
                            'FIBREBOARD': int(fib_boxes_i),
                            'PESO_G': f"{saca_kg_j:.2f}".replace('.', ','),
                            'TOTAL_OVERPACK': f"{total_ovp:.2f}".replace('.', ','),
                            'MARCACAO': texto_marcacao,
                            'DATA': date.today().strftime('%d/%m/%Y'),
                            'QTD_OVERPACK': int(sacas_f)
                        }
                        doc.render(contexto)
                        
                        # Preparação do Download
                        output = io.BytesIO()
                        doc.save(output)
                        output.seek(0)
                        
                        st.success("✅ Documento gerado com sucesso!")
                        st.download_button(f"📥 BAIXAR SHIPPER {sigla}", output, f"Shipper_{sigla}.docx")
                    else:
                        st.error(f"Destino '{termo}' não encontrado.")
                else:
                    st.error("Colunas DESTINO ou PESO não identificadas.")
        else:
            st.info("Planilha carregada. Preencha os dados e clique no botão verde.")
            
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")
