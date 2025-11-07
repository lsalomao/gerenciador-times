import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gerenciador_volei.settings')
django.setup()

from volei.models import Jogador

jogadores_fixos = [
    "Tati", "Sil", "Ronaldo", "Vini", "Julia", "Lorena", "Clair", "Felipe",
    "Davisson", "Sofia", "Rhyana", "Livia", "Letícia", "Chiquinho", "Camile",
    "Gio", "Leandro", "Campos", "Yuki", "Alexia"
]

print("Cadastrando jogadores fixos...")
for nome in jogadores_fixos:
    jogador, created = Jogador.objects.get_or_create(
        nome=nome,
        defaults={'nivel': 3, 'ativo': True}
    )
    if created:
        print(f"✓ Jogador {nome} cadastrado!")
    else:
        print(f"- Jogador {nome} já existe")

print(f"\nTotal de jogadores cadastrados: {Jogador.objects.count()}")
