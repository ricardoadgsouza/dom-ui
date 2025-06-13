import os
import json
import re
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from streamlit_pdf_viewer import pdf_viewer
import requests
import re


# --- Função para limpar HTML ---
def limpar_html_completo(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        texto_formatado = soup.decode(formatter="html")
        texto_formatado = texto_formatado.replace("\\n", "<br>")
        texto_formatado = re.sub(r'[\ud800-\udfff]', '', texto_formatado)
        return f'<div style="text-align: justify">{texto_formatado}</div>'

    except Exception as e:
        return f"<p><b>Erro ao renderizar conteúdo:</b> {e}</p>"
    
# --- Função para baixar o pdf, caso tenha ---

def get_pdf_if_exists(ato_id):
    url = f"https://www.diariomunicipal.sc.gov.br/atos/{ato_id}"
    response = requests.get(url, timeout=10)
    html = response.text

    match = re.search(r'https://www\.diariomunicipal\.sc\.gov\.br/arquivosbd/atos/[^"]+\.pdf', html)
    if match:
        pdf_url = match.group(0)
        pdf_response = requests.get(pdf_url, timeout=10)
        if pdf_response.status_code == 200 and pdf_response.headers["Content-Type"] == "application/pdf":
            return pdf_response.content, pdf_url
    return None, None


# --- Interface Streamlit ---
st.set_page_config(
    page_title="DOMSC UI",
    page_icon="📖",
    layout="wide")
st.title("Diário Oficial - Florianópolis")



# --- Função para carregar Parquet com cache ---
#@st.cache_data
def carregar_parquet():
    return pd.read_parquet("dados/atos.parquet")

try:
    df = carregar_parquet()
except Exception as e:
    st.warning(f"⚠️ Erro ao carregar o arquivo Parquet: {e}")
    st.stop()

with st.sidebar:
    st.markdown("### Filtros")
    palavra_chave = st.text_input("Buscar palavra-chave no título:")
    buscar_em_texto = st.sidebar.toggle("Incluir corpo do texto na busca?", value=False)
    datas_disponiveis = sorted(
        df["data_edicao"].dropna().unique().tolist(),
        key=lambda x: pd.to_datetime(x, dayfirst=True),
        reverse=True
    )
    data_selecionada = st.selectbox("Escolha a data da edição:", datas_disponiveis)
    buscar_todas = st.sidebar.toggle("Buscar em todas as edições", value=False)

if not buscar_todas:
    df = df[df["data_edicao"] == data_selecionada]

entidades = ["Todas"] + sorted(df["entidade"].dropna().unique().tolist())
categorias = ["Todas"] + sorted(df["categoria"].dropna().unique().tolist())

entidade = st.sidebar.selectbox("Filtrar por Entidade:", entidades)
categoria = st.sidebar.selectbox("Filtrar por Categoria:", categorias)

df_filtrado = df.copy()

def contem_todos_os_termos(texto, termos):
    texto_limpo = re.sub(r"[“”\".,:;!?()\[\]{}<>]", " ", texto.lower())
    return all(re.search(rf"\b{re.escape(t.lower())}\b", texto_limpo) for t in termos)

if palavra_chave:
    termos = palavra_chave.strip().split()
    cond_titulo = df_filtrado["titulo"].astype(str).apply(lambda x: contem_todos_os_termos(x, termos))
    if not buscar_em_texto:
        df_filtrado = df_filtrado[cond_titulo]
    else:
        cond_texto = df_filtrado["texto"].astype(str).apply(lambda x: contem_todos_os_termos(x, termos))
        df_filtrado = df_filtrado[cond_titulo | cond_texto]
if entidade != "Todas":
    df_filtrado = df_filtrado[df_filtrado["entidade"] == entidade]
if categoria != "Todas":
    df_filtrado = df_filtrado[df_filtrado["categoria"] == categoria]

# Ordenar os resultados filtrados do mais recente ao mais antigo
df_filtrado["data_edicao"] = pd.to_datetime(df_filtrado["data_edicao"], dayfirst=True, errors="coerce")
df_filtrado = df_filtrado.sort_values(by="data_edicao", ascending=False)

if df_filtrado.empty:
    st.warning("Nenhum resultado encontrado com os filtros aplicados.")
else:
    # Aplicar limpeza de HTML somente nos filtrados
    df_filtrado = df_filtrado.copy()
    df_filtrado["html_formatado"] = df_filtrado["texto"].apply(limpar_html_completo)
    titulos = df_filtrado["titulo"].tolist()
    opcoes = {f"{i+1}. {titulo}": i for i, titulo in enumerate(titulos)}
    escolha = st.selectbox("Escolha um Ato:", list(opcoes.keys()))
    indice = opcoes[escolha]
    ato = df_filtrado.iloc[indice]
    st.subheader(ato["titulo"])
    st.markdown(f"**Data:** {ato['data_edicao'].strftime('%d/%m/%Y')}  \n**Categoria:** {ato['categoria']}  \n**Entidade:** {ato['entidade']}")
    st.markdown("---")

    pdf_bytes, pdf_url = get_pdf_if_exists(ato["codigo"])  # usa a coluna "codigo"

    if pdf_bytes:
        st.success(f"PDF encontrado: [abrir PDF]({pdf_url})")
        pdf_viewer(input=pdf_bytes, width=10000, height=1000, annotations=[])
    else:
        st.markdown(ato["html_formatado"], unsafe_allow_html=True)
    
    st.markdown(f"[🔗 Acessar publicação original]({ato['link']})")

with st.sidebar:
    st.markdown(
        "---\n"
        "<p style='font-size: 0.8em; color: gray; font-style: italic;'>⚠️ Este projeto não possui vínculo oficial com a Prefeitura de Florianópolis ou com o CIGA. "
        "É uma ferramenta experimental com fins informativos e de transparência.</p>",
        unsafe_allow_html=True
    )

    #---<</file></file></file>