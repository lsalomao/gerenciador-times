from django.core.management.base import BaseCommand
from volei.models import Jogador


class Command(BaseCommand):
    help = 'Cadastra os jogadores fixos no sistema'

    def handle(self, *args, **options):
        jogadores_fixos = [
            "Tati", "Sil", "Ronaldo", "Vini", "Julia", "Lorena", "Clair", "Felipe",
            "Davisson", "Sofia", "Rhyana", "Livia", "Letícia", "Chiquinho", "Camile",
            "Gio", "Leandro", "Campos", "Yuki", "Alexia"
        ]

        self.stdout.write(self.style.SUCCESS('Cadastrando jogadores fixos...'))
        
        for nome in jogadores_fixos:
            jogador, created = Jogador.objects.get_or_create(
                nome=nome,
                defaults={'nivel': 3, 'ativo': True}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Jogador {nome} cadastrado!'))
            else:
                self.stdout.write(self.style.WARNING(f'- Jogador {nome} já existe'))

        total = Jogador.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\nTotal de jogadores cadastrados: {total}'))
