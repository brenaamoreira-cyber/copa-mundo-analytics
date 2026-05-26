import requests
import time
import re
import pandas as pd
import os
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DE CAMINHOS
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
HEADERS = {'User-Agent': 'CopaMundoBot/1.0 (projeto academico)'}

# Edições que o Kaggle NÃO tem
EDICOES_FALTANDO = [2018, 2022]

# Mapa de fases da Wikipedia para o padrão do projeto
FASE_MAP = {
    'group':        'FASE DE GRUPOS',
    'round of 16':  'OITAVAS',
    'quarter':      'QUARTAS',
    'semi':         'SEMIFINAL',
    'third':        'TERCEIRO LUGAR',
    'final':        'FINAL',
}

# Mapa de países para ISO2 (bandeiras)
ISO2_MAP = {
    'Argentina': 'ar',   'France': 'fr',      'Croatia': 'hr',
    'Morocco': 'ma',     'Qatar': 'qa',        'Brazil': 'br',
    'Germany': 'de',     'Spain': 'es',        'England': 'gb-eng',
    'Belgium': 'be',     'Portugal': 'pt',     'Uruguay': 'uy',
    'Switzerland': 'ch', 'South Korea': 'kr',  'Japan': 'jp',
    'Australia': 'au',   'Netherlands': 'nl',  'Senegal': 'sn',
    'Poland': 'pl',      'Denmark': 'dk',      'Tunisia': 'tn',
    'Mexico': 'mx',      'USA': 'us',          'Canada': 'ca',
    'Saudi Arabia': 'sa','Iran': 'ir',          'Ecuador': 'ec',
    'Ghana': 'gh',       'Cameroon': 'cm',     'Costa Rica': 'cr',
    'Serbia': 'rs',      'Wales': 'gb-wls',    'Russia': 'ru',
    'Sweden': 'se',      'Colombia': 'co',     'Mexico': 'mx',
    'Nigeria': 'ng',     'Iceland': 'is',      'Panama': 'pa',
    'Costa Rica': 'cr',  'Egypt': 'eg',        'Peru': 'pe',
    'Tunisia': 'tn',     'Uruguay': 'uy',
}


# ══════════════════════════════════════════════
# FUNÇÃO AUXILIAR — limpar_valor()
#
# Remove textos indesejados que a Wikipedia
# adiciona junto com os dados:
# 'Argentina (3rd title)[1]' -> 'Argentina'
# 'Qatar[a]'                 -> 'Qatar'
# ══════════════════════════════════════════════
def limpar_valor(val: str) -> str:
    if not val:
        return None
    # Remove conteúdo entre parênteses: (3rd title)
    val = re.sub(r'\(.*?\)', '', val)
    # Remove conteúdo entre colchetes: [1], [a]
    val = re.sub(r'\[.*?\]', '', val)
    # Remove espaços extras
    return val.strip() or None


# ══════════════════════════════════════════════
# FUNÇÃO 1 — get_soup()
#
# ENTRADA: URL da página
# SAIDA:   Objeto BeautifulSoup com o HTML
#
# O @retry tenta automaticamente 3 vezes
# com 5 segundos de espera entre tentativas.
# O time.sleep(1.5) é o delay respeitoso
# para não sobrecarregar o servidor.
# ══════════════════════════════════════════════
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def get_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()  # lança erro se status != 200
    time.sleep(1.5)          # delay respeitoso à Wikipedia
    return BeautifulSoup(resp.text, 'html.parser')


# ══════════════════════════════════════════════
# FUNÇÃO 2 — extrair_infobox()
#
# ENTRADA: soup (HTML interpretado) + ano
# SAIDA:   dicionário com campeão, vice, sede
#
# Percorre as linhas da infobox e captura
# apenas os campos que nos interessam,
# identificados por palavras-chave no th.
# ══════════════════════════════════════════════
def extrair_infobox(soup: BeautifulSoup, ano: int) -> dict:
    dados = {
        'ano_edicao':          ano,
        'nome_vencedor':       None,
        'nome_vice':           None,
        'nome_terceiro_lugar': None,
        'nome_pais_sede':      None,
    }

    infobox = soup.find('table', class_='infobox')
    if not infobox:
        print(f'  Infobox nao encontrada para {ano}')
        return dados

    for row in infobox.find_all('tr'):
        th = row.find('th')
        td = row.find('td')

        # Só processa linhas que têm th E td
        if not th or not td:
            continue

        # Converte para minúsculo para comparar
        key = th.get_text(strip=True).lower()
        val = limpar_valor(td.get_text(' ', strip=True))

        # ── Aqui definimos quais campos capturar ──
        if 'host' in key or key == 'country':
            dados['nome_pais_sede'] = val

        elif 'champion' in key or 'winner' in key:
            dados['nome_vencedor'] = val

        elif 'runner' in key:
            dados['nome_vice'] = val

        elif 'third' in key and 'place' in key:
            dados['nome_terceiro_lugar'] = val

    return dados


# ══════════════════════════════════════════════
# FUNÇÃO 3 — extrair_partidas()
#
# ENTRADA: soup (HTML interpretado) + ano
# SAIDA:   lista de dicionários com partidas
#
# Percorre todos os elementos da página em ordem.
# Quando encontra um heading (h2/h3/h4), atualiza
# a fase atual. Quando encontra uma wikitable,
# extrai as partidas com a fase que estava ativa.
# ══════════════════════════════════════════════
def extrair_partidas(soup: BeautifulSoup, ano: int) -> list:
    partidas  = []
    fase_atual = 'FASE DE GRUPOS'

    for elem in soup.find_all(['h2', 'h3', 'h4', 'table']):

        # ── Se for heading, atualiza a fase ──────
        if elem.name in ['h2', 'h3', 'h4']:
            texto = elem.get_text(strip=True).lower()
            for palavra, fase in FASE_MAP.items():
                if palavra in texto:
                    fase_atual = fase
                    break

        # ── Se for wikitable, extrai partidas ────
        elif elem.name == 'table' and 'wikitable' in elem.get('class', []):
            for row in elem.find_all('tr')[1:]:  # pula o header
                cells = row.find_all(['td', 'th'])

                # Linha precisa ter pelo menos 3 células
                if len(cells) < 3:
                    continue

                try:
                    textos = [
                        limpar_valor(c.get_text(' ', strip=True))
                        for c in cells
                    ]
                    partidas.append({
                        'ano_edicao':   ano,
                        'fase_partida': fase_atual,
                        'dados_brutos': textos,
                    })
                except Exception:
                    continue

    return partidas


# ══════════════════════════════════════════════
# FUNÇÃO 4 — coletar_edicao()
#
# ENTRADA: ano da edição (ex: 2018)
# SAIDA:   dicionário com edicao e partidas
#
# Orquestra as funções anteriores para uma
# edição específica. O try/except garante que
# se uma edição falhar, o script não para.
# ══════════════════════════════════════════════
def coletar_edicao(ano: int) -> dict:
    url = f'https://en.wikipedia.org/wiki/{ano}_FIFA_World_Cup'
    print(f'Coletando {ano}...')

    try:
        soup     = get_soup(url)
        edicao   = extrair_infobox(soup, ano)
        partidas = extrair_partidas(soup, ano)

        print(f'  Edicao:   {edicao}')
        print(f'  Partidas: {len(partidas)} linhas coletadas')

        return {'edicao': edicao, 'partidas': partidas}

    except Exception as e:
        print(f'  ERRO ao coletar {ano}: {e}')
        return {'edicao': {}, 'partidas': []}


# ══════════════════════════════════════════════
# FUNÇÃO 5 — processar_edicoes_wiki()
#
# ENTRADA: lista de dicionários de edições
#          + df_paises para buscar os IDs
# SAIDA:   DataFrame no padrão da tabela
#          edicao_copa do BigQuery
#
# Formata os dados brutos da Wikipedia no
# mesmo padrão das edições do Kaggle.
# id_base=21 porque o Kaggle já tem 20 edições.
# ══════════════════════════════════════════════
def processar_edicoes_wiki(dados_wiki: list, df_paises: pd.DataFrame) -> pd.DataFrame:
    # Dicionário para trocar nome do país pelo ID
    mapa_id = dict(zip(df_paises['des_pais'], df_paises['id_pais']))

    # 2018 recebe id_edicao=21, 2022 recebe id_edicao=22
    id_base = 21

    rows = []
    for i, d in enumerate(dados_wiki):
        nome_venc  = d.get('nome_vencedor')
        nome_vice  = d.get('nome_vice')
        nome_terc  = d.get('nome_terceiro_lugar')
        nome_sede  = d.get('nome_pais_sede')

        rows.append({
            'id_edicao':           id_base + i,
            'ano_edicao':          d.get('ano_edicao'),
            'id_vencedor':         mapa_id.get(nome_venc),
            'nome_vencedor':       nome_venc,
            'id_vice':             mapa_id.get(nome_vice),
            'nome_vice':           nome_vice,
            'id_terceiro_lugar':   mapa_id.get(nome_terc),
            'nome_terceiro_lugar': nome_terc,
            'id_pais_sede':        mapa_id.get(nome_sede),
            'nome_pais_sede':      nome_sede,
        })

    df = pd.DataFrame(rows)
    print(f'Edicoes processadas: {len(df)}')
    return df