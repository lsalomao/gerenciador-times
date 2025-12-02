from django.test import TestCase
from .models import Jogador
from .views import equilibrar_times, validar_jogadores, calcular_metricas_times


class EquilibrarTimesTestCase(TestCase):

    def criar_jogador(self, nome, nivel, posicao, tipo='fixo'):
        return Jogador.objects.create(
            nome=nome,
            nivel=nivel,
            posicao_preferida=posicao,
            tipo_jogador=tipo,
            ativo=True
        )

    def test_exatamente_16_jogadores(self):
        jogadores = []
        posicoes = ['levantador', 'oposto', 'ponteiro', 'central']

        for i in range(16):
            jogadores.append(self.criar_jogador(
                nome=f'Jogador {i+1}',
                nivel=(i % 5) + 1,
                posicao=posicoes[i % 4],
                tipo='fixo' if i < 8 else 'convidado'
            ))

        times_gerados = equilibrar_times(jogadores, 4)

        self.assertEqual(len(times_gerados), 4)

        for titulares, reservas in times_gerados:
            self.assertEqual(len(titulares), 4)
            self.assertEqual(len(reservas), 0)

    def test_20_jogadores_com_reservas(self):
        jogadores = []
        posicoes = ['levantador', 'oposto', 'ponteiro', 'central']

        for i in range(20):
            jogadores.append(self.criar_jogador(
                nome=f'Jogador {i+1}',
                nivel=(i % 5) + 1,
                posicao=posicoes[i % 4],
                tipo='fixo' if i < 10 else 'convidado'
            ))

        times_gerados = equilibrar_times(jogadores, 4)

        self.assertEqual(len(times_gerados), 4)

        total_titulares = sum(len(titulares) for titulares, _ in times_gerados)
        total_reservas = sum(len(reservas) for _, reservas in times_gerados)

        self.assertEqual(total_titulares, 16)
        self.assertEqual(total_reservas, 4)

    def test_todos_mesma_posicao(self):
        jogadores = []

        for i in range(16):
            jogadores.append(self.criar_jogador(
                nome=f'Jogador {i+1}',
                nivel=(i % 5) + 1,
                posicao='ponteiro',
                tipo='fixo'
            ))

        with self.assertRaises(ValueError) as context:
            equilibrar_times(jogadores, 4)

        self.assertIn('posições diferentes', str(context.exception).lower())

    def test_todos_tantofaz(self):
        jogadores = []

        for i in range(16):
            jogadores.append(self.criar_jogador(
                nome=f'Jogador {i+1}',
                nivel=(i % 5) + 1,
                posicao='tantofaz',
                tipo='fixo' if i < 8 else 'convidado'
            ))

        with self.assertRaises(ValueError) as context:
            equilibrar_times(jogadores, 4)

        self.assertIn('posições diferentes', str(context.exception).lower())

    def test_mix_extremo_niveis(self):
        jogadores = []
        posicoes = ['levantador', 'oposto', 'ponteiro', 'central']

        for i in range(8):
            jogadores.append(self.criar_jogador(
                nome=f'Pro {i+1}',
                nivel=5,
                posicao=posicoes[i % 4],
                tipo='fixo'
            ))

        for i in range(8):
            jogadores.append(self.criar_jogador(
                nome=f'Iniciante {i+1}',
                nivel=1,
                posicao=posicoes[i % 4],
                tipo='convidado'
            ))

        times_gerados = equilibrar_times(jogadores, 4)
        titulares_apenas = [titulares for titulares, _ in times_gerados]

        somas = [sum(j.nivel for j in time) for time in titulares_apenas]
        diferenca = max(somas) - min(somas)

        self.assertLessEqual(diferenca, 4)

    def test_diversidade_posicoes(self):
        jogadores = []
        posicoes = ['levantador', 'oposto', 'ponteiro', 'central']

        for i in range(16):
            jogadores.append(self.criar_jogador(
                nome=f'Jogador {i+1}',
                nivel=(i % 5) + 1,
                posicao=posicoes[i % 4],
                tipo='fixo' if i < 8 else 'convidado'
            ))

        times_gerados = equilibrar_times(jogadores, 4)

        for titulares, _ in times_gerados:
            posicoes_unicas = set(
                j.posicao_preferida for j in titulares
                if j.posicao_preferida and j.posicao_preferida != 'tantofaz'
            )
            self.assertGreaterEqual(len(posicoes_unicas), 2)

    def test_equilibrio_fixos_convidados(self):
        jogadores = []
        posicoes = ['levantador', 'oposto', 'ponteiro', 'central']

        for i in range(16):
            jogadores.append(self.criar_jogador(
                nome=f'Jogador {i+1}',
                nivel=(i % 5) + 1,
                posicao=posicoes[i % 4],
                tipo='fixo' if i < 8 else 'convidado'
            ))

        times_gerados = equilibrar_times(jogadores, 4)

        for titulares, _ in times_gerados:
            fixos = sum(1 for j in titulares if j.tipo_jogador == 'fixo')
            convidados = sum(1 for j in titulares if j.tipo_jogador == 'convidado')

            self.assertGreaterEqual(fixos, 1)
            self.assertGreaterEqual(convidados, 1)

    def test_validacao_nivel_invalido(self):
        jogadores = [
            self.criar_jogador('Jogador 1', 6, 'ponteiro', 'fixo')
        ]

        erros = validar_jogadores(jogadores)
        self.assertTrue(any('nível inválido' in erro for erro in erros))

    def test_metricas_times(self):
        jogadores = []
        posicoes = ['levantador', 'oposto', 'ponteiro', 'central']

        for i in range(16):
            jogadores.append(self.criar_jogador(
                nome=f'Jogador {i+1}',
                nivel=(i % 5) + 1,
                posicao=posicoes[i % 4],
                tipo='fixo' if i < 8 else 'convidado'
            ))

        times_gerados = equilibrar_times(jogadores, 4)
        titulares_apenas = [titulares for titulares, _ in times_gerados]

        score, detalhes = calcular_metricas_times(titulares_apenas)

        self.assertGreater(score, 0)
        self.assertLessEqual(score, 1)
        self.assertIn('diferenca_niveis', detalhes)
        self.assertIn('diversidade_media', detalhes)
        self.assertIn('equilibrio_fixos', detalhes)
