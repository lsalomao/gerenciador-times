import os
import sys

# Adicionar o diretório do projeto ao path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gerenciador_volei.settings')

import django
django.setup()

from volei.views import gerar_times_simplificado
from volei.models import Jogador
from datetime import date
import random

# Criar jogadores de teste com MUITOS jogadores nível 5
jogadores = []
id_counter = 1

# 4 Levantadores (alguns nível 5)
for i in range(1, 5):
    j = Jogador(
        nome=f'Levantador {i}',
        nivel=5 if i <= 2 else 4,  # 2 levantadores nível 5
        posicao_preferida='levantador',
        tipo_jogador='fixo'
    )
    j.id = id_counter
    id_counter += 1
    jogadores.append(j)

# 4 Liberos (alguns nível 5)
for i in range(1, 5):
    j = Jogador(
        nome=f'Libero {i}',
        nivel=5 if i <= 2 else 4,  # 2 líberos nível 5
        posicao_preferida='libero',
        tipo_jogador='fixo'
    )
    j.id = id_counter
    id_counter += 1
    jogadores.append(j)

# 12 Fixos normais - MUITOS nível 5 para testar a regra
for i in range(12):
    # 8 jogadores nível 5, 4 jogadores nível 4
    nivel = 5 if i < 8 else 4
    j = Jogador(
        nome=f'Fixo {i+1} (Nível {nivel})',
        nivel=nivel,
        posicao_preferida='central',
        tipo_jogador='fixo'
    )
    j.id = id_counter
    id_counter += 1
    jogadores.append(j)

print(f'Criados {len(jogadores)} jogadores para teste')
print(f'- Total nível 5: {len([j for j in jogadores if j.nivel == 5])}')
print(f'- Total nível 4: {len([j for j in jogadores if j.nivel == 4])}')
print()

# Gerar times
times = gerar_times_simplificado(jogadores, date.today())

print('\n' + '='*70)
print('RESULTADO DA DISTRIBUIÇÃO')
print('='*70)

for i, (titulares, reservas) in enumerate(times, 1):
    levantadores = [j for j in titulares if j.posicao_preferida == 'levantador']
    liberos = [j for j in titulares if j.posicao_preferida == 'libero']
    nivel_5 = [j for j in titulares if j.nivel == 5]
    soma = sum(j.nivel for j in titulares)

    print(f'\nTime {i} ({len(titulares)} titulares, soma: {soma}):')
    print(f'  Titulares: {[j.nome for j in titulares]}')
    print(f'  Levantadores: {len(levantadores)} | Liberos: {len(liberos)} | Nível 5: {len(nivel_5)}')

print('\n' + '='*70)
print('VERIFICAÇÃO DE NÍVEL 5:')
print('='*70)
for i, (titulares, reservas) in enumerate(times, 1):
    nivel_5 = [j for j in titulares if j.nivel == 5]
    print(f'Time {i}: {len(nivel_5)} jogador(es) nível 5')

# Verificar se há algum time com 3+ jogadores nível 5
print('\n' + '='*70)
print('ALERTAS:')
print('='*70)
alertas = []
for i, (titulares, reservas) in enumerate(times, 1):
    nivel_5 = [j for j in titulares if j.nivel == 5]
    if len(nivel_5) >= 3:
        alertas.append(f'Time {i} tem {len(nivel_5)} jogadores nível 5!')

if alertas:
    for alerta in alertas:
        print(f'⚠️  {alerta}')
else:
    print('✅ Nenhum time tem 3+ jogadores nível 5')
