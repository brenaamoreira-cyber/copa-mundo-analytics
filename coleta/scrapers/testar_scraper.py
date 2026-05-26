import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

import pandas as pd
from scrapers.wikipedia_scraper import coletar_edicao, processar_edicoes_wiki

# ── Simular df_paises sem precisar do BigQuery ──
# Cria um DataFrame mínimo só para testar o mapa de IDs
df_paises_teste = pd.DataFrame([
    {'id_pais': 1,  'des_pais': 'Argentina'},
    {'id_pais': 2,  'des_pais': 'France'},
    {'id_pais': 3,  'des_pais': 'Croatia'},
    {'id_pais': 4,  'des_pais': 'Morocco'},
    {'id_pais': 5,  'des_pais': 'Qatar'},
    {'id_pais': 6,  'des_pais': 'Russia'},
    {'id_pais': 7,  'des_pais': 'Belgium'},
    {'id_pais': 8,  'des_pais': 'England'},
    {'id_pais': 9,  'des_pais': 'Uruguay'},
    {'id_pais': 10, 'des_pais': 'Sweden'},
])

print('=== Coletando 2018 e 2022 ===')
dados_wiki = []
for ano in [2018, 2022]:
    resultado = coletar_edicao(ano)
    if resultado['edicao']:
        dados_wiki.append(resultado['edicao'])

print('\n=== Dados brutos coletados ===')
for d in dados_wiki:
    print(d)

print('\n=== Processando edicoes ===')
df = processar_edicoes_wiki(dados_wiki, df_paises_teste)
print(df.to_string())

print('\n=== Validacoes ===')
print(f'2018 campeao: {df[df["ano_edicao"]==2018]["nome_vencedor"].values}')
print(f'2022 campeao: {df[df["ano_edicao"]==2022]["nome_vencedor"].values}')
print(f'2018 sede:    {df[df["ano_edicao"]==2018]["nome_pais_sede"].values}')
print(f'2022 sede:    {df[df["ano_edicao"]==2022]["nome_pais_sede"].values}')