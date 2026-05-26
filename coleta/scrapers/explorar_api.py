import sys, os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

import pandas as pd
from scrapers.partidas_wiki_scraper import coletar_edicao, formatar_partidas

df_paises = pd.DataFrame([
    {'id_pais':  1, 'des_pais': 'France'},
    {'id_pais':  2, 'des_pais': 'Croatia'},
    {'id_pais':  3, 'des_pais': 'Belgium'},
    {'id_pais':  4, 'des_pais': 'England'},
    {'id_pais':  5, 'des_pais': 'Russia'},
    {'id_pais':  6, 'des_pais': 'Sweden'},
    {'id_pais':  7, 'des_pais': 'Brazil'},
    {'id_pais':  8, 'des_pais': 'Uruguay'},
    {'id_pais':  9, 'des_pais': 'Colombia'},
    {'id_pais': 10, 'des_pais': 'Japan'},
    {'id_pais': 11, 'des_pais': 'Mexico'},
    {'id_pais': 12, 'des_pais': 'Switzerland'},
    {'id_pais': 13, 'des_pais': 'Denmark'},
    {'id_pais': 14, 'des_pais': 'Spain'},
    {'id_pais': 15, 'des_pais': 'Portugal'},
    {'id_pais': 16, 'des_pais': 'Argentina'},
    {'id_pais': 17, 'des_pais': 'Germany'},
    {'id_pais': 18, 'des_pais': 'Peru'},
    {'id_pais': 19, 'des_pais': 'Poland'},
    {'id_pais': 20, 'des_pais': 'Senegal'},
    {'id_pais': 21, 'des_pais': 'Netherlands'},
    {'id_pais': 22, 'des_pais': 'Ecuador'},
    {'id_pais': 23, 'des_pais': 'Qatar'},
    {'id_pais': 24, 'des_pais': 'Morocco'},
    {'id_pais': 25, 'des_pais': 'Australia'},
    {'id_pais': 26, 'des_pais': 'South Korea'},
    {'id_pais': 27, 'des_pais': 'Tunisia'},
    {'id_pais': 28, 'des_pais': 'Ghana'},
    {'id_pais': 29, 'des_pais': 'Cameroon'},
    {'id_pais': 30, 'des_pais': 'Serbia'},
    {'id_pais': 31, 'des_pais': 'Poland'},
    {'id_pais': 32, 'des_pais': 'Costa Rica'},
    {'id_pais': 33, 'des_pais': 'Canada'},
    {'id_pais': 34, 'des_pais': 'Wales'},
    {'id_pais': 35, 'des_pais': 'Iran'},
    {'id_pais': 36, 'des_pais': 'Saudi Arabia'},
    {'id_pais': 37, 'des_pais': 'USA'},
])

dados_2022 = coletar_edicao(2022)
df_partidas = formatar_partidas(dados_2022, df_paises, id_partida_base=852)

# Identificar a partida sem id_time_owner
print('=== Partida com id_time_owner nulo ===')
nulos = df_partidas[df_partidas['id_time_owner'].isna()]
print(nulos[['ano_edicao','nome_time_owner','nome_time_away','fase_partida']].to_string())

# Ver todos os nomes únicos de países coletados
print('\n=== Todos os países coletados ===')
paises_coletados = set(df_partidas['nome_time_owner'].unique()) | set(df_partidas['nome_time_away'].unique())
paises_no_mapa   = set(df_paises['des_pais'].unique())
faltando         = paises_coletados - paises_no_mapa
print(f'Paises faltando no mapa: {faltando}')