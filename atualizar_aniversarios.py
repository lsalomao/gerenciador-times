import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gerenciador_volei.settings')
django.setup()

from volei.models import Jogador
from datetime import date

aniversarios = [
    ("Livia",            date(2000,  1, 14)),
    ("Campos",           date(2000,  1, 10)),
    ("Davisson",         date(2000,  2,  4)),
    ("Felipe",           date(2000,  3, 24)),
    ("Julia",            date(2000,  4, 13)),
    ("Tati",             date(2000,  5, 26)),
    ("Lorena",           date(2000,  7, 15)),
    ("Letícia",          date(2000,  7, 26)),
    ("Rhyana",           date(2000,  8,  3)),
    ("Gio",              date(2000,  8, 11)),
    ("Clair",            date(2000,  8, 28)),
    ("Yuki",             date(2000,  9, 19)),
    ("Leandro Salomão",  date(2000,  9,  7)),
    ("Sofia",            date(2000, 10, 24)),
    ("Silvia",           date(2000, 11,  5)),
    ("Vini",             date(2000, 11, 20)),
    ("Alexia",           date(2000, 12, 18)),
]

print(f"{'Nome informado':<20} {'Jogador encontrado':<30} {'Data':<12} Status")
print("-" * 80)

nao_encontrados = []

for nome, data in aniversarios:
    jogadores = Jogador.objects.filter(nome__icontains=nome)
    if jogadores.count() == 1:
        j = jogadores.first()
        j.data_nascimento = data
        j.save()
        print(f"{nome:<20} {j.nome:<30} {data.strftime('%d/%m/%Y'):<12} OK")
    elif jogadores.count() > 1:
        print(f"{nome:<20} {'MULTIPLOS RESULTADOS':<30} {data.strftime('%d/%m/%Y'):<12} REVISAR")
        for j in jogadores:
            print(f"  -> id={j.id} {j.nome}")
        nao_encontrados.append(nome)
    else:
        print(f"{nome:<20} {'NAO ENCONTRADO':<30} {data.strftime('%d/%m/%Y'):<12} ERRO")
        nao_encontrados.append(nome)

print()
if nao_encontrados:
    print(f"Atenção: {len(nao_encontrados)} jogador(es) não atualizado(s): {', '.join(nao_encontrados)}")
else:
    print("Todos os aniversários foram atualizados com sucesso!")
