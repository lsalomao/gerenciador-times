import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gerenciador_volei.settings')
django.setup()

from volei.models import Jogador, Presenca, Time
from volei.views import gerar_times_simplificado


def criar_jogadores_teste():
    """Cria jogadores de teste para simular diferentes cenários"""
    Jogador.objects.all().delete()
    
    jogadores = [
        {'nome': 'Levantador 1', 'nivel': 5, 'posicao': 'levantador', 'tipo': 'fixo'},
        {'nome': 'Levantador 2', 'nivel': 4, 'posicao': 'levantador', 'tipo': 'fixo'},
        {'nome': 'Levantador 3', 'nivel': 3, 'posicao': 'levantador', 'tipo': 'convidado'},
        {'nome': 'Levantador 4', 'nivel': 3, 'posicao': 'levantador', 'tipo': 'convidado'},
        
        {'nome': 'Líbero 1', 'nivel': 4, 'posicao': 'libero', 'tipo': 'fixo'},
        {'nome': 'Líbero 2', 'nivel': 3, 'posicao': 'libero', 'tipo': 'convidado'},
        
        {'nome': 'Fixo Nível 5 - A', 'nivel': 5, 'posicao': 'ponta', 'tipo': 'fixo'},
        {'nome': 'Fixo Nível 5 - B', 'nivel': 5, 'posicao': 'oposto', 'tipo': 'fixo'},
        {'nome': 'Fixo Nível 4 - A', 'nivel': 4, 'posicao': 'ponta', 'tipo': 'fixo'},
        {'nome': 'Fixo Nível 4 - B', 'nivel': 4, 'posicao': 'oposto', 'tipo': 'fixo'},
        {'nome': 'Fixo Nível 3 - A', 'nivel': 3, 'posicao': 'ponta', 'tipo': 'fixo'},
        {'nome': 'Fixo Nível 3 - B', 'nivel': 3, 'posicao': 'oposto', 'tipo': 'fixo'},
        {'nome': 'Fixo Nível 2 - A', 'nivel': 2, 'posicao': 'ponta', 'tipo': 'fixo'},
        {'nome': 'Fixo Nível 2 - B', 'nivel': 2, 'posicao': 'oposto', 'tipo': 'fixo'},
        
        {'nome': 'Convidado Nível 5', 'nivel': 5, 'posicao': 'ponta', 'tipo': 'convidado'},
        {'nome': 'Convidado Nível 4 - A', 'nivel': 4, 'posicao': 'oposto', 'tipo': 'convidado'},
        {'nome': 'Convidado Nível 4 - B', 'nivel': 4, 'posicao': 'ponta', 'tipo': 'convidado'},
        {'nome': 'Convidado Nível 3 - A', 'nivel': 3, 'posicao': 'oposto', 'tipo': 'convidado'},
        {'nome': 'Convidado Nível 3 - B', 'nivel': 3, 'posicao': 'ponta', 'tipo': 'convidado'},
        {'nome': 'Convidado Nível 2 - A', 'nivel': 2, 'posicao': 'oposto', 'tipo': 'convidado'},
        {'nome': 'Convidado Nível 2 - B', 'nivel': 2, 'posicao': 'ponta', 'tipo': 'convidado'},
    ]
    
    jogadores_criados = []
    for j in jogadores:
        jogador = Jogador.objects.create(
            nome=j['nome'],
            nivel=j['nivel'],
            posicao_preferida=j['posicao'],
            tipo_jogador=j['tipo'],
            ativo=True
        )
        jogadores_criados.append(jogador)
    
    print(f"✅ {len(jogadores_criados)} jogadores criados")
    return jogadores_criados


def testar_cenario(nome, quantidade_jogadores):
    """Testa um cenário específico de geração de times"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTE: {nome}")
    print(f"{'='*60}")
    
    Time.objects.all().delete()
    Presenca.objects.all().delete()
    
    todos_jogadores = list(Jogador.objects.all())
    jogadores_selecionados = todos_jogadores[:quantidade_jogadores]
    
    data_teste = date.today()
    
    for jogador in jogadores_selecionados:
        Presenca.objects.create(
            jogador=jogador,
            data=data_teste,
            confirmado=True
        )
    
    print(f"📊 Jogadores confirmados: {len(jogadores_selecionados)}")
    
    try:
        times_gerados = gerar_times_simplificado(jogadores_selecionados, data_teste)
        
        print(f"✅ {len(times_gerados)} times gerados com sucesso!\n")
        
        for i, (titulares, reservas) in enumerate(times_gerados, 1):
            soma_titulares = sum(j.nivel for j in titulares)
            fracos_titulares = sum(1 for j in titulares if j.nivel < 3)
            fracos_total = sum(1 for j in titulares + reservas if j.nivel < 3)
            
            levantadores = [j for j in titulares if j.posicao_preferida == 'levantador']
            liberos = [j for j in titulares if j.posicao_preferida == 'libero']
            
            print(f"⚽ TIME {i}:")
            print(f"   Titulares ({len(titulares)}): {', '.join(f'{j.nome} ({j.nivel})' for j in titulares)}")
            if reservas:
                print(f"   Reservas ({len(reservas)}): {', '.join(f'{j.nome} ({j.nivel})' for j in reservas)}")
            print(f"   📈 Soma níveis: {soma_titulares}")
            print(f"   🎯 Levantadores: {len(levantadores)} | Líberos: {len(liberos)}")
            print(f"   ⚠️  Jogadores nível < 3: {fracos_total} (titulares: {fracos_titulares})")
            print()
        
        somas = [sum(j.nivel for j in titulares) for titulares, _ in times_gerados]
        diferenca = max(somas) - min(somas) if somas else 0
        print(f"📊 RESUMO: Diferença de níveis entre times: {diferenca}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("🏐 TESTE DE GERAÇÃO DE TIMES - ALGORITMO SIMPLIFICADO")
    print("="*60)
    
    jogadores = criar_jogadores_teste()
    
    cenarios = [
        ("20 jogadores (4 times com 4 titulares + 1 reserva)", 20),
        ("16 jogadores (4 times com 4 titulares)", 16),
        ("15 jogadores (3 times com 4 titulares + 3 reservas)", 15),
        ("12 jogadores (3 times com 4 titulares)", 12),
        ("8 jogadores (2 times com 4 titulares)", 8),
    ]
    
    resultados = []
    for nome, qtd in cenarios:
        sucesso = testar_cenario(nome, qtd)
        resultados.append((nome, sucesso))
    
    print("\n" + "="*60)
    print("📋 RESUMO DOS TESTES")
    print("="*60)
    for nome, sucesso in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"{status} - {nome}")
    
    total = len(resultados)
    passou = sum(1 for _, s in resultados if s)
    print(f"\n🎯 Total: {passou}/{total} testes passaram")


if __name__ == '__main__':
    main()
