import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
from datetime import date
from zipfile import ZipFile # Biblioteca para criar o arquivo ZIP

# 1. CONFIGURAÇÃO
st.set_page_config(page_title=" 📄 Gerador de shippers - New post logística", layout="wide")
st.title("Gerador de Shippers em Lote")
st.markdown("Digite as siglas separadas por vírgula para baixar tudo de uma vez.")

# 2. MAPA DE TRADUÇÃO
MAPA_DESTINOS = {
    "CGR": "CAMPO GRANDE",
    "CGB": "CUIABA",
    "CWB": "CURITIBA",
    "FLN": "FLORIANOPOLIS",
    "GYN": "GOIANIA",
    "MAO": "MANAUS",
    "POA": "PORTO ALEGRE",
    "PVH": "PORTO VELHO"
}

# 3. ENTRADA MULTIPLA
# Agora aceita: CGB, POA, MAO
siglas_input = st.text_input("Digite as Siglas (Ex: CGB, POA, MAO):").upper().strip()

file = st.file_uploader("Upload da Planilha de Informações (.xlsm)", type=["xlsm", "xlsx"])

if file and siglas_input:
    try:
        df = pd.read_excel(file, header=None, engine='openpyxl')
        
        # Transforma a entrada "CGB, POA" em uma lista ['CGB', 'POA']
        lista_siglas = [s.strip() for s in siglas_input.split(",")]

        if st.button(f"GERAR {len(lista_siglas)} SHIPPERS"):
            # Criamos um "balde" (buffer) para guardar o arquivo ZIP na memória
            zip_buffer = io.BytesIO()

            with ZipFile(zip_buffer, "w") as zip_file:
                processados = 0
                
                for sigla in lista_siglas:
                    termo_busca = MAPA_DESTINOS.get(sigla, sigla)
                    
                    # Localiza a linha do destino
                    dados = None
                    for index, row in df.iterrows():
                        linha_texto = " ".join([str(val).upper() for val in row.values if pd.notnull(val)])
                        if termo_busca in linha_texto:
                            dados = row
                            break
                    
                    if dados is not None:
                        # Extração das colunas F, I, J, K
                        v_sacas      = dados[5]   
                        v_fibreboard = dados[8]   
                        v_kg_g       = dados[9]   
                        v_total_ovp  = dados[10]  

                        def formatar(v):
                            try: return "{:.2f}".format(float(v)).replace('.', ',')
                            except: return str(v).replace('.', ',')

                        qtd_sacas = int(v_sacas) if pd.notnull(v_sacas) else 1
                        
                        # Gera o conteúdo do Word
                        try:
                            doc = DocxTemplate(f"templates/{sigla}-SHIPPER-t.docx")
                            contexto = {
                                'FIBREBOARD': int(v_fibreboard) if pd.notnull(v_fibreboard) else 0,
                                'PESO_G': formatar(v_kg_g),
                                'TOTAL_OVERPACK': formatar(v_total_ovp),
                                'MARCACAO': " ".join([f"#{i+1}" for i in range(qtd_sacas)]),
                                'DATA': date.today().strftime('%d/%m/%Y'),
                                'QTD_OVERPACK': qtd_sacas
                            }
                            doc.render(contexto)

                            # Salva este Word específico dentro do ZIP
                            doc_io = io.BytesIO()
                            doc.save(doc_io)
                            zip_file.writestr(f"Shipper_{sigla}.docx", doc_io.getvalue())
                            processados += 1
                        except:
                            st.error(f"Template para {sigla} não encontrado.")

                if processados > 0:
                    zip_buffer.seek(0)
                    st.success(f"✅ {processados} Shippers preparadas!")
                    st.download_button(
                        label="📥 BAIXAR TODAS (ARQUIVO ZIP)",
                        data=zip_buffer,
                        file_name=f"Shippers_NewPost_{date.today()}.zip",
                        mime="application/zip"
                    )
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
