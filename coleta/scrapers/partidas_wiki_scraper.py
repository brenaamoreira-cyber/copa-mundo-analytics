import requests
import time
import re
import os
import hashlib
import pandas as pd
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(
             os.path.dirname(
               os.path.dirname(
                 os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

HEADERS = {'User-Agent': 'CopaMundoBot/1.0 (projeto academico)'}

# ─────────────────────────────────────────────
# URLs por edição
# 8 grupos + 1 knockout = 64 partidas por Copa
# ─────────────────────────────────────────────
GRUPOS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

URLS = {
    2018: (
        [f'https://en.wikipedia.org/wiki/2018_FIFA_World_Cup_Group_{g}' for g in GRUPOS] +
        ['https://en.wikipedia.org/wiki/2018_FIFA_World_Cup_knockout_stage']
    ),
    2022: (
        [f'https://en.wikipedia.org/wiki/2022_FIFA_World_Cup_Group_{g}' for g in GRUPOS] +
        ['https://en.wikipedia.org/wiki/2022_FIFA_World_Cup_knockout_stage']
    ),
}

# ─────────────────────────────────────────────
# NORMALIZAÇÃO DE NOMES
# A Wikipedia usa nomes diferentes dos que
# temos na tb_paises. Esse mapa padroniza.
# ─────────────────────────────────────────────
NOME_MAP = {
    'United States':  'USA',
    'South Korea':    'South Korea',
    'IR Iran':        'Iran',
    'Korea Republic': 'South Korea',
    'Côte d\'Ivoire': 'Ivory Coast',
    'Republic of Ireland': 'Republic of Ireland',
}

def normalizar_nome(nome: str) -> str:
    """
    Normaliza nomes de países da Wikipedia
    para o padrão da nossa tb_paises.
    """
    if not nome:
        return nome
    return NOME_MAP.get(nome, nome)

# ─────────────────────────────────────────────
# Mapa de fases baseado na URL
# ─────────────────────────────────────────────
def detectar_fase(url: str, box_index: int, total_boxes: int) -> str:
    """
    Detecta a fase baseado na URL e posição do box.
    No knockout_stage, a Wikipedia organiza assim:
    - Boxes 1-8:  Oitavas de final
    - Boxes 9-12: Quartas de final
    - Boxes 13-14: Semifinais
    - Box 15:     Terceiro lugar
    - Box 16:     Final
    """
    if 'Group' in url:
        return 'FASE DE GRUPOS'

    # knockout_stage tem 16 partidas em ordem
    if box_index <= 7:
        return 'OITAVAS'
    elif box_index <= 11:
        return 'QUARTAS'
    elif box_index <= 13:
        return 'SEMIFINAL'
    elif box_index == 14:
        return 'TERCEIRO LUGAR'
    else:
        return 'FINAL'


# ─────────────────────────────────────────────
# Função para limpar texto
# ─────────────────────────────────────────────
def limpar(texto: str) -> str:
    if not texto:
        return ''
    # Remove notas de rodapé [1], [a], [note 1]
    texto = re.sub(r'\[.*?\]', '', texto)
    # Remove conteúdo entre parênteses exceto (pen.)
    texto = re.sub(r'\((?!pen\.).*?\)', '', texto)
    return texto.strip()


# ─────────────────────────────────────────────
# Função para parsear placar
# Ex: "0–2" → (0, 2)
# Ex: "3–3 (a.e.t.)" → (3, 3)
# ─────────────────────────────────────────────
def parsear_placar(placar_str: str):
    if not placar_str:
        return None, None
    # Remove texto extra como (a.e.t.), (pen.)
    placar_limpo = re.sub(r'\(.*?\)', '', placar_str).strip()
    # Divide pelo traço (–)
    partes = re.split(r'[–\-]', placar_limpo)
    if len(partes) == 2:
        try:
            return int(partes[0].strip()), int(partes[1].strip())
        except ValueError:
            return None, None
    return None, None


# ─────────────────────────────────────────────
# Função para parsear gols
# Ex: "Messi 23' (pen.), 108' Di María 36'"
# → [{'nome': 'Messi', 'minutos': [23, 108], 'pen': True},
#    {'nome': 'Di María', 'minutos': [36], 'pen': False}]
# ─────────────────────────────────────────────
def parsear_gols(td_gol) -> list:
    if not td_gol:
        return []

    gols = []
    # Cada <li> é um jogador com seus gols
    items = td_gol.find_all('li')

    if not items:
        # Sem <li>, tenta parsear o texto direto
        texto = td_gol.get_text(' ', strip=True)
        if texto:
            items_texto = [texto]
        else:
            return []
    else:
        items_texto = [li.get_text(' ', strip=True) for li in items]

    for item in items_texto:
        item = limpar(item)
        if not item:
            continue

        # Extrai minutos: números seguidos de '
        minutos = re.findall(r'(\d+)\+?\d*\'', item)
        # Verifica se algum minuto tem (pen.)
        e_pen = 'pen' in item.lower()

        # Nome é tudo antes do primeiro número seguido de '
        nome_match = re.match(r'^(.*?)\s*\d+\+?\d*\'', item)
        nome = nome_match.group(1).strip() if nome_match else item

        if nome and minutos:
            gols.append({
                'nome_jogador': nome,
                'quantidade_gols': len(minutos),
                'pen': e_pen,
            })

    return gols


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL — extrair_footballboxes()
# ─────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def get_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    time.sleep(1.5)
    return BeautifulSoup(resp.text, 'html.parser')


def extrair_footballboxes(url: str, ano: int) -> list:
    """
    Extrai todas as partidas de uma URL.
    Retorna lista de dicionários com dados de cada partida.
    """
    print(f'  Coletando: {url.split("/")[-1]}')
    soup   = get_soup(url)
    boxes  = soup.find_all('div', class_='footballbox')
    dados  = []

    for i, box in enumerate(boxes):
        try:
            # ── Data ──────────────────────────────────
            fdate = box.find('div', class_='fdate')
            # A data vem como "20 November 2022(2022-11-20)"
            # Precisamos extrair o formato ISO: 2022-11-20
            dt_partida = None
            if fdate:
                texto_data = fdate.get_text(strip=True)
                match_iso  = re.search(r'(\d{4}-\d{2}-\d{2})', texto_data)
                if match_iso:
                    dt_partida = match_iso.group(1)

            # ── Times ─────────────────────────────────
            home_td = box.find('th', class_='fhome')
            away_td = box.find('th', class_='faway')
            nome_time_owner = normalizar_nome(limpar(home_td.get_text(strip=True))) if home_td else None
            nome_time_away  = normalizar_nome(limpar(away_td.get_text(strip=True))) if away_td else None

            # ── Placar ────────────────────────────────
            score_td = box.find('th', class_='fscore')
            placar_str = score_td.get_text(strip=True) if score_td else ''
            placar_owner, placar_away = parsear_placar(placar_str)

            # ── Fase ──────────────────────────────────
            fase = detectar_fase(url, i, len(boxes))

            # ── Gols ──────────────────────────────────
            fhgoal = box.find('td', class_='fhgoal')
            fagoal = box.find('td', class_='fagoal')
            gols_owner = parsear_gols(fhgoal)
            gols_away  = parsear_gols(fagoal)

            dados.append({
                'ano_edicao':     ano,
                'dt_partida':     dt_partida,
                'fase_partida':   fase,
                'nome_time_owner':nome_time_owner,
                'nome_time_away': nome_time_away,
                'placar_owner':   placar_owner,
                'placar_away':    placar_away,
                'gols_owner':     gols_owner,
                'gols_away':      gols_away,
            })

        except Exception as e:
            print(f'    ERRO na partida {i+1}: {e}')
            continue

    print(f'    {len(dados)} partidas extraidas')
    return dados


def coletar_edicao(ano: int) -> list:
    """Coleta todas as partidas de uma edição"""
    print(f'\n=== Coletando {ano} ===')
    todas = []
    for url in URLS[ano]:
        partidas = extrair_footballboxes(url, ano)
        todas.extend(partidas)
        time.sleep(1.5)
    print(f'Total {ano}: {len(todas)} partidas')
    return todas

def formatar_partidas(dados: list, df_paises: pd.DataFrame,
                      id_partida_base: int) -> pd.DataFrame:
    mapa_id = dict(zip(df_paises['des_pais'], df_paises['id_pais']))
    rows    = []

    for i, d in enumerate(dados):
        nome_owner = d.get('nome_time_owner')
        nome_away  = d.get('nome_time_away')
        placar_o   = d.get('placar_owner', 0) or 0
        placar_a   = d.get('placar_away', 0) or 0

        if placar_o > placar_a:
            id_venc   = mapa_id.get(nome_owner)
            nome_venc = nome_owner
        elif placar_a > placar_o:
            id_venc   = mapa_id.get(nome_away)
            nome_venc = nome_away
        else:
            id_venc   = 0
            nome_venc = 'Empate'

        rows.append({
            'id_partida':                 id_partida_base + i + 1,
            'ano_edicao':                 d.get('ano_edicao'),
            'dt_partida':                 d.get('dt_partida'),
            'id_time_owner':              mapa_id.get(nome_owner),
            'nome_time_owner':            nome_owner,
            'id_time_away':               mapa_id.get(nome_away),
            'nome_time_away':             nome_away,
            'fase_partida':               d.get('fase_partida'),
            'id_vencedor':                id_venc,
            'nome_vencedor':              nome_venc,
            'placar_time_owner':          placar_o,
            'placar_time_away':           placar_a,
            'gols_primeiro_tempo_owner':  0,
            'gols_primeiro_tempo_away':   0,
        })

    df = pd.DataFrame(rows)

    # ── Converter dt_partida de string para date ──────────
    # O BigQuery exige tipo DATE, não string
    # "2022-11-20" → datetime.date(2022, 11, 20)
    df['dt_partida'] = pd.to_datetime(
        df['dt_partida'], format='%Y-%m-%d', errors='coerce'
    ).dt.date

    print(f'  Nulos em dt_partida: {df["dt_partida"].isna().sum()}')
    return df


def formatar_jogadores_por_jogo(dados: list, df_paises: pd.DataFrame,
                                 df_partidas_novas: pd.DataFrame,
                                 id_jogo_base: int) -> pd.DataFrame:
    """
    Formata os gols extraídos no padrão da tabela
    jogadoresporjogos do BigQuery.
    Uma linha por jogador por partida.
    """
    mapa_id = dict(zip(df_paises['des_pais'], df_paises['id_pais']))
    rows    = []
    id_jogo = id_jogo_base

    for i, d in enumerate(dados):
        # Busca o id_partida correspondente
        id_partida = None
        filtro     = (
            (df_partidas_novas['nome_time_owner'] == d.get('nome_time_owner')) &
            (df_partidas_novas['nome_time_away']  == d.get('nome_time_away')) &
            (df_partidas_novas['ano_edicao']      == d.get('ano_edicao'))
        )
        match = df_partidas_novas[filtro]
        if len(match) > 0:
            id_partida = int(match['id_partida'].values[0])

        # Processa gols do mandante
        nome_owner = d.get('nome_time_owner')
        for gol in d.get('gols_owner', []):
            nome  = gol['nome_jogador']
            chave = f'{nome}{nome_owner}'
            id_j  = int(hashlib.md5(chave.encode()).hexdigest(), 16) % 10**8
            id_jogo += 1
            rows.append({
                'id_jogo':                    id_jogo,
                'id_jogador':                 id_j,
                'id_partida':                 id_partida,
                'id_time':                    mapa_id.get(nome_owner),
                'nome_time':                  nome_owner,
                'nome_jogador':               nome,
                'posicao_jogador':            None,
                'quantidade_gols':            gol['quantidade_gols'],
                'quantidade_cartao_amarelo':  0,
                'quantidade_cartao_vermelho': 0,
            })

        # Processa gols do visitante
        nome_away = d.get('nome_time_away')
        for gol in d.get('gols_away', []):
            nome  = gol['nome_jogador']
            chave = f'{nome}{nome_away}'
            id_j  = int(hashlib.md5(chave.encode()).hexdigest(), 16) % 10**8
            id_jogo += 1
            rows.append({
                'id_jogo':                    id_jogo,
                'id_jogador':                 id_j,
                'id_partida':                 id_partida,
                'id_time':                    mapa_id.get(nome_away),
                'nome_time':                  nome_away,
                'nome_jogador':               nome,
                'posicao_jogador':            None,
                'quantidade_gols':            gol['quantidade_gols'],
                'quantidade_cartao_amarelo':  0,
                'quantidade_cartao_vermelho': 0,
            })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)[[
        'id_jogo', 'id_jogador', 'id_partida',
        'id_time', 'nome_time', 'nome_jogador',
        'posicao_jogador', 'quantidade_gols',
        'quantidade_cartao_amarelo', 'quantidade_cartao_vermelho',
    ]]