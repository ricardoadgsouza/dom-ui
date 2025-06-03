import os
import json
import re
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
import tempfile
from docling.document_converter import DocumentConverter

# --- Função para limpar HTML ---
def limpar_html_completo(html):
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as tmp_file:
            tmp_file.write(html)
            temp_path = tmp_file.name
        converter = DocumentConverter()
        result = converter.convert(temp_path)
        return result.document.export_to_markdown()
    except Exception as e:
        return f"**Erro ao converter conteúdo:** {e}"

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
    st.markdown(ato["html_formatado"], unsafe_allow_html=False)
    st.markdown(f"[🔗 Acessar publicação original]({ato['link']})")

with st.sidebar:
    st.markdown(
        "---\n"
        "<p style='font-size: 0.8em; color: gray; font-style: italic;'>⚠️ Este projeto não possui vínculo oficial com a Prefeitura de Florianópolis ou com o CIGA. "
        "É uma ferramenta experimental com fins informativos e de transparência.</p>",
        unsafe_allow_html=True
    )