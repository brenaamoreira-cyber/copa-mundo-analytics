from google.cloud import bigquery
import os
from dotenv import load_dotenv

# Caminho absoluto do .env na raiz do projeto
ENV_PATH = r"C:\Users\brena\Desktop\project-world-cup\.env"
load_dotenv(ENV_PATH)

PROJECT     = os.getenv('GCP_PROJECT_ID')
DATASET_RAW = os.getenv('BQ_DATASET_RAW')
DATASET_DW  = os.getenv('BQ_DATASET_DW')

print(f"Projeto:     {PROJECT}")
print(f"Dataset RAW: {DATASET_RAW}")
print(f"Dataset DW:  {DATASET_DW}")

if not PROJECT:
    raise ValueError("GCP_PROJECT_ID nao encontrado — verifique o .env")

client = bigquery.Client(project=PROJECT)

# ─────────────────────────────────────────────
# SCHEMAS DAS TABELAS
# Define nome, tipo e mode de cada coluna.
# mode='REQUIRED' = campo obrigatório (NOT NULL)
# mode='NULLABLE' = campo opcional (padrão)
# ─────────────────────────────────────────────
TABELAS = {
    'tb_paises': [
        bigquery.SchemaField('id_pais',        'INTEGER', mode='REQUIRED'),
        bigquery.SchemaField('des_pais',        'STRING',  mode='NULLABLE'),
        bigquery.SchemaField('des_continente',  'STRING',  mode='NULLABLE'),
        bigquery.SchemaField('img_bandeira',    'STRING',  mode='NULLABLE'),
    ],
    'edicao_copa': [
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
    ],
    'partidas': [
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
    ],
    'jogadores': [
        bigquery.SchemaField('id_jogador',      'INTEGER', mode='REQUIRED'),
        bigquery.SchemaField('nome_jogador',    'STRING',  mode='NULLABLE'),
        bigquery.SchemaField('posicao_jogador', 'STRING',  mode='NULLABLE'),
        bigquery.SchemaField('id_pais',         'INTEGER', mode='NULLABLE'),
        bigquery.SchemaField('nome_pais',       'STRING',  mode='NULLABLE'),
    ],
    'jogadoresporjogos': [
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
    ],
}


def criar_dataset(dataset_id):
    """
    Cria um dataset no BigQuery se não existir.
    exists_ok=True garante que não dá erro
    se o dataset já existir.
    """
    dataset_ref = f'{PROJECT}.{dataset_id}'
    dataset     = bigquery.Dataset(dataset_ref)
    dataset.location = 'US'

    client.create_dataset(dataset, exists_ok=True)
    print(f'  Dataset {dataset_id} OK')


def criar_tabela(dataset_id, nome_tabela, schema):
    """
    Cria uma tabela no BigQuery com o schema definido.
    Se a tabela já existir, não faz nada (exists_ok=True).
    Se quiser recriar do zero, mude para exists_ok=False.
    """
    table_id  = f'{PROJECT}.{dataset_id}.{nome_tabela}'
    table_ref = bigquery.Table(table_id, schema=schema)

    table = client.create_table(table_ref, exists_ok=True)
    print(f'  Tabela {nome_tabela:25s} OK  ({len(schema)} colunas)')


def deletar_tabela(dataset_id, nome_tabela):
    """
    Deleta uma tabela se existir.
    not_found_ok=True evita erro se a tabela não existir.
    Útil para recriar do zero quando o schema mudar.
    """
    table_id = f'{PROJECT}.{dataset_id}.{nome_tabela}'
    client.delete_table(table_id, not_found_ok=True)
    print(f'  Tabela {nome_tabela} deletada')


def recriar_tabelas(dataset_id):
    """
    Deleta e recria todas as tabelas.
    Use quando o schema mudar e precisar
    recriar as tabelas do zero.
    """
    print(f'\nRecriando tabelas em {dataset_id}...')
    for nome, schema in TABELAS.items():
        deletar_tabela(dataset_id, nome)
        criar_tabela(dataset_id, nome, schema)


def criar_estrutura_completa():
    """
    Cria datasets e tabelas do zero.
    Função principal — rode essa para configurar
    o BigQuery antes de carregar os dados.
    """
    print('=== Criando datasets ===')
    criar_dataset(DATASET_RAW)
    criar_dataset(DATASET_DW)

    print(f'\n=== Criando tabelas em {DATASET_RAW} ===')
    for nome, schema in TABELAS.items():
        criar_tabela(DATASET_RAW, nome, schema)

    print('\n=== Estrutura criada com sucesso! ===')
    listar_tabelas(DATASET_RAW)


def listar_tabelas(dataset_id):
    """
    Lista todas as tabelas existentes no dataset
    com o número de colunas de cada uma.
    """
    print(f'\nTabelas em {dataset_id}:')
    tabelas = list(client.list_tables(f'{PROJECT}.{dataset_id}'))

    if not tabelas:
        print('  Nenhuma tabela encontrada.')
        return

    for t in tabelas:
        table    = client.get_table(f'{PROJECT}.{dataset_id}.{t.table_id}')
        n_colunas = len(table.schema)
        n_linhas  = table.num_rows
        print(f'  {t.table_id:25s} {n_colunas} colunas  {n_linhas} linhas')


# ─────────────────────────────────────────────
# MENU PRINCIPAL
# Permite escolher o que fazer ao rodar o script
# ─────────────────────────────────────────────
if __name__ == '__main__':
    print("""
╔══════════════════════════════════════╗
║   Gerenciador de Tabelas BigQuery    ║
╚══════════════════════════════════════╝

O que deseja fazer?

  1 - Criar estrutura completa (datasets + tabelas)
  2 - Recriar tabelas do zero (apaga e recria)
  3 - Listar tabelas existentes
  4 - Sair
    """)

    opcao = input('Digite a opção (1/2/3/4): ').strip()

    if opcao == '1':
        criar_estrutura_completa()

    elif opcao == '2':
        print('\n⚠️  Isso vai APAGAR e recriar todas as tabelas.')
        confirma = input('Confirma? (s/n): ').strip().lower()
        if confirma == 's':
            recriar_tabelas(DATASET_RAW)
            print('\nTabelas recriadas com sucesso!')
            listar_tabelas(DATASET_RAW)
        else:
            print('Operação cancelada.')

    elif opcao == '3':
        listar_tabelas(DATASET_RAW)

    elif opcao == '4':
        print('Saindo...')

    else:
        print('Opção inválida.')