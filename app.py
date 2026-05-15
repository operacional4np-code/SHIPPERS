import streamlit as st
import pandas as pd
from docxtpl import DocxTemplate
import io
from datetime import date

# 1. CONFIGURAÇÃO DA INTERFACE
st.set_page_config(page_title="Gerador New Post", layout="wide")
st.title(" 📄 Gerador de Shippers - New post logística")
st.markdown("Agora o sistema busca todas as informações (incluindo sacas) diretamente da planilha.")

# 2. MAPA DE TRADUÇÃO (Sigla -> Termo na Planilha)
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

# 3. ENTRADA ÚNICA: SIGLA
sigla_digitada = st.text_input("Digite a Sigla do Destino (Ex: CGB, POA, MAO):").upper().strip()

file = st.file_uploader("Upload da Planilha de Informações (.xlsm)", type=["xlsm", "xlsx"])

if file and sigla_digitada:
    try:
        # Carrega a planilha com suporte a macros
        df = pd.read_excel(file, header=None, engine='openpyxl')
        
        if st.button("GERAR SHIPPER"):
            # Traduz a sigla para o nome que está na planilha
            termo_busca = MAPA_DESTINOS.get(sigla_digitada, sigla_digitada)
            
            def localizar_linha(termo, dataframe):
                for index, row in dataframe.iterrows():
                    linha_texto = " ".join([str(val).upper() for val in row.values if pd.notnull(val)])
                    if termo in linha_texto:
                        return row
                return None

            dados = localizar_linha(termo_busca, df)

            if dados is not None:
                # --- EXTRAÇÃO AUTOMÁTICA PELAS COLUNAS ---
                # F = 5, I = 8, J = 9, K = 10 (Índices começam em 0)
                v_sacas      = dados[5]   # Coluna F
                v_fibreboard = dados[8]   # Coluna I
                v_kg_g       = dados[9]   # Coluna J
                v_total_ovp  = dados[10]  # Coluna K

                def formatar_valor(valor):
                    try:
                        return "{:.2f}".format(float(valor)).replace('.', ',')
                    except:
                        return str(valor).replace('.', ',')

                txt_kg_g = formatar_valor(v_kg_g)
                txt_total_k = formatar_valor(v_total_ovp)
                
                # Gera as etiquetas baseadas na Coluna F da planilha
                qtd_sacas_int = int(v_sacas) if pd.notnull(v_sacas) else 1
                marcacao = " ".join([f"#{i+1}" for i in range(qtd_sacas_int)])

                # 4. GERAÇÃO DO DOCUMENTO
                try:
                    doc = DocxTemplate(f"templates/{sigla_digitada}-SHIPPER-t.docx")
                    
                    contexto = {
                        'FIBREBOARD': int(v_fibreboard) if pd.notnull(v_fibreboard) else 0,
                        'PESO_G': txt_kg_g,
                        'TOTAL_OVERPACK': txt_total_k,
                        'MARCACAO': marcacao,
                        'DATA': date.today().strftime('%d/%m/%Y'),
                        'QTD_OVERPACK': qtd_sacas_int
                    }
                    
                    doc.render(contexto)
                    
                    output = io.BytesIO()
                    doc.save(output)
                    output.seek(0)
                    
                    st.success(f"✅ Sucesso! Destino: {termo_busca} | Sacas: {qtd_sacas_int}")
                    st.download_button(
                        label=f"📥 BAIXAR SHIPPER {sigla_digitada}",
                        data=output,
                        file_name=f"Shipper_{sigla_digitada}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"Erro ao localizar o template para {sigla_digitada}. Verifique a pasta 'templates'.")
            else:
                st.error(f"O termo '{termo_busca}' não foi encontrado em nenhuma linha da planilha.")
                
    except Exception as e:
        st.error(f"Erro ao processar a planilha: {e}")
