#!/usr/bin/env python
"""
Teste simplificado do algoritmo de geração de times
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gerenciador_volei.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from volei.views import gerar_times_simplificado
from volei.models import Jogador
from datetime import date

class MockJogador:
    def __init__(self, id, nome, nivel, posicao, tipo='fixo'):
        self.id = id
        self.nome = nome
        self.nivel = nivel
        self.posicao_preferida = posicao
        self.tipo_jogador = tipo

    def __repr__(self):
        return f"{self.nome} (Nível {self.nivel})"

def criar_jogadores_teste():
    """Cria jogadores simulando a situação da imagem"""
    jogadores = []
    id_counter = 1

    # Levantadores (diferentes níveis)
    for i in range(4):
        jogadores.append(MockJogador(id_counter, f"Levantador {i+1}", 4 if i < 2 else 3, 'levantador'))
        id_counter += 1

    # Líberos (diferentes níveis)
    for i in range(4):
        jogadores.append(MockJogador(id_counter, f"Libero {i+1}", 4 if i < 2 else 3, 'libero'))
        id_counter += 1

    # Fixos nível 5 (poucos)
    for i in range(4):
        jogadores.append(MockJogador(id_counter, f"Fixo Nível 5 - {chr(65+i)}", 5, 'nao_definido'))
        id_counter += 1

    # Fixos nível 4
    for i in range(4):
        jogadores.append(MockJogador(id_counter, f"Fixo Nível 4 - {chr(65+i)}", 4, 'nao_definido'))
        id_counter += 1

    # Fixos nível 3 (vários)
    for i in range(6):
        jogadores.append(MockJogador(id_counter, f"Fixo Nível 3 - {chr(65+i)}", 3, 'nao_definido'))
        id_counter += 1

    # Fixos nível 2
    for i in range(2):
        jogadores.append(MockJogador(id_counter, f"Fixo Nível 2 - {chr(65+i)}", 2, 'nao_definido'))
        id_counter += 1

    return jogadores

def main():
    print("=" * 70)
    print("TESTE SIMPLIFICADO - GERAÇÃO DE TIMES")
    print("=" * 70)

    jogadores = criar_jogadores_teste()
    print(f"\nTotal de jogadores: {len(jogadores)}")

    # Contar por nível
    for nivel in [5, 4, 3, 2]:
        count = sum(1 for j in jogadores if j.nivel == nivel)
        print(f"  Nível {nivel}: {count} jogadores")

    print(f"  Levantadores: {sum(1 for j in jogadores if j.posicao_preferida == 'levantador')}")
    print(f"  Líberos: {sum(1 for j in jogadores if j.posicao_preferida == 'libero')}")

    print("\n" + "=" * 70)
    print("RESULTADO DA DISTRIBUIÇÃO")
    print("=" * 70)

    try:
        resultado = gerar_times_simplificado(jogadores, date.today())

        for i, (titulares, reservas) in enumerate(resultado, 1):
            soma = sum(j.nivel for j in titulares)
            levantadores = sum(1 for j in titulares if j.posicao_preferida == 'levantador')
            liberos = sum(1 for j in titulares if j.posicao_preferida == 'libero')

            print(f"\nTime {i} ({len(titulares)} titulares, soma: {soma}):")
            print(f"  Titulares: {[j.nome for j in titulares]}")
            print(f"  Levantadores: {levantadores} | Líberos: {liberos}")

            if reservas:
                print(f"  Reservas: {[j.nome for j in reservas]}")

        # Verificar equilíbrio
        print("\n" + "=" * 70)
        print("VERIFICAÇÃO DE EQUILÍBRIO")
        print("=" * 70)

        somas = [sum(j.nivel for j in titulares) for titulares, _ in resultado]
        max_diff = max(somas) - min(somas)

        print(f"Somas dos níveis por time: {somas}")
        print(f"Diferença máxima: {max_diff}")

        # Verificar levantadores e líberos
        print("\nVerificação de posições:")
        for i, (titulares, _) in enumerate(resultado, 1):
            levs = sum(1 for j in titulares if j.posicao_preferida == 'levantador')
            libs = sum(1 for j in titulares if j.posicao_preferida == 'libero')
            status = "✅" if levs >= 1 and libs >= 1 else "⚠️"
            print(f"  Time {i}: {levs} levantador(es), {libs} líbero(s) {status}")

    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
