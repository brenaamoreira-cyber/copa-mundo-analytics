import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

import pandas as pd
from google.cloud import bigquery
from scrapers.wikipedia_scraper import (
    coletar_edicao,
    processar_edicoes_wiki,
)

PROJECT     = os.getenv('GCP_PROJECT_ID')
DATASET_RAW = os.getenv('BQ_DATASET_RAW')
client      = bigquery.Client(project=PROJECT)

# ─────────────────────────────────────────────
# MAPA DE ISO2 PARA BANDEIRAS
# Adicione novos países aqui conforme necessário
# ─────────────────────────────────────────────
ISO2_MAP = {
    'Qatar':           'qa', 'Canada':       'ca',
    'Wales':           'gb-wls', 'Iceland':  'is',
    'Panama':          'pa', 'Egypt':        'eg',
    'Peru':            'pe', 'Argentina':    'ar',
    'France':          'fr', 'Croatia':      'hr',
    'Morocco':         'ma', 'Brazil':       'br',
    'Germany':         'de', 'Spain':        'es',
    'England':         'gb-eng', 'Belgium':  'be',
    'Portugal':        'pt', 'Uruguay':      'uy',
    'Switzerland':     'ch', 'South Korea':  'kr',
    'Japan':           'jp', 'Australia':    'au',
    'Netherlands':     'nl', 'Senegal':      'sn',
    'Poland':          'pl', 'Denmark':      'dk',
    'Tunisia':         'tn', 'Mexico':       'mx',
    'USA':             'us', 'Saudi Arabia': 'sa',
    'Iran':            'ir', 'Ecuador':      'ec',
    'Ghana':           'gh', 'Cameroon':     'cm',
    'Costa Rica':      'cr', 'Serbia':       'rs',
    'Russia':          'ru', 'Sweden':       'se',
    'Colombia':        'co', 'Nigeria':      'ng',
    'Algeria':         'dz', 'Greece':       'gr',
    'Slovenia':        'si', 'Slovakia':     'sk',
    'Ukraine':         'ua', 'Trinidad and Tobago': 'tt',
    'New Zealand':     'nz', 'El Salvador':  'sv',
    'Haiti':           'ht', 'Israel':       'il',
    'Kuwait':          'kw', 'Angola':       'ao',
    'Ivory Coast':     'ci', 'Togo':         'tg',
    'Bosnia':          'ba', 'Honduras':     'hn',
    'Bulgaria':        'bg',
}

# ─────────────────────────────────────────────
# MAPA DE CONTINENTES
# Para preencher des_continente automaticamente
# ─────────────────────────────────────────────
CONTINENTE_MAP = {
    'Qatar':        'Asia',           'Saudi Arabia':  'Asia',
    'Iran':         'Asia',           'Japan':         'Asia',
    'South Korea':  'Asia',           'Australia':     'Oceania',
    'Canada':       'North America',  'USA':           'North America',
    'Mexico':       'North America',  'Costa Rica':    'North America',
    'Honduras':     'North America',  'El Salvador':   'North America',
    'Haiti':        'North America',  'Trinidad and Tobago': 'North America',
    'Panama':       'North America',  'Ecuador':       'South America',
    'Brazil':       'South America',  'Argentina':     'South America',
    'Uruguay':      'South America',  'Colombia':      'South America',
    'Peru':         'South America',  'Chile':         'South America',
    'Bolivia':      'South America',  'Paraguay':      'South America',
    'France':       'Europe',         'Germany':       'Europe',
    'Spain':        'Europe',         'England':       'Europe',
    'Portugal':     'Europe',         'Netherlands':   'Europe',
    'Belgium':      'Europe',         'Croatia':       'Europe',
    'Switzerland':  'Europe',         'Denmark':       'Europe',
    'Poland':       'Europe',         'Serbia':        'Europe',
    'Wales':        'Europe',         'Sweden':        'Europe',
    'Russia':       'Europe',         'Greece':        'Europe',
    'Slovenia':     'Europe',         'Slovakia':      'Europe',
    'Ukraine':      'Europe',         'Bulgaria':      'Europe',
    'Iceland':      'Europe',         'Bosnia':        'Europe',
    'Senegal':      'Africa',         'Morocco':       'Africa',
    'Cameroon':     'Africa',         'Ghana':         'Africa',
    'Nigeria':      'Africa',         'Tunisia':       'Africa',
    'Algeria':      'Africa',         'Ivory Coast':   'Africa',
    'Togo':         'Africa',         'Angola':        'Africa',
    'Egypt':        'Africa',         'South Africa':  'Africa',
    'New Zealand':  'Oceania',        'Australia':     'Oceania',
    'Israel':       'Asia',           'Kuwait':        'Asia',
}


# ══════════════════════════════════════════════
# FUNÇÃO 1 — buscar_paises_bq()
# ══════════════════════════════════════════════
def buscar_paises_bq() -> pd.DataFrame:
    query = f'SELECT id_pais, des_pais FROM `{PROJECT}.{DATASET_RAW}.tb_paises`'
    df    = client.query(query).to_dataframe()
    print(f'  {len(df)} paises encontrados no BigQuery')
    return df


# ══════════════════════════════════════════════
# FUNÇÃO 2 — garantir_paises()
#
# Verifica se todos os países dos dados
# existem na tb_paises. Se não existirem,
# adiciona automaticamente antes de qualquer
# outra carga — evitando NaN nos IDs.
# ══════════════════════════════════════════════
def garantir_paises(nomes: list, df_paises: pd.DataFrame) -> pd.DataFrame:
    # Remove None e vazios da lista
    nomes_validos = [p for p in nomes if p and str(p).strip()]

    # Países que já existem no banco
    paises_existentes = set(df_paises['des_pais'].dropna().unique())

    # Filtra só os que não existem
    novos = [p for p in nomes_validos if p not in paises_existentes]

    if not novos:
        print('  Todos os paises ja existem na tb_paises')
        return df_paises

    print(f'  Novos paises encontrados: {novos}')

    # Continua a sequência de IDs
    max_id = int(df_paises['id_pais'].max())

    rows_novos = []
    for i, pais in enumerate(novos, start=1):
        id_novo = max_id + i
        rows_novos.append({
            'id_pais':        id_novo,
            'des_pais':       pais,
            'des_continente': CONTINENTE_MAP.get(pais, ''),
            'img_bandeira':   f"https://flagcdn.com/w80/{ISO2_MAP.get(pais, 'un')}.png",
        })
        print(f'  Adicionando: {pais} (id_pais={id_novo})')

    df_novos = pd.DataFrame(rows_novos)

    # Carrega no BigQuery
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
    job = client.load_table_from_dataframe(df_novos, table_id, job_config=job_config)
    job.result()
    print(f'  OK: {len(df_novos)} novos paises adicionados!')

    # Retorna df_paises atualizado com os novos países
    # para que o restante do pipeline use os IDs corretos
    return pd.concat([df_paises, df_novos], ignore_index=True)


# ══════════════════════════════════════════════
# FUNÇÃO 3 — verificar_edicoes_existentes()
# ══════════════════════════════════════════════
def verificar_edicoes_existentes() -> list:
    query  = f'SELECT ano_edicao FROM `{PROJECT}.{DATASET_RAW}.edicao_copa`'
    result = client.query(query).result()
    anos   = [row.ano_edicao for row in result]
    print(f'  Edicoes ja existentes: {sorted(anos)}')
    return anos


# ══════════════════════════════════════════════
# FUNÇÃO 4 — append_edicoes()
# ══════════════════════════════════════════════
def append_edicoes(df: pd.DataFrame):
    table_id   = f'{PROJECT}.{DATASET_RAW}.edicao_copa'
    job_config = bigquery.LoadJobConfig(
        write_disposition='WRITE_APPEND',
        schema=[
            bigquery.SchemaField('id_edicao',           'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('ano_edicao',           'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('id_vencedor',          'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('nome_vencedor',        'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('id_vice',              'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('nome_vice',            'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('id_terceiro_lugar',    'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('nome_terceiro_lugar',  'STRING',  mode='NULLABLE'),
            bigquery.SchemaField('id_pais_sede',         'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('nome_pais_sede',       'STRING',  mode='NULLABLE'),
        ]
    )
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()
    print(f'OK edicao_copa: {len(df)} edicoes adicionadas')


# ══════════════════════════════════════════════
# FUNÇÃO 5 — validar_carga()
# ══════════════════════════════════════════════
def validar_carga():
    print('\nValidacao:')

    # Total de países
    for row in client.query(
        f'SELECT COUNT(*) as total FROM `{PROJECT}.{DATASET_RAW}.tb_paises`'
    ).result():
        print(f'  tb_paises:   {row.total} paises')

    # Total de edições
    for row in client.query(
        f'SELECT COUNT(*) as total FROM `{PROJECT}.{DATASET_RAW}.edicao_copa`'
    ).result():
        print(f'  edicao_copa: {row.total} edicoes (esperado: 22)')

    # Detalhes das novas edições
    query = f"""
        SELECT e.ano_edicao, e.nome_vencedor, e.nome_vice,
               e.nome_terceiro_lugar, e.nome_pais_sede,
               e.id_pais_sede, p.des_pais as pais_sede_confirmado
        FROM `{PROJECT}.{DATASET_RAW}.edicao_copa` e
        LEFT JOIN `{PROJECT}.{DATASET_RAW}.tb_paises` p
               ON e.id_pais_sede = p.id_pais
        WHERE e.ano_edicao >= 2018
        ORDER BY e.ano_edicao
    """
    print('\n  Novas edicoes:')
    for row in client.query(query).result():
        print(f'  {row.ano_edicao} | '
              f'Campeao: {row.nome_vencedor} | '
              f'Vice: {row.nome_vice} | '
              f'3o: {row.nome_terceiro_lugar} | '
              f'Sede: {row.nome_pais_sede} | '
              f'id_sede: {row.id_pais_sede} | '
              f'Confirmado: {row.pais_sede_confirmado}')


# ══════════════════════════════════════════════
# FUNÇÃO PRINCIPAL — run()
# ══════════════════════════════════════════════
def run():
    print('=== Buscando dados do BigQuery ===')
    df_paises       = buscar_paises_bq()
    anos_existentes = verificar_edicoes_existentes()

    # Filtra edições que ainda não estão no banco
    edicoes_coletar = [
        ano for ano in [2018, 2022]
        if ano not in anos_existentes
    ]

    if not edicoes_coletar:
        print('\nTodas as edicoes ja existem no banco!')
        validar_carga()
        return

    print(f'\nEdicoes a coletar: {edicoes_coletar}')

    print('\n=== Coletando Wikipedia ===')
    dados_wiki = []
    for ano in edicoes_coletar:
        resultado = coletar_edicao(ano)
        if resultado['edicao']:
            dados_wiki.append(resultado['edicao'])

    if not dados_wiki:
        print('ERRO: Nenhum dado coletado da Wikipedia!')
        return

    # ── Garante que todos os países existem na tb_paises ──
    print('\n=== Verificando paises ===')
    nomes_paises = []
    for d in dados_wiki:
        nomes_paises.extend([
            d.get('nome_vencedor'),
            d.get('nome_vice'),
            d.get('nome_terceiro_lugar'),
            d.get('nome_pais_sede'),
        ])

    # Atualiza df_paises com eventuais novos países
    # antes de processar — garante IDs corretos
    df_paises = garantir_paises(nomes_paises, df_paises)

    print('\n=== Processando dados ===')
    df_novas = processar_edicoes_wiki(dados_wiki, df_paises)
    print(df_novas.to_string())

    print('\n=== Carregando no BigQuery ===')
    append_edicoes(df_novas)

    print('\n=== Validando ===')
    validar_carga()

    print('\nDia 03 concluido!')


if __name__ == '__main__':
    run()