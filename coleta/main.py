import sys
import os

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
from loaders.bigquery_loader import upsert_tabela, validar_carga


def run():
    DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

    print('=== Lendo arquivos Kaggle ===')
    df_copas    = pd.read_csv(f'{DATA}/WorldCups.csv')
    df_part_raw = pd.read_csv(f'{DATA}/WorldCupMatches.csv')
    df_jog_raw  = pd.read_csv(f'{DATA}/WorldCupPlayers.csv')

    print('\n=== Processando dados ===')
    df_paises   = processar_paises(df_copas, df_part_raw)
    df_edicoes  = processar_edicoes(df_copas, df_paises)
    df_part     = processar_partidas(df_part_raw, df_paises)
    df_jog      = processar_jogadores(df_jog_raw, df_paises)
    df_jog_part = processar_jogadores_por_partida(df_jog_raw, df_paises, df_part)

    print('\n=== Carregando no BigQuery ===')
    upsert_tabela(df_paises,    'tb_paises')
    upsert_tabela(df_edicoes,   'edicao_copa')
    upsert_tabela(df_part,      'partidas')
    upsert_tabela(df_jog,       'jogadores')
    upsert_tabela(df_jog_part,  'jogadoresporjogos')

    print('\n=== Validando carga ===')
    validar_carga()
    print('\nPipeline Dia 02 concluido!')


if __name__ == '__main__':
    run()