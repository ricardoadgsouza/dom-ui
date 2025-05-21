import os
import json
import re
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup

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

# --- Carregar edições válidas ---
@st.cache_data(hash_funcs={list: lambda x: tuple(sorted(x))})
def carregar_edicoes_validas(pasta="data"):
    arquivos = sorted(os.listdir(pasta))
    edicoes = {}
    for nome_arquivo in arquivos:
        if nome_arquivo.endswith(".json"):
            caminho = os.path.join(pasta, nome_arquivo)
            print(f"📄 Verificando: {nome_arquivo}")
            try:
                with open(caminho, encoding="utf-8") as f:
                    data = json.load(f)

                edicoes_ordinarias = data.get("edicoes_ordinarias_exclusivas")

                if not edicoes_ordinarias:
                    print("⛔ 'edicoes_ordinarias_exclusivas' ausente ou vazia.")
                    continue

                if isinstance(edicoes_ordinarias, list):
                    for i, item in enumerate(edicoes_ordinarias):
                        print(f"🔍 Item {i}: {type(item)}")
                        if isinstance(item, dict) and "atos" in item and item["atos"]:
                            match = re.search(r'(\d{4})_(\d{2})_(\d{2})_1600_2359', nome_arquivo)
                            if match:
                                data_str = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
                                edicoes[data_str] = item["atos"]
                                print(f"✅ Ato válido para {data_str}")
                            break
                        else:
                            print(f"⚠️ Item inválido ou sem atos.")
                else:
                    print("⚠️ edicoes_ordinarias_exclusivas não é lista.")
            except Exception as e:
                print(f"[!] Erro ao processar {nome_arquivo}: {e}")
    return edicoes

# --- Interface Streamlit ---
st.set_page_config(
    page_title="DOMSC UI",
    page_icon="📖",
    layout="wide")
st.title("Diário Oficial - Florianópolis")

edicoes = carregar_edicoes_validas()

if not edicoes:
    st.warning("⚠️ Nenhuma edição do DOM de Florianópolis disponível na pasta data.")
    st.stop()

with st.sidebar:
    st.markdown("### Filtros")
    palavra_chave = st.text_input("Buscar palavra-chave no título:")
    # Novo toggle para buscar no corpo do texto
    buscar_em_texto = st.sidebar.toggle("Incluir corpo do texto na busca?", value=True)
    datas_disponiveis = sorted(edicoes.keys(), reverse=True)
    data_selecionada = st.selectbox("Escolha a data da edição:", datas_disponiveis)
    buscar_todas = st.sidebar.toggle(
        "Buscar em todas as edições ",
        value=False,
        help="Ao ativar, a pesquisa pode demorar consideravelmente mais, pois serão carregados todos os atos disponíveis."
    )

if buscar_todas:
    todos_atos = []
    for lista_atos in reversed(edicoes.values()):
        todos_atos.extend(lista_atos)
    df = pd.DataFrame(todos_atos)
else:
    atos = edicoes[data_selecionada]
    df = pd.DataFrame(atos)

df["html_formatado"] = df["texto"].apply(limpar_html_completo)

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
    cond_titulo = df_filtrado["titulo"].apply(lambda x: contem_todos_os_termos(x, termos))
    if buscar_em_texto:
        cond_texto = df_filtrado["texto"].apply(lambda x: contem_todos_os_termos(x, termos))
        df_filtrado = df_filtrado[cond_titulo | cond_texto]
    else:
        df_filtrado = df_filtrado[cond_titulo]
if entidade != "Todas":
    df_filtrado = df_filtrado[df_filtrado["entidade"] == entidade]
if categoria != "Todas":
    df_filtrado = df_filtrado[df_filtrado["categoria"] == categoria]

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
    st.markdown(f"[🔗 Acessar publicação original]({ato['link']})")

with st.sidebar:
    st.markdown(
        "---\n"
        "<p style='font-size: 0.8em; color: gray; font-style: italic;'>⚠️ Este projeto não possui vínculo oficial com a Prefeitura de Florianópolis ou com o CIGA. "
        "É uma ferramenta experimental com fins informativos e de transparência.</p>",
        unsafe_allow_html=True
    )