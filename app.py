import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
from datetime import date

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Gerador New Post", layout="wide")
st.title("Gerador de Shippers - Busca Flexível (XLSM)")

# 2. ENTRADA
col1, col2 = st.columns(2)
with col1:
    # Agora você pode digitar a sigla ou parte do nome (ex: CUIABA)
    busca_destino = st.text_input("Digite o Destino ou Sigla (Ex: CUIABA ou CGB):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas:", min_value=1, step=1)

file = st.file_uploader("Upload da Planilha de Informações (.xlsm)", type=["xlsm", "xlsx"])

if file and busca_destino:
    try:
        # Carrega a planilha ignorando erros de formatação
        df = pd.read_excel(file, header=None, engine='openpyxl')
        
        if st.button(f"GERAR SHIPPER"):
            # BUSCA FLEXÍVEL: Procura em todas as linhas se o termo digitado aparece 
            # em alguma célula das primeiras colunas (onde costuma ficar o destino)
            def localizar_linha(termo, dataframe):
                for index, row in dataframe.iterrows():
                    # Verifica as colunas A, B e C (índices 0, 1, 2)
                    celulas_texto = " ".join([str(val).upper() for val in row.values[:5]])
                    if termo in celulas_texto:
                        return row
                return None

            dados = localizar_linha(busca_destino, df)

            if dados is not None:
                # MAPEAMENTO PELAS LETRAS DA PLANILHA (Índice começa em 0)
                # I = 8, J = 9, K = 10
                v_fibreboard = dados[8]  # Coluna I
                v_kg_g = dados[9]       # Coluna J
                v_total_overpack = dados[10] # Coluna K

                # Função para formatar números no padrão brasileiro (0,00)
                def formatar_valor(valor):
                    try:
                        val_float = float(valor)
                        return "{:.2f}".format(val_float).replace('.', ',')
                    except:
                        return str(valor).replace('.', ',')

                txt_kg_g = formatar_valor(v_kg_g)
                txt_total_k = formatar_valor(v_total_overpack)
                
                # Gera as etiquetas (#1 #2 #3...)
                marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                # 3. GERAÇÃO (Usa a sigla digitada para buscar o template ex: CGB-SHIPPER-t.docx)
                # Se você digitou CUIABA e o template chama CGB, recomendo digitar a sigla
                sigla_arquivo = busca_destino if len(busca_destino) == 3 else "CGB" 
                
                try:
                    doc = DocxTemplate(f"templates/{sigla_arquivo}-SHIPPER-t.docx")
                except:
                    st.warning(f"Template '{sigla_arquivo}' não encontrado, tentando template padrão...")
                    doc = DocxTemplate("templates/CGB-SHIPPER-t.docx")

                contexto = {
                    'FIBREBOARD': int(v_fibreboard) if pd.notnull(v_fibreboard) else 0,
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
                
                st.success(f"✅ Destino localizado! Dados extraídos das colunas I, J, K.")
                st.download_button(
                    label=f"📥 BAIXAR SHIPPER",
                    data=output,
                    file_name=f"Shipper_{busca_destino}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            else:
                st.error(f"Não foi possível encontrar '{busca_destino}' na planilha. Verifique se o nome está correto.")
                
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
