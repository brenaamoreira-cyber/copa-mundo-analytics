import requests
import os
import sys

# Configurar caminho do .env
BASE_DIR = os.path.dirname(
             os.path.dirname(
               os.path.dirname(
                 os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

TOKEN    = os.getenv('FOOTBALL_DATA_API_KEY')
BASE_URL = 'https://api.football-data.org/v4'
HEADERS  = {'X-Auth-Token': TOKEN}

print(f'Token carregado: {TOKEN[:8]}...')  # mostra só os primeiros 8 caracteres

# ── Teste 1: Acessar informações da Copa do Mundo ──
print('\n=== Teste 1: Informacoes da competicao ===')
resp = requests.get(f'{BASE_URL}/competitions/WC', headers=HEADERS)
print(f'Status: {resp.status_code}')

if resp.status_code == 200:
    data = resp.json()
    print(f'Competicao: {data["name"]}')
    print(f'Area:       {data["area"]["name"]}')
    print('TOKEN OK!')

elif resp.status_code == 400:
    print('ERRO: Token invalido — verifique o .env')

elif resp.status_code == 429:
    print('ERRO: Rate limit atingido — aguarde 1 minuto')

else:
    print(f'ERRO inesperado: {resp.status_code}')
    print(resp.text)