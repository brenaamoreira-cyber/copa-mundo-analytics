import sys
import os

# Configurar caminhos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

import requests
from bs4 import BeautifulSoup

# HEADER — nos identificamos honestamente
# Sem isso o servidor pode nos bloquear
# ─────────────────────────────────────────────
HEADERS = {'User-Agent': 'CopaMundoBot/1.0 (projeto academico)'}

def testar_acesso(ano: int):
    print(f'Testando acesso: Copa {ano}')

    url = f'https://en.wikipedia.org/wiki/{ano}_FIFA_World_Cup'
    print(f'URL: {url}')

    # ── Passo 1: Testar conexão ──────────────────
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f'Status HTTP: {resp.status_code}')   # 200 = sucesso

        if resp.status_code != 200:
            print('ERRO: Nao conseguimos acessar a pagina!')
            return

    except requests.exceptions.Timeout:
        print('ERRO: Timeout — servidor demorou demais para responder')
        return
    except requests.exceptions.ConnectionError:
        print('ERRO: Sem conexao com a internet')
        return

    # ── Passo 2: Interpretar o HTML ──────────────
    soup = BeautifulSoup(resp.text, 'html.parser')
    print(f'Tamanho do HTML: {len(resp.text):,} caracteres')

    # ── Passo 3: Verificar a infobox ─────────────
    # A infobox tem campeao, vice, sede
    infobox = soup.find('table', class_='infobox')
    print(f'Infobox encontrada: {infobox is not None}')

    if infobox:
        print('\nConteudo da infobox (primeiras linhas):')
        for i, row in enumerate(infobox.find_all('tr')[:20]):
            th = row.find('th')
            td = row.find('td')
            if th and td:
                key = th.get_text(strip=True)
                val = td.get_text(' ', strip=True)[:50]  # limita a 50 chars
                print(f'  {key:20s} -> {val}')

    # ── Passo 4: Verificar tabelas de partidas ───
    wikitables = soup.find_all('table', class_='wikitable')
    print(f'\nTabelas de partidas (wikitable): {len(wikitables)}')

    # ── Passo 5: Ver headings da página ──────────
    # Os headings identificam as fases (Group Stage, Quarter-finals, etc.)
    print('\nHeadings da pagina (h2):')
    for h2 in soup.find_all('h2')[:8]:
        texto = h2.get_text(strip=True)
        if texto and texto != 'Contents':
            print(f'  {texto}')

    print(f'\nCopa {ano}: ACESSO OK!')


# Testar as duas edicoes que precisamos
testar_acesso(2018)
testar_acesso(2022)

print('\n\nSe ambas mostraram ACESSO OK, pode avançar para o Bloco 3!')