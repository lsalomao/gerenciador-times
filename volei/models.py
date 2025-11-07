from django.db import models

class Jogador(models.Model):
    nome = models.CharField(max_length=100)
    nivel = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
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
