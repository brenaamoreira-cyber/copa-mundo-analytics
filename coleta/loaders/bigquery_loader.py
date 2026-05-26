from google.cloud import bigquery
import pandas as pd
import os
from dotenv import load_dotenv

# Sobe dois níveis a partir de loaders/ para encontrar o .env na raiz
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Remove BOM se existir (problema comum no Windows)
env_path = os.path.join(BASE_DIR, '.env')
with open(env_path, 'rb') as f:
    content = f.read()
if content.startswith(b'\xef\xbb\xbf'):
    content = content[3:]
    with open(env_path, 'wb') as f:
        f.write(content)
load_dotenv(env_path, override=True)

PROJECT     = os.getenv('GCP_PROJECT_ID')
DATASET_RAW = os.getenv('BQ_DATASET_RAW')

print(f"Projeto:     {PROJECT}")
print(f"Dataset RAW: {DATASET_RAW}")

client = bigquery.Client(project=PROJECT)

# ─────────────────────────────────────────────
# SCHEMAS — define o tipo de cada coluna.
# Sem isso o BigQuery tenta adivinhar e erra.
# ─────────────────────────────────────────────
SCHEMAS = {
    'tb_paises': [
        bigquery.SchemaField('id_pais',        'INTEGER', mode='REQUIRED'),
        bigquery.SchemaField('des_pais',        'STRING'),
        bigquery.SchemaField('des_continente',  'STRING'),
        bigquery.SchemaField('img_bandeira',    'STRING'),
    ],
    'edicao_copa': [
        bigquery.SchemaField('id_edicao',           'INTEGER', mode='REQUIRED'),
        bigquery.SchemaField('ano_edicao',           'INTEGER'),
        bigquery.SchemaField('id_vencedor',          'INTEGER'),
        bigquery.SchemaField('nome_vencedor',        'STRING'),
        bigquery.SchemaField('id_vice',              'INTEGER'),
        bigquery.SchemaField('nome_vice',            'STRING'),
        bigquery.SchemaField('id_terceiro_lugar',    'INTEGER'),
        bigquery.SchemaField('nome_terceiro_lugar',  'STRING'),
        bigquery.SchemaField('id_pais_sede',         'INTEGER'),
        bigquery.SchemaField('nome_pais_sede',       'STRING'),
    ],
    'partidas': [
        bigquery.SchemaField('id_partida',                'INTEGER', mode='REQUIRED'),
        bigquery.SchemaField('ano_edicao',                'INTEGER'),
        bigquery.SchemaField('dt_partida',                'DATE'),
        bigquery.SchemaField('id_time_owner',             'INTEGER'),
        bigquery.SchemaField('nome_time_owner',           'STRING'),
        bigquery.SchemaField('id_time_away',              'INTEGER'),
        bigquery.SchemaField('nome_time_away',            'STRING'),
        bigquery.SchemaField('fase_partida',              'STRING'),
        bigquery.SchemaField('id_vencedor',               'INTEGER'),
        bigquery.SchemaField('nome_vencedor',             'STRING'),
        bigquery.SchemaField('placar_time_owner',         'INTEGER'),
        bigquery.SchemaField('placar_time_away',          'INTEGER'),
        bigquery.SchemaField('gols_primeiro_tempo_owner', 'INTEGER'),
        bigquery.SchemaField('gols_primeiro_tempo_away',  'INTEGER'),
    ],
    'jogadores': [
        bigquery.SchemaField('id_jogador',      'INTEGER', mode='REQUIRED'),
        bigquery.SchemaField('nome_jogador',    'STRING'),
        bigquery.SchemaField('posicao_jogador', 'STRING'),
        bigquery.SchemaField('id_pais',         'INTEGER'),
        bigquery.SchemaField('nome_pais',       'STRING'),
    ],
    'jogadoresporjogos': [
        bigquery.SchemaField('id_jogo',                    'INTEGER', mode='REQUIRED'),
        bigquery.SchemaField('id_jogador',                 'INTEGER'),
        bigquery.SchemaField('id_partida',                 'INTEGER'),
        bigquery.SchemaField('id_time',                    'INTEGER'),
        bigquery.SchemaField('nome_time',                  'STRING'),
        bigquery.SchemaField('nome_jogador',               'STRING'),
        bigquery.SchemaField('posicao_jogador',            'STRING'),
        bigquery.SchemaField('quantidade_gols',            'INTEGER'),
        bigquery.SchemaField('quantidade_cartao_amarelo',  'INTEGER'),
        bigquery.SchemaField('quantidade_cartao_vermelho', 'INTEGER'),
    ],
}


def upsert_tabela(df: pd.DataFrame, tabela: str):
    """
    Carrega um DataFrame no BigQuery.
    WRITE_TRUNCATE = apaga tudo e reescreve.
    Pode rodar quantas vezes quiser sem duplicar.
    """
    table_id   = f'{PROJECT}.{DATASET_RAW}.{tabela}'
    job_config = bigquery.LoadJobConfig(
        schema=SCHEMAS[tabela],
        write_disposition='WRITE_TRUNCATE',
    )
    job = client.load_table_from_dataframe(
        df, table_id, job_config=job_config
    )
    job.result()
    tabela_bq = client.get_table(table_id)
    print(f'OK {tabela}: {tabela_bq.num_rows} linhas')


def validar_carga():
    """Verifica quantas linhas cada tabela tem no BigQuery"""
    print('\nValidacao das tabelas:')
    for tabela in SCHEMAS.keys():
        query  = f'SELECT COUNT(*) as total FROM `{PROJECT}.{DATASET_RAW}.{tabela}`'
        result = client.query(query).result()
        for row in result:
            print(f'  {tabela}: {row.total} linhas')