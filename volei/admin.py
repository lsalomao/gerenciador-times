from django.contrib import admin
from .models import Jogador, Presenca, Time, Partida, EventoPonto

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


class EventoPontoInline(admin.TabularInline):
    model = EventoPonto
    extra = 0
    readonly_fields = ('sequencia', 'timestamp')
    can_delete = False


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status', 'pontos_time_a', 'pontos_time_b', 'vencedor', 'start_time')
    list_filter = ('status', 'start_time')
    search_fields = ('time_a__nome', 'time_b__nome')
    date_hierarchy = 'start_time'
    readonly_fields = ('pontos_time_a', 'pontos_time_b', 'vencedor', 'start_time', 'end_time')
    inlines = [EventoPontoInline]

    fieldsets = (
        ('Times', {
            'fields': ('time_a', 'time_b')
        }),
        ('Status da Partida', {
            'fields': ('status', 'pontos_time_a', 'pontos_time_b', 'vencedor')
        }),
        ('Horários', {
            'fields': ('start_time', 'end_time')
        }),
    )


@admin.register(EventoPonto)
class EventoPontoAdmin(admin.ModelAdmin):
    list_display = ('partida', 'time', 'sequencia', 'timestamp')
    list_filter = ('timestamp', 'time')
    search_fields = ('partida__time_a__nome', 'partida__time_b__nome', 'time__nome')
    date_hierarchy = 'timestamp'
    readonly_fields = ('sequencia', 'timestamp')
