import requests
import zipfile
import io
import os
import json

def baixar_e_extrair_json_com_nome(zip_url, pasta_destino="data"):
    nome_zip = os.path.basename(zip_url)
    nome_json = nome_zip.replace(".zip", ".json")
    caminho_json = os.path.join(pasta_destino, nome_json)

    print(f"🔽 Baixando: {zip_url}")
    response = requests.get(zip_url)
    response.raise_for_status()

    print("📦 Extraindo JSON...")
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        nome_arquivo_json = [name for name in z.namelist() if name.endswith(".json")][0]
        with z.open(nome_arquivo_json) as f:
            conteudo = json.load(f)

    print(f"💾 Salvando JSON em: {caminho_json}")
    os.makedirs(pasta_destino, exist_ok=True)
    with open(caminho_json, "w", encoding="utf-8") as f_out:
        json.dump(conteudo, f_out, ensure_ascii=False, indent=2)

    print("✅ Finalizado.")

# Exemplo de uso único
if __name__ == "__main__":
    url = "https://dados.ciga.sc.gov.br/dataset/6fb88011-fc0b-4d0d-bceb-ab59a3811bce/resource/ed0c462e-8c00-47f5-8e4f-6fc4ecb07fd6/download/cigadados_publicacoes_2025_05_06_1600_2359.zip"
    baixar_e_extrair_json_com_nome(url)