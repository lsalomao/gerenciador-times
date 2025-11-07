from django.contrib import admin
from .models import Jogador, Presenca, Time

@admin.register(Jogador)
class JogadorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'nivel', 'ativo')
    list_filter = ('nivel', 'ativo')
    search_fields = ('nome',)

@admin.register(Presenca)
class PresencaAdmin(admin.ModelAdmin):
    list_display = ('jogador', 'data', 'confirmado')
    list_filter = ('data', 'confirmado')
    search_fields = ('jogador__nome',)
    date_hierarchy = 'data'

@admin.register(Time)
class TimeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data', 'soma_niveis')
    list_filter = ('data',)
    date_hierarchy = 'data'
    filter_horizontal = ('jogadores', 'reservas')
