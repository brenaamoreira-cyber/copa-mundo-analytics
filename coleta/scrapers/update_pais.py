import os
import sys

# ─────────────────────────────────────────────
# CORRIGIR CAMINHO DO .env
# O arquivo está em coleta/scrapers/
# O .env está na raiz do projeto
# Precisamos subir 3 níveis:
# scrapers/ -> coleta/ -> project-world-cup/
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(                    # project-world-cup/
             os.path.dirname(                  # coleta/
               os.path.dirname(                # scrapers/
                 os.path.abspath(__file__))))  # update_pais.py

sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

from google.cloud import bigquery
import pandas as pd

PROJECT     = os.getenv('GCP_PROJECT_ID')
DATASET_RAW = os.getenv('BQ_DATASET_RAW')

# Confirma que carregou
print(f'Projeto:     {PROJECT}')
print(f'Dataset RAW: {DATASET_RAW}')

if not PROJECT:
    raise ValueError("GCP_PROJECT_ID nao encontrado — verifique o .env")

client = bigquery.Client(project=PROJECT)

# ─────────────────────────────────────────────
# MAPA DE PAÍSES
# Adicione novos países aqui quando necessário
# ─────────────────────────────────────────────
ISO2_MAP = {
    'Qatar':   'qa', 'Canada':  'ca',
    'Wales':   'gb-wls', 'Iceland': 'is',
    'Panama':  'pa', 'Egypt':   'eg',
    'Peru':    'pe',
}

CONTINENTE_MAP = {
    'Qatar':   'Asia',
    'Canada':  'North America',
    'Wales':   'Europe',
    'Iceland': 'Europe',
    'Panama':  'North America',
    'Egypt':   'Africa',
    'Peru':    'South America',
}


def buscar_max_id() -> int:
    """Busca o maior id_pais atual para continuar a sequência"""
    query  = f'SELECT MAX(id_pais) as max_id FROM `{PROJECT}.{DATASET_RAW}.tb_paises`'
    result = client.query(query).result()
    for row in result:
        return row.max_id or 0


def verificar_paises_existentes() -> set:
    """Retorna conjunto com todos os países já cadastrados"""
    query  = f'SELECT des_pais FROM `{PROJECT}.{DATASET_RAW}.tb_paises`'
    result = client.query(query).result()
    return {row.des_pais for row in result}


def inserir_paises(paises: list):
    """
    Insere apenas países que ainda não existem na tb_paises.
    Evita duplicatas verificando antes de inserir.
    """
    existentes = verificar_paises_existentes()
    print(f'Paises ja existentes: {len(existentes)}')

    # Filtra só os que realmente precisam ser inseridos
    novos = [p for p in paises if p['des_pais'] not in existentes]

    if not novos:
        print('Todos os paises ja existem na tb_paises!')
        return

    print(f'Paises a inserir: {[p["des_pais"] for p in novos]}')

    max_id = buscar_max_id()
    print(f'Maior id_pais atual: {max_id}')

    rows = []
    for i, p in enumerate(novos, start=1):
        id_pais = max_id + i
        rows.append({
            'id_pais':        id_pais,
            'des_pais':       p['des_pais'],
            'des_continente': CONTINENTE_MAP.get(p['des_pais'], ''),
            'img_bandeira':   f"https://flagcdn.com/w80/{ISO2_MAP.get(p['des_pais'], 'un')}.png",
        })
        print(f'  Preparando: {p["des_pais"]} (id_pais={id_pais})')

    df = pd.DataFrame(rows)

    table_id   = f'{PROJECT}.{DATASET_RAW}.tb_paises'
    job_config = bigquery.LoadJobConfig(
        write_disposition='WRITE_APPEND',
        schema=[
            bigquery.SchemaField('id_pais',        'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('des_pais',        'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('des_continente',  'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('img_bandeira',    'STRING',  mode='NULLABLE'),
        ]
    )

    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()
    print(f'\nOK: {len(df)} paises inseridos!')
    print(df.to_string())


def atualizar_id_pais_sede(ano: int, nome_pais_sede: str):
    """
    Atualiza o id_pais_sede na edicao_copa
    após inserir o país na tb_paises.
    """
    # Busca o ID do país recém inserido
    query_id = f"""
        SELECT id_pais
        FROM `{PROJECT}.{DATASET_RAW}.tb_paises`
        WHERE des_pais = '{nome_pais_sede}'
        LIMIT 1
    """
    id_pais = None
    for row in client.query(query_id).result():
        id_pais = row.id_pais

    if not id_pais:
        print(f'ERRO: {nome_pais_sede} nao encontrado na tb_paises')
        return

    # Atualiza o id_pais_sede na edicao_copa
    query_update = f"""
        UPDATE `{PROJECT}.{DATASET_RAW}.edicao_copa`
        SET id_pais_sede = {id_pais}
        WHERE ano_edicao = {ano}
    """
    client.query(query_update).result()
    print(f'OK: id_pais_sede da Copa {ano} atualizado para {id_pais} ({nome_pais_sede})')


def validar():
    """Valida o resultado final com JOIN entre as tabelas"""
    print('\n=== Validacao ===')

    # Total de países
    for row in client.query(
        f'SELECT COUNT(*) as total FROM `{PROJECT}.{DATASET_RAW}.tb_paises`'
    ).result():
        print(f'tb_paises: {row.total} paises')

    # Edições com JOIN confirmando sede
    query = f"""
        SELECT e.ano_edicao, e.nome_pais_sede,
               e.id_pais_sede, p.des_pais as sede_confirmada
        FROM `{PROJECT}.{DATASET_RAW}.edicao_copa` e
        LEFT JOIN `{PROJECT}.{DATASET_RAW}.tb_paises` p
               ON e.id_pais_sede = p.id_pais
        WHERE e.ano_edicao >= 2018
        ORDER BY e.ano_edicao
    """
    print('\nEdicoes 2018 e 2022:')
    for row in client.query(query).result():
        print(f'  {row.ano_edicao} | '
              f'Sede: {row.nome_pais_sede} | '
              f'id_sede: {row.id_pais_sede} | '
              f'Confirmado: {row.sede_confirmada}')


if __name__ == '__main__':

    # Passo 1 — Inserir países faltando
    print('=== Inserindo paises ===')
    paises_novos = [
        {'des_pais': 'Qatar'},
        {'des_pais': 'Canada'},
        {'des_pais': 'Wales'},
    ]
    inserir_paises(paises_novos)

    # Passo 2 — Corrigir id_pais_sede da Copa 2022
    print('\n=== Corrigindo Copa 2022 ===')
    atualizar_id_pais_sede(2022, 'Qatar')

    # Passo 3 — Validar
    validar()