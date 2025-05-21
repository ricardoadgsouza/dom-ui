import requests
from bs4 import BeautifulSoup
import re
import os
import zipfile
import io
import json

# Configuração
url_base = "https://dados.ciga.sc.gov.br/dataset/domsc-publicacoes-de-05-2025"
site_prefix = "https://dados.ciga.sc.gov.br"
pasta_saida = "data"
os.makedirs(pasta_saida, exist_ok=True)

# Pega o HTML da página principal do mês
resp = requests.get(url_base)
soup = BeautifulSoup(resp.text, "html.parser")

# Coleta links para as subpáginas de recurso
padrao_pagina = re.compile(r'^/dataset/.+/resource/[\w-]+$')
paginas_recursos = sorted(
    set(site_prefix + l['href'] for l in soup.find_all("a", href=True) if padrao_pagina.match(l['href'])),
    reverse=True
)

# Função para extrair link .zip com padrão 1600_2359
def encontrar_link_zip(pagina_recurso):
    try:
        resp = requests.get(pagina_recurso)
        soup = BeautifulSoup(resp.text, "html.parser")
        link_zip = soup.find("a", href=True, text=re.compile(r'cigadados_publicacoes_\d{4}_\d{2}_\d{2}_1600_2359\.zip$'))
        if link_zip:
            href = link_zip["href"]
            return href if href.startswith("http") else site_prefix + href
    except Exception as e:
        print(f"[!] Erro ao acessar {pagina_recurso}: {e}")
    return None

# Armazena os links válidos
links_validos = list(set(filter(None, [encontrar_link_zip(p) for p in paginas_recursos])))

# Baixa e extrai JSON de todos os arquivos encontrados
for link_final in links_validos:
    print(f"\n🔗 Baixando: {link_final}")
    nome_arquivo_zip = os.path.basename(link_final)
    nome_arquivo_json = nome_arquivo_zip.replace(".zip", ".json")
    caminho_json = os.path.join(pasta_saida, nome_arquivo_json)

    if os.path.exists(caminho_json):
        print(f"✅ Já existe: {nome_arquivo_json}")
        continue

    try:
        r = requests.get(link_final)
        r.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            nome_interno_json = [f for f in z.namelist() if f.endswith(".json")][0]
            with z.open(nome_interno_json) as f:
                conteudo = json.load(f)

        with open(caminho_json, "w", encoding="utf-8") as f_out:
            json.dump(conteudo, f_out, ensure_ascii=False, indent=2)

        print(f"💾 Extraído e salvo como: {caminho_json}")
        print(f"🗑️ Arquivo .zip descartado (não salvo em disco)")

    except Exception as e:
        print(f"[!] Falha ao processar {link_final}: {e}")

# Geração de arquivo Parquet otimizado (apenas Florianópolis e atos válidos)
print("\n📦 Gerando arquivo Parquet...")

try:
    import pandas as pd
    records = []

    for nome in os.listdir("data"):
        if nome.endswith(".json"):
            caminho = os.path.join("data", nome)
            with open(caminho, encoding="utf-8") as f:
                dados = json.load(f)

            for ed in dados.get("edicoes_ordinarias_exclusivas", []):
                if not isinstance(ed, dict):
                    continue
                if ed.get("municipio") != "Florianópolis":
                    continue
                for ato in ed.get("atos", []):
                    rec = ato.copy()
                    rec["data_edicao"] = ed.get("data")
                    rec["url_edicao"] = ed.get("url")
                    records.append(rec)

    df = pd.DataFrame(records)
    os.makedirs("dados", exist_ok=True)
    df.to_parquet("dados/atos.parquet", index=False)
    print(f"✅ Parquet salvo com {len(df)} registros.")
except Exception as e:
    print(f"[!] Erro ao gerar Parquet: {e}")