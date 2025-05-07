import streamlit as st
import pandas as pd
import json
import re
from bs4 import BeautifulSoup

# --- Leitura do JSON ---
json_path = "publicacoes_de_2025_05_06_1600_2359.json"
with open(json_path, encoding="utf-8") as f:
    data = json.load(f)

# Extrai os atos da primeira edição ordinária exclusiva
atos = data['edicoes_ordinarias_exclusivas'][0]['atos']
df = pd.DataFrame(atos)

# Função para limpar e converter HTML com segurança
def limpar_html_completo(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        texto_formatado = soup.decode(formatter="html")
        texto_formatado = texto_formatado.replace("\\n", "<br>")
        texto_formatado = re.sub(r'[\ud800-\udfff]', '', texto_formatado)  # remove surrogates inválidos
        return texto_formatado
    except Exception as e:
        return f"<p><b>Erro ao renderizar conteúdo:</b> {e}</p>"

df["html_formatado"] = df["texto"].apply(limpar_html_completo)

# --- Interface Streamlit ---
st.set_page_config(layout="wide")
st.title("Diário Oficial - Florianópolis")

with st.sidebar:
    st.markdown("### Filtros")
    palavra_chave = st.text_input("Buscar palavra-chave no título:")

    entidades = ["Todas"] + sorted(df["entidade"].dropna().unique().tolist())
    categorias = ["Todas"] + sorted(df["categoria"].dropna().unique().tolist())

    entidade = st.selectbox("Filtrar por Entidade:", entidades)
    categoria = st.selectbox("Filtrar por Categoria:", categorias)

# Aplica filtros
df_filtrado = df.copy()
if palavra_chave:
    df_filtrado = df_filtrado[df_filtrado["titulo"].str.contains(palavra_chave, case=False, na=False)]
if entidade != "Todas":
    df_filtrado = df_filtrado[df_filtrado["entidade"] == entidade]
if categoria != "Todas":
    df_filtrado = df_filtrado[df_filtrado["categoria"] == categoria]

# Verifica se há resultados
if df_filtrado.empty:
    st.warning("Nenhum resultado encontrado com os filtros aplicados.")
else:
    titulos = df_filtrado["titulo"].tolist()
    indice = st.selectbox("Escolha um Ato:", range(len(titulos)), format_func=lambda i: titulos[i])

    ato = df_filtrado.iloc[indice]
    st.subheader(ato["titulo"])
    st.markdown(f"**Categoria:** {ato['categoria']}  \n**Entidade:** {ato['entidade']}")
    st.markdown("---")
    st.markdown(ato["html_formatado"], unsafe_allow_html=True)

    link = ato["link"]
    st.markdown(f"[🔗 Acessar publicação original]({link})")