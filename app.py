import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
from datetime import date

# 1. CONFIGURAÇÃO DA INTERFACE
st.set_page_config(page_title="Gerador New Post", layout="wide")
st.title("Gerador de Shippers - Preenchimento Direto")
st.markdown("Este modo apenas lê as colunas **I, J e K** da planilha e preenche o Word.")

# 2. ENTRADA DE DADOS
col1, col2 = st.columns(2)
with col1:
    sigla = st.text_input("Sigla do Destino (Ex: CGB):").upper().strip()
with col2:
    sacas_f = st.number_input("Quantidade de Sacas (Etiquetas):", min_value=1, step=1)

file = st.file_uploader("Upload da Planilha de Informações para Shippers", type=["xlsx"])

if file and sigla:
    try:
        # Lendo a planilha (ajustando para encontrar o cabeçalho)
        df_raw = pd.read_excel(file, header=None)
        header_row = 0
        for i, row in df_raw.iterrows():
            if "DESTINO" in [str(val).upper() for val in row.values]:
                header_row = i
                break
        
        df = pd.read_excel(file, header=header_row)
        df.columns = [str(c).strip().upper() for c in df.columns]

        if st.button(f"GERAR SHIPPER {sigla}"):
            # Localizando a linha do destino
            # Filtra pela sigla ou nome do destino
            df_f = df[df['DESTINO'].astype(str).str.contains(sigla, case=False, na=False)].copy()
            
            if not df_f.empty:
                # PEGA OS DADOS DIRETAMENTE DAS COLUNAS (Sem cálculos extras)
                # Coluna I: FIBREBOARD
                # Coluna J: Kg G (Unitário)
                # Coluna K: TOTAL QUANTITY PER OVERPACK
                
                # Pegamos a primeira linha encontrada para esse destino
                dados = df_f.iloc[0]
                
                v_fibreboard = dados.get('FIBREBOARD', 0)
                v_kg_g = dados.get('KG G', 0)
                v_total_overpack = dados.get('TOTAL QUANTITY PER OVERPACK', 0)

                # Formatação para o Word (Troca ponto por vírgula e mantém 2 casas decimais)
                def formatar_pt_br(valor):
                    try:
                        return "{:.2f}".format(float(valor)).replace('.', ',')
                    except:
                        return str(valor).replace('.', ',')

                txt_kg_g = formatar_pt_br(v_kg_g)
                txt_total_k = formatar_pt_br(v_total_overpack)
                
                # Gera as etiquetas (#1 #2 #3...)
                marcacao = " ".join([f"#{i+1}" for i in range(int(sacas_f))])

                # 3. GERAÇÃO DO DOCUMENTO
                # O template deve estar na pasta 'templates' com o nome correspondente
                doc_path = f"templates/{sigla}-SHIPPER-t.docx"
                doc = DocxTemplate(doc_path)
                
                contexto = {
                    'FIBREBOARD': int(v_fibreboard),
                    'PESO_G': txt_kg_g,
                    'TOTAL_OVERPACK': txt_total_k,
                    'MARCACAO': marcacao,
                    'DATA': date.today().strftime('%d/%m/%Y'),
                    'QTD_OVERPACK': int(sacas_f)
                }
                
                doc.render(contexto)
                
                # Salva em memória para o download
                output = io.BytesIO()
                doc.save(output)
                output.seek(0)
                
                st.success(f"✅ Shipper de {sigla} gerada com sucesso!")
                st.download_button(
                    label=f"📥 BAIXAR SHIPPER {sigla}",
                    data=output,
                    file_name=f"Shipper_{sigla}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            else:
                st.error(f"Destino '{sigla}' não encontrado na coluna DESTINO da planilha.")
                
    except Exception as e:
        st.error(f"Erro ao processar: {e}")
