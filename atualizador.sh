#!/bin/bash

# Executa o script Python
python3 atualizador.py

# Adiciona arquivos modificados em data/
git add data/*.json

git commit -m "Atualiza /data"

git status

git push


