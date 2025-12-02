from django.db import models
from django.utils import timezone

class Jogador(models.Model):
    POSICOES = [
        ('ponta', 'Ponta'),
        ('oposto', 'Oposto'),
        ('levantador', 'Levantador'),
        ('libero', 'Líbero'),
        ('tantofaz', 'Tanto Faz'),
    ]

    TIPO_JOGADOR = [
        ('fixo', 'Fixo'),
        ('convidado', 'Convidado'),
    ]

    nome = models.CharField(max_length=100)
    nivel = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    posicao_preferida = models.CharField(max_length=20, choices=POSICOES, blank=True, null=True)
    tipo_jogador = models.CharField(max_length=20, choices=TIPO_JOGADOR, default='fixo')
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nome} (Nível {self.nivel})"

    class Meta:
        verbose_name_plural = "Jogadores"
        ordering = ['nome']

class Presenca(models.Model):
    jogador = models.ForeignKey(Jogador, on_delete=models.CASCADE)
    data = models.DateField()
    confirmado = models.BooleanField(default=False)

    class Meta:
        unique_together = ('jogador', 'data')
        verbose_name = "Presença"
        verbose_name_plural = "Presenças"
        ordering = ['-data', 'jogador__nome']

    def __str__(self):
        return f"{self.jogador.nome} - {self.data} ({'Confirmado' if self.confirmado else 'Não confirmado'})"

class Time(models.Model):
    data = models.DateField()
    nome = models.CharField(max_length=50)
    jogadores = models.ManyToManyField(Jogador, related_name='times')
    reservas = models.ManyToManyField(Jogador, related_name='reservas', blank=True)

    class Meta:
        ordering = ['-data', 'nome']

    def __str__(self):
        return f"Time {self.nome} - {self.data}"

    def soma_niveis(self):
        return sum(j.nivel for j in self.jogadores.all())


class Partida(models.Model):
    STATUS_CHOICES = [
        ('agendada', 'Agendada'),
        ('em_andamento', 'Em Andamento'),
        ('finalizada', 'Finalizada'),
    ]

    time_a = models.ForeignKey(
        Time,
        on_delete=models.CASCADE,
        related_name='partidas_como_time_a'
    )
    time_b = models.ForeignKey(
        Time,
        on_delete=models.CASCADE,
        related_name='partidas_como_time_b'
    )
    pontos_time_a = models.IntegerField(default=0)
    pontos_time_b = models.IntegerField(default=0)
    vencedor = models.ForeignKey(
        Time,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vitorias'
    )
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='agendada'
    )

    class Meta:
        verbose_name = 'Partida'
        verbose_name_plural = 'Partidas'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.time_a.nome} vs {self.time_b.nome} - {self.status}"

    def verificar_vencedor(self):
        """
        Verifica se há um vencedor conforme as regras:
        - Até 9x9: primeiro a 10 com 2 de diferença
        - A partir de 9x9: primeiro a 12 (sem exigir diferença)

        Returns:
            Time ou None
        """
        a = self.pontos_time_a
        b = self.pontos_time_b

        # Regra especial: a partir de 9x9
        if a >= 9 and b >= 9:
            # Vence quem chegar a 12 primeiro
            if a >= 12:
                return self.time_a
            elif b >= 12:
                return self.time_b
        else:
            # Regra padrão: 10 pontos com 2 de diferença
            if a >= 10 and (a - b) >= 2:
                return self.time_a
            elif b >= 10 and (b - a) >= 2:
                return self.time_b

        return None

    def iniciar(self):
        """Inicia a partida registrando o horário"""
        if self.status == 'agendada':
            self.start_time = timezone.now()
            self.status = 'em_andamento'
            self.save()
            return True
        return False

    def adicionar_ponto(self, time):
        """
        Adiciona um ponto ao time especificado e verifica vitória

        Args:
            time: instância de Time (deve ser time_a ou time_b)

        Returns:
            bool: True se ponto foi adicionado com sucesso
        """
        if self.status != 'em_andamento':
            return False

        if time not in [self.time_a, self.time_b]:
            return False

        # Incrementa pontuação
        if time == self.time_a:
            self.pontos_time_a += 1
        else:
            self.pontos_time_b += 1

        # Cria evento no histórico
        ultimo_evento = self.eventos.last()
        sequencia = (ultimo_evento.sequencia + 1) if ultimo_evento else 1

        EventoPonto.objects.create(
            partida=self,
            time=time,
            sequencia=sequencia
        )

        # Verifica se há vencedor
        vencedor = self.verificar_vencedor()
        if vencedor:
            self.vencedor = vencedor
            self.end_time = timezone.now()
            self.status = 'finalizada'

        self.save()
        return True

    def desfazer_ultimo_ponto(self):
        """
        Remove o último ponto e recalcula o estado da partida

        Returns:
            bool: True se ponto foi removido com sucesso
        """
        ultimo_evento = self.eventos.last()
        if not ultimo_evento:
            return False

        # Decrementa pontuação
        if ultimo_evento.time == self.time_a:
            self.pontos_time_a -= 1
        else:
            self.pontos_time_b -= 1

        # Remove evento
        ultimo_evento.delete()

        # Recalcula vencedor
        vencedor = self.verificar_vencedor()
        if vencedor:
            self.vencedor = vencedor
            self.status = 'finalizada'
        else:
            # Não há mais vencedor, volta para em andamento
            self.vencedor = None
            self.end_time = None
            self.status = 'em_andamento'

        self.save()
        return True

    @property
    def duracao(self):
        """Retorna a duração da partida em formato legível"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            minutos = int(delta.total_seconds() / 60)
            segundos = int(delta.total_seconds() % 60)
            return f"{minutos}min {segundos}s"
        return None

    @property
    def pode_desfazer(self):
        """Verifica se há pontos para desfazer"""
        return self.eventos.exists()


class EventoPonto(models.Model):
    partida = models.ForeignKey(
        Partida,
        on_delete=models.CASCADE,
        related_name='eventos'
    )
    time = models.ForeignKey(
        Time,
        on_delete=models.CASCADE
    )
    sequencia = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento de Ponto'
        verbose_name_plural = 'Eventos de Pontos'
        ordering = ['sequencia']
        unique_together = [('partida', 'sequencia')]

    def __str__(self):
        return f"Ponto #{self.sequencia} - {self.time.nome}"