import pandas as pd
import os
import hashlib
import re
from dotenv import load_dotenv

# Carrega o .env da raiz do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# ─────────────────────────────────────────────
# MAPA DE PAÍSES PARA CÓDIGO ISO2
# Usado para gerar o link da bandeira
# ─────────────────────────────────────────────
ISO2_MAP = {
    'Brazil': 'br',          'Germany': 'de',
    'Argentina': 'ar',       'France': 'fr',
    'Italy': 'it',           'Spain': 'es',
    'England': 'gb-eng',     'Uruguay': 'uy',
    'Netherlands': 'nl',     'Sweden': 'se',
    'Hungary': 'hu',         'Czechoslovakia': 'cz',
    'Austria': 'at',         'Yugoslavia': 'rs',
    'Poland': 'pl',          'Portugal': 'pt',
    'Mexico': 'mx',          'USA': 'us',
    'Belgium': 'be',         'Romania': 'ro',
    'Chile': 'cl',           'Croatia': 'hr',
    'Turkey': 'tr',          'South Korea': 'kr',
    'Japan': 'jp',           'Senegal': 'sn',
    'Morocco': 'ma',         'Colombia': 'co',
    'Australia': 'au',       'Switzerland': 'ch',
    'Denmark': 'dk',         'Nigeria': 'ng',
    'Cameroon': 'cm',        'Iran': 'ir',
    'Costa Rica': 'cr',      'Ecuador': 'ec',
    'Ghana': 'gh',           'Russia': 'ru',
    'Serbia': 'rs',          'Algeria': 'dz',
    'Greece': 'gr',          'Bosnia': 'ba',
    'Honduras': 'hn',        'Qatar': 'qa',
    'Canada': 'ca',          'Germany FR': 'de',
    'Soviet Union': 'ru',    'Zaire': 'cd',
    'East Germany': 'de',    'North Korea': 'kp',
    'Paraguay': 'py',        'Peru': 'pe',
    'Bolivia': 'bo',         'Egypt': 'eg',
    'Scotland': 'gb-sct',    'Wales': 'gb-wls',
    'Cuba': 'cu',            'Iraq': 'iq',
    'UAE': 'ae',             'Saudi Arabia': 'sa',
    'Tunisia': 'tn',         'Togo': 'tg',
    'Angola': 'ao',          'Ivory Coast': 'ci',
    'Slovenia': 'si',        'Slovakia': 'sk',
    'Ukraine': 'ua',         'New Zealand': 'nz',
    'El Salvador': 'sv',     'Haiti': 'ht',
    'Israel': 'il',          'Kuwait': 'kw',
    'Northern Ireland': 'gb-nir',
    'Republic of Ireland': 'ie',
    'China PR': 'cn',        'Bulgaria': 'bg',
    'Trinidad and Tobago': 'tt',
}

# ─────────────────────────────────────────────
# MAPA DE SIGLAS PARA NOMES COMPLETOS
# O Kaggle usa BRA, GER, ARG...
# ─────────────────────────────────────────────
SIGLA_MAP = {
    'BRA': 'Brazil',       'GER': 'Germany',
    'ARG': 'Argentina',    'FRA': 'France',
    'ITA': 'Italy',        'ESP': 'Spain',
    'ENG': 'England',      'URU': 'Uruguay',
    'NED': 'Netherlands',  'POR': 'Portugal',
    'MEX': 'Mexico',       'USA': 'USA',
    'BEL': 'Belgium',      'SWE': 'Sweden',
    'CHI': 'Chile',        'CRO': 'Croatia',
    'TUR': 'Turkey',       'KOR': 'South Korea',
    'JPN': 'Japan',        'SEN': 'Senegal',
    'MAR': 'Morocco',      'COL': 'Colombia',
    'AUS': 'Australia',    'SUI': 'Switzerland',
    'DEN': 'Denmark',      'NGA': 'Nigeria',
    'CMR': 'Cameroon',     'IRN': 'Iran',
    'CRC': 'Costa Rica',   'ECU': 'Ecuador',
    'GHA': 'Ghana',        'RUS': 'Russia',
    'SRB': 'Serbia',       'ALG': 'Algeria',
    'GRE': 'Greece',       'QAT': 'Qatar',
    'GFR': 'Germany FR',   'URS': 'Soviet Union',
    'YUG': 'Yugoslavia',   'TCH': 'Czechoslovakia',
    'ZAI': 'Zaire',        'SCO': 'Scotland',
    'WAL': 'Wales',        'NIR': 'Northern Ireland',
    'IRL': 'Republic of Ireland',
    'CHN': 'China PR',     'PRK': 'North Korea',
    'PAR': 'Paraguay',     'PER': 'Peru',
    'BOL': 'Bolivia',      'EGY': 'Egypt',
    'CUB': 'Cuba',         'IRQ': 'Iraq',
    'KUW': 'Kuwait',       'TUN': 'Tunisia',
    'TOG': 'Togo',         'ANG': 'Angola',
    'CIV': 'Ivory Coast',  'SVN': 'Slovenia',
    'SVK': 'Slovakia',     'UKR': 'Ukraine',
    'TRI': 'Trinidad and Tobago',
    'NZL': 'New Zealand',  'SLV': 'El Salvador',
    'HAI': 'Haiti',        'ISR': 'Israel',
    'SAU': 'Saudi Arabia', 'UAE': 'UAE',
    'ROM': 'Romania',      'POL': 'Poland',
    'HUN': 'Hungary',      'AUT': 'Austria',
    'EGD': 'East Germany', 'BUL': 'Bulgaria',
    'MOR': 'Morocco',
}


def get_flag_url(pais, size=80):
    """Gera URL da bandeira via flagcdn.com"""
    code = ISO2_MAP.get(pais, 'un')
    return f'https://flagcdn.com/w{size}/{code}.png'


# ══════════════════════════════════════════════
# FUNÇÃO 1 — processar_paises()
# SAIDA: id_pais, des_pais, des_continente,
#        img_bandeira
# ══════════════════════════════════════════════
def processar_paises(df_copas, df_partidas):
    paises = set()

    for col in ['Winner', 'Runners-Up', 'Third', 'Fourth', 'Country']:
        paises.update(df_copas[col].dropna().unique())

    for col in ['Home Team Name', 'Away Team Name']:
        paises.update(df_partidas[col].dropna().unique())

    paises = {
        p for p in paises
        if isinstance(p, str) and p.strip() != ''
    }

    rows = []
    for i, pais in enumerate(sorted(paises), start=1):
        rows.append({
            'id_pais':        i,
            'des_pais':       pais,
            'des_continente': '',
            'img_bandeira':   get_flag_url(pais),
        })

    df = pd.DataFrame(rows)
    print(f'tb_paises: {len(df)} paises')
    return df


# ══════════════════════════════════════════════
# FUNÇÃO 2 — processar_edicoes()
# SAIDA: id_edicao, ano_edicao,
#        id_vencedor, nome_vencedor,
#        id_vice, nome_vice,
#        id_terceiro_lugar, nome_terceiro_lugar,
#        id_pais_sede, nome_pais_sede
# ══════════════════════════════════════════════
def processar_edicoes(df_copas, df_paises):
    mapa_id = dict(zip(df_paises['des_pais'], df_paises['id_pais']))

    df = df_copas.rename(columns={
        'Year':       'ano_edicao',
        'Winner':     'nome_vencedor',
        'Runners-Up': 'nome_vice',
        'Third':      'nome_terceiro_lugar',
        'Country':    'nome_pais_sede',
    }).copy()

    df['id_edicao']         = range(1, len(df) + 1)
    df['id_vencedor']       = df['nome_vencedor'].map(mapa_id)
    df['id_vice']           = df['nome_vice'].map(mapa_id)
    df['id_terceiro_lugar'] = df['nome_terceiro_lugar'].map(mapa_id)
    df['id_pais_sede']      = df['nome_pais_sede'].map(mapa_id)

    resultado = df[[
        'id_edicao',          'ano_edicao',
        'id_vencedor',        'nome_vencedor',
        'id_vice',            'nome_vice',
        'id_terceiro_lugar',  'nome_terceiro_lugar',
        'id_pais_sede',       'nome_pais_sede',
    ]]

    print(f'edicao_copa: {len(resultado)} edicoes')
    return resultado


# ══════════════════════════════════════════════
# FUNÇÃO 3 — processar_partidas()
# SAIDA: id_partida, ano_edicao, dt_partida,
#        id_time_owner, nome_time_owner,
#        id_time_away, nome_time_away,
#        fase_partida,
#        id_vencedor, nome_vencedor,
#        placar_time_owner, placar_time_away,
#        gols_primeiro_tempo_owner,
#        gols_primeiro_tempo_away
# ══════════════════════════════════════════════
def processar_partidas(df_partidas, df_paises):
    mapa_id = dict(zip(df_paises['des_pais'], df_paises['id_pais']))

    df = df_partidas.dropna(how='all').copy()

    df = df.rename(columns={
        'Year':                 'ano_edicao',
        'Datetime':             'dt_partida',
        'Stage':                'fase_partida',
        'Home Team Name':       'nome_time_owner',
        'Away Team Name':       'nome_time_away',
        'Home Team Goals':      'placar_time_owner',
        'Away Team Goals':      'placar_time_away',
        'Half-time Home Goals': 'gols_primeiro_tempo_owner',
        'Half-time Away Goals': 'gols_primeiro_tempo_away',
    })

    df['id_partida']    = range(1, len(df) + 1)
    df['id_time_owner'] = df['nome_time_owner'].map(mapa_id)
    df['id_time_away']  = df['nome_time_away'].map(mapa_id)
    df['ano_edicao']    = df['ano_edicao'].astype(int)

    df['placar_time_owner']         = df['placar_time_owner'].fillna(0).astype(int)
    df['placar_time_away']          = df['placar_time_away'].fillna(0).astype(int)
    df['gols_primeiro_tempo_owner'] = df['gols_primeiro_tempo_owner'].fillna(0).astype(int)
    df['gols_primeiro_tempo_away']  = df['gols_primeiro_tempo_away'].fillna(0).astype(int)

    # Converter data — trata formato abreviado (Jul) e completo (July)
    datas       = df['dt_partida'].str.strip().str.replace(' - ', ' ', regex=False)
    dt_abrev    = pd.to_datetime(datas, format='%d %b %Y %H:%M',  errors='coerce')
    dt_completo = pd.to_datetime(datas, format='%d %B %Y %H:%M',  errors='coerce')
    df['dt_partida'] = dt_abrev.combine_first(dt_completo).dt.date

    # Normalizar fases
    fase_map = {
        'Group 1': 'FASE DE GRUPOS', 'Group 2': 'FASE DE GRUPOS',
        'Group 3': 'FASE DE GRUPOS', 'Group 4': 'FASE DE GRUPOS',
        'Group 5': 'FASE DE GRUPOS', 'Group 6': 'FASE DE GRUPOS',
        'Group 7': 'FASE DE GRUPOS', 'Group 8': 'FASE DE GRUPOS',
        'Group A': 'FASE DE GRUPOS', 'Group B': 'FASE DE GRUPOS',
        'Group C': 'FASE DE GRUPOS', 'Group D': 'FASE DE GRUPOS',
        'Group E': 'FASE DE GRUPOS', 'Group F': 'FASE DE GRUPOS',
        'Group G': 'FASE DE GRUPOS', 'Group H': 'FASE DE GRUPOS',
        'Round of 16':               'OITAVAS',
        'Quarter-finals':            'QUARTAS',
        'Semi-finals':               'SEMIFINAL',
        'Third place':               'TERCEIRO LUGAR',
        'Play-off for third place':  'TERCEIRO LUGAR',
        'Final':                     'FINAL',
    }
    df['fase_partida'] = df['fase_partida'].map(
        lambda x: fase_map.get(str(x).strip(), 'FASE DE GRUPOS')
    )

    # Determinar vencedor — ID e nome
    def get_id_vencedor(row):
        if row['placar_time_owner'] > row['placar_time_away']:
            return row['id_time_owner']
        elif row['placar_time_away'] > row['placar_time_owner']:
            return row['id_time_away']
        return 0

    def get_nome_vencedor(row):
        if row['placar_time_owner'] > row['placar_time_away']:
            return row['nome_time_owner']
        elif row['placar_time_away'] > row['placar_time_owner']:
            return row['nome_time_away']
        return 'Empate'

    df['id_vencedor']   = df.apply(get_id_vencedor,   axis=1)
    df['nome_vencedor'] = df.apply(get_nome_vencedor, axis=1)

    resultado = df[[
        'id_partida',                'ano_edicao',
        'dt_partida',
        'id_time_owner',             'nome_time_owner',
        'id_time_away',              'nome_time_away',
        'fase_partida',
        'id_vencedor',               'nome_vencedor',
        'placar_time_owner',         'placar_time_away',
        'gols_primeiro_tempo_owner', 'gols_primeiro_tempo_away',
    ]]

    print(f'partidas: {len(resultado)} jogos')
    return resultado


# ══════════════════════════════════════════════
# FUNÇÃO 4 — processar_jogadores()
# SAIDA: id_jogador, nome_jogador,
#        posicao_jogador, id_pais, nome_pais
# ══════════════════════════════════════════════
def processar_jogadores(df_jogadores, df_paises):
    mapa_id = dict(zip(df_paises['des_pais'], df_paises['id_pais']))

    posicao_map = {
        'GK': 'GK',
        'DF': 'DEF',
        'MF': 'MID',
        'FW': 'FWD',
    }

    jogadores_unicos = {}

    for _, row in df_jogadores.iterrows():
        nome  = str(row.get('Player Name', '')).strip()
        sigla = str(row.get('Team Initials', '')).strip()
        pais  = SIGLA_MAP.get(sigla, sigla)
        chave = f'{nome}{pais}'
        id_j  = int(hashlib.md5(chave.encode()).hexdigest(), 16) % 10**8

        if id_j not in jogadores_unicos:
            pos_raw = str(row.get('Position', '')).strip()
            jogadores_unicos[id_j] = {
                'id_jogador':      id_j,
                'nome_jogador':    nome,
                'posicao_jogador': posicao_map.get(pos_raw),
                'id_pais':         mapa_id.get(pais),
                'nome_pais':       pais,
            }

    df = pd.DataFrame(list(jogadores_unicos.values()))[[
        'id_jogador', 'nome_jogador',
        'posicao_jogador',
        'id_pais',    'nome_pais',
    ]]

    print(f'jogadores: {len(df)} jogadores unicos')
    return df


# ══════════════════════════════════════════════
# FUNÇÃO 5 — processar_jogadores_por_partida()
# SAIDA: id_jogo, id_jogador, id_partida,
#        id_time, nome_time,
#        nome_jogador, posicao_jogador,
#        quantidade_gols,
#        quantidade_cartao_amarelo,
#        quantidade_cartao_vermelho
# ══════════════════════════════════════════════
def processar_jogadores_por_partida(df_jogadores, df_paises, df_partidas_proc):
    mapa_id = dict(zip(df_paises['des_pais'], df_paises['id_pais']))

    posicao_map = {
        'GK': 'GK',
        'DF': 'DEF',
        'MF': 'MID',
        'FW': 'FWD',
    }

    match_ids    = df_jogadores['MatchID'].dropna().unique()
    mapa_partida = {
        int(mid): i + 1
        for i, mid in enumerate(sorted(match_ids))
    }

    def parse_evento(event_str):
        """
        Extrai gols e cartões da coluna Event.
        G = gol, Y = amarelo, R = vermelho
        Exemplo: 'G40 Y75' -> gols=1, amarelos=1, vermelhos=0
        """
        if pd.isna(event_str) or str(event_str).strip() == '':
            return 0, 0, 0
        s         = str(event_str)
        gols      = len(re.findall(r'G\d+', s))
        amarelos  = len(re.findall(r'Y\d+', s))
        vermelhos = len(re.findall(r'R\d+', s))
        return gols, amarelos, vermelhos

    rows = []
    for idx, row in df_jogadores.iterrows():
        nome  = str(row.get('Player Name', '')).strip()
        sigla = str(row.get('Team Initials', '')).strip()
        pais  = SIGLA_MAP.get(sigla, sigla)
        chave = f'{nome}{pais}'
        id_j  = int(hashlib.md5(chave.encode()).hexdigest(), 16) % 10**8

        match_id   = row.get('MatchID')
        id_partida = mapa_partida.get(int(match_id)) if pd.notna(match_id) else None

        pos_raw = str(row.get('Position', '')).strip()
        posicao = posicao_map.get(pos_raw)

        gols, amarelos, vermelhos = parse_evento(row.get('Event'))

        rows.append({
            'id_jogo':                    idx + 1,
            'id_jogador':                 id_j,
            'id_partida':                 id_partida,
            'id_time':                    mapa_id.get(pais),
            'nome_time':                  pais,
            'nome_jogador':               nome,
            'posicao_jogador':            posicao,
            'quantidade_gols':            gols,
            'quantidade_cartao_amarelo':  amarelos,
            'quantidade_cartao_vermelho': vermelhos,
        })

    df = pd.DataFrame(rows)[[
        'id_jogo',     'id_jogador',   'id_partida',
        'id_time',     'nome_time',
        'nome_jogador','posicao_jogador',
        'quantidade_gols',
        'quantidade_cartao_amarelo',
        'quantidade_cartao_vermelho',
    ]]

    print(f'jogadoresporjogos: {len(df)} registros')
    print(f'  Gols registrados:  {df["quantidade_gols"].sum()}')
    print(f'  Cartoes amarelos:  {df["quantidade_cartao_amarelo"].sum()}')
    print(f'  Cartoes vermelhos: {df["quantidade_cartao_vermelho"].sum()}')
    return df