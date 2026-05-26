import sys
import os

# Garante que o .env da raiz seja carregado corretamente
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

import pandas as pd
from scrapers.kaggle_processor import (
    processar_paises,
    processar_edicoes,
    processar_partidas,
    processar_jogadores,
    processar_jogadores_por_partida,
)

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

print('=== Lendo arquivos ===')
df_copas    = pd.read_csv(f'{DATA}/WorldCups.csv')
df_part_raw = pd.read_csv(f'{DATA}/WorldCupMatches.csv')
df_jog_raw  = pd.read_csv(f'{DATA}/WorldCupPlayers.csv')

print('\n=== Processando ===')
df_paises   = processar_paises(df_copas, df_part_raw)
df_edicoes  = processar_edicoes(df_copas, df_paises)
df_part     = processar_partidas(df_part_raw, df_paises)
df_jog      = processar_jogadores(df_jog_raw, df_paises)
df_jog_part = processar_jogadores_por_partida(df_jog_raw, df_paises, df_part)

print('\n=== Amostra tb_paises ===')
print(df_paises.head(3))

print('\n=== Amostra edicao_copa ===')
print(df_edicoes.head(3))

print('\n=== Amostra partidas ===')
print(df_part.head(3))

print('\n=== Amostra jogadores ===')
print(df_jog.head(3))

print('\n=== Amostra jogadoresporjogos ===')
print(df_jog_part.head(3))

print('\n=== Validacoes ===')
brasil_id  = df_paises[df_paises['des_pais'] == 'Brazil']['id_pais'].values[0]
print(f'ID do Brasil: {brasil_id}')

camp_1970  = df_edicoes[df_edicoes['ano_edicao'] == 1970]['id_vencedor'].values[0]
print(f'Campeao 1970 (deve ser {brasil_id}): {camp_1970}')

camp_2002  = df_edicoes[df_edicoes['ano_edicao'] == 2002]['id_vencedor'].values[0]
print(f'Campeao 2002 (deve ser {brasil_id}): {camp_2002}')

nulos_data = df_part['dt_partida'].isna().sum()
print(f'Datas nulas: {nulos_data} (esperado: 0)')

total_gols = df_jog_part['quantidade_gols'].sum()
print(f'Total de gols: {total_gols}')

ids_dim    = set(df_jog['id_jogador'].unique())
ids_fato   = set(df_jog_part['id_jogador'].unique())
sem_dim    = ids_fato - ids_dim
print(f'IDs sem correspondencia: {len(sem_dim)} (esperado: 0)')

print('\nTeste concluido!')