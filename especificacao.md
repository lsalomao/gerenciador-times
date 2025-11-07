# Especificação do Sistema de Gerenciamento de Times de Vôlei

## Resumo do Projeto

Desenvolver um sistema web responsivo (compatível com celulares) para organizar e equilibrar times de vôlei semanais, considerando o nível dos jogadores.

---

## Tecnologias

- **Framework:** Python Django (backend e frontend, utilizando Django Templates)
- **Banco de Dados:** SQLite
- **Hospedagem:** Servidor próprio, com deploy via Docker (fornecer Dockerfile pronto para produção)

---

## Funcionalidades Principais

1. **Cadastro de Jogadores**
   - Cadastro de nome e nível (1 a 5, avaliado por um organizador).
   - Lista de jogadores ativos e reservas.

2. **Confirmação de Presença**
   - Interface para o organizador marcar quem confirmou presença para o jogo da semana.

3. **Formação Automática de Times**
   - Gerar automaticamente times de 4 titulares e 1 reserva, equilibrando os níveis dos jogadores.
   - O número de times depende do total de confirmados (até 20 pessoas).
   - Algoritmo deve buscar o maior equilíbrio possível entre os times, somando os níveis dos jogadores.

4. **Ajustes Manuais**
   - Permitir ao organizador fazer alterações manuais nos times antes de finalizar.

5. **Gestão de Ausências**
   - Caso algum jogador falte, permitir substituição por outro do mesmo nível (preferencialmente um reserva de outro time).

6. **Interface Responsiva**
   - Utilizar Django Templates com CSS responsivo (Bootstrap ou similar) para garantir boa usabilidade em celulares.

7. **MVP Simples**
   - Para o MVP, considerar apenas o critério de nível para equilibrar os times.
   - Não é necessário histórico de jogos, estatísticas ou controle de posições.

---

## Regras de Negócio

- Cada time deve ter 4 titulares e 1 reserva.
- O sistema deve permitir a visualização dos times formados e dos reservas.
- O organizador pode editar os times antes de confirmar a formação final.
- O sistema deve ser simples, intuitivo e rápido para uso semanal.

---

## Estrutura de Models Django

```python
from django.db import models

class Jogador(models.Model):
    nome = models.CharField(max_length=100)
    nivel = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nome} (Nível {self.nivel})"

class Presenca(models.Model):
    jogador = models.ForeignKey(Jogador, on_delete=models.CASCADE)
    data = models.DateField()
    confirmado = models.BooleanField(default=False)

    class Meta:
        unique_together = ('jogador', 'data')

class Time(models.Model):
    data = models.DateField()
    nome = models.CharField(max_length=50)
    jogadores = models.ManyToManyField(Jogador, related_name='times')
    reservas = models.ManyToManyField(Jogador, related_name='reservas', blank=True)

    def __str__(self):
        return f"Time {self.nome} - {self.data}"