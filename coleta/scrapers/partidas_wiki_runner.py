import sys
import os

BASE_DIR = os.path.dirname(
             os.path.dirname(
               os.path.dirname(
                 os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

import pandas as pd
from google.cloud import bigquery
from scrapers.partidas_wiki_scraper import (
    coletar_edicao,
    formatar_partidas,
    formatar_jogadores_por_jogo,
)

PROJECT     = os.getenv('GCP_PROJECT_ID')
DATASET_RAW = os.getenv('BQ_DATASET_RAW')
client      = bigquery.Client(project=PROJECT)


# ══════════════════════════════════════════════
# FUNÇÕES DE BUSCA NO BIGQUERY
# ══════════════════════════════════════════════
def buscar_paises_bq() -> pd.DataFrame:
    q = f'SELECT id_pais, des_pais FROM `{PROJECT}.{DATASET_RAW}.tb_paises`'
    df = client.query(q).to_dataframe()
    print(f'  {len(df)} paises encontrados')
    return df


def buscar_max_id_partida() -> int:
    q = f'SELECT MAX(id_partida) as max_id FROM `{PROJECT}.{DATASET_RAW}.partidas`'
    for row in client.query(q).result():
        return row.max_id or 0


def buscar_max_id_jogo() -> int:
    q = f'SELECT MAX(id_jogo) as max_id FROM `{PROJECT}.{DATASET_RAW}.jogadoresporjogos`'
    for row in client.query(q).result():
        return row.max_id or 0


def buscar_anos_existentes() -> list:
    q = f'SELECT DISTINCT ano_edicao FROM `{PROJECT}.{DATASET_RAW}.partidas`'
    return [row.ano_edicao for row in client.query(q).result()]


# ══════════════════════════════════════════════
# FUNÇÕES DE CARGA NO BIGQUERY
# ══════════════════════════════════════════════
def carregar_partidas(df: pd.DataFrame):
    """
    Usa WRITE_APPEND para adicionar as novas
    partidas sem apagar as 852 existentes.
    """
    table_id   = f'{PROJECT}.{DATASET_RAW}.partidas'
    job_config = bigquery.LoadJobConfig(
        write_disposition='WRITE_APPEND',
        schema=[
            bigquery.SchemaField('id_partida',                'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('ano_edicao',                'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('dt_partida',                'DATE',    mode='NULLABLE'),
            bigquery.SchemaField('id_time_owner',             'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('nome_time_owner',           'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('id_time_away',              'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('nome_time_away',            'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('fase_partida',              'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('id_vencedor',               'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('nome_vencedor',             'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('placar_time_owner',         'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('placar_time_away',          'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('gols_primeiro_tempo_owner', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('gols_primeiro_tempo_away',  'INTEGER', mode='NULLABLE'),
        ]
    )
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()
    print(f'  OK partidas: {len(df)} linhas adicionadas')


def carregar_jogadores_por_jogo(df: pd.DataFrame):
    """
    Usa WRITE_APPEND para adicionar gols
    sem apagar os 37784 registros existentes.
    """
    if df.empty:
        print('  Sem registros de gols para carregar')
        return

    table_id   = f'{PROJECT}.{DATASET_RAW}.jogadoresporjogos'
    job_config = bigquery.LoadJobConfig(
        write_disposition='WRITE_APPEND',
        schema=[
            bigquery.SchemaField('id_jogo',                    'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('id_jogador',                 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('id_partida',                 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('id_time',                    'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('nome_time',                  'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('nome_jogador',               'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('posicao_jogador',            'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('quantidade_gols',            'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('quantidade_cartao_amarelo',  'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('quantidade_cartao_vermelho', 'INTEGER', mode='NULLABLE'),
        ]
    )
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()
    print(f'  OK jogadoresporjogos: {len(df)} registros adicionados')


# ══════════════════════════════════════════════
# VALIDAÇÃO FINAL
# ══════════════════════════════════════════════
def validar_carga():
    print('\nValidacao:')

    # Total de partidas
    for row in client.query(
        f'SELECT COUNT(*) as total FROM `{PROJECT}.{DATASET_RAW}.partidas`'
    ).result():
        print(f'  partidas: {row.total} (esperado: 980)')

    # Partidas por edição
    for row in client.query(f'''
        SELECT ano_edicao, COUNT(*) as total
        FROM `{PROJECT}.{DATASET_RAW}.partidas`
        WHERE ano_edicao >= 2018
        GROUP BY ano_edicao
        ORDER BY ano_edicao
    ''').result():
        print(f'  {row.ano_edicao}: {row.total} partidas (esperado: 64)')

    # Total de gols registrados
    for row in client.query(f'''
        SELECT COUNT(*) as total,
               SUM(quantidade_gols) as gols
        FROM `{PROJECT}.{DATASET_RAW}.jogadoresporjogos`
    ''').result():
        print(f'  jogadoresporjogos: {row.total} registros')
        print(f'  Total gols: {row.gols}')

    # Conferir final de 2022
    print('\n  Final 2022:')
    for row in client.query(f'''
        SELECT nome_time_owner, nome_time_away,
               placar_time_owner, placar_time_away,
               nome_vencedor, fase_partida
        FROM `{PROJECT}.{DATASET_RAW}.partidas`
        WHERE ano_edicao = 2022
        AND fase_partida = 'FINAL'
    ''').result():
        print(f'  {row.nome_time_owner} {row.placar_time_owner} x '
              f'{row.placar_time_away} {row.nome_time_away} '
              f'| Vencedor: {row.nome_vencedor}')


# ══════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════
def run():
    print('=== Buscando dados do BigQuery ===')
    df_paises       = buscar_paises_bq()
    anos_existentes = buscar_anos_existentes()
    max_id_partida  = buscar_max_id_partida()
    max_id_jogo     = buscar_max_id_jogo()

    print(f'  Maior id_partida atual: {max_id_partida}')
    print(f'  Maior id_jogo atual:    {max_id_jogo}')

    # Filtra apenas edições que ainda não têm partidas
    edicoes_coletar = [
        ano for ano in [2018, 2022]
        if ano not in anos_existentes
    ]

    if not edicoes_coletar:
        print('\nPartidas de 2018 e 2022 ja existem no banco!')
        validar_carga()
        return

    print(f'\nEdicoes a coletar: {edicoes_coletar}')

    # Coleta dados de todas as edições necessárias
    print('\n=== Coletando Wikipedia ===')
    todos_dados = []
    for ano in edicoes_coletar:
        dados = coletar_edicao(ano)
        todos_dados.extend(dados)

    print(f'\nTotal coletado: {len(todos_dados)} partidas')

    # Formata partidas
    print('\n=== Formatando dados ===')
    df_partidas = formatar_partidas(
        todos_dados, df_paises,
        id_partida_base=max_id_partida
    )
    print(f'  Partidas formatadas: {len(df_partidas)}')

    # Formata gols por jogador
    df_jog_jogo = formatar_jogadores_por_jogo(
        todos_dados, df_paises,
        df_partidas, max_id_jogo
    )
    print(f'  Registros de gols: {len(df_jog_jogo)}')
    print(f'  Total gols: {df_jog_jogo["quantidade_gols"].sum()}')

    # Carrega no BigQuery
    print('\n=== Carregando no BigQuery ===')
    carregar_partidas(df_partidas)
    carregar_jogadores_por_jogo(df_jog_jogo)

    # Valida
    print('\n=== Validando ===')
    validar_carga()

    print('\nDia 04 concluido!')


if __name__ == '__main__':
    run()