from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from .models import Jogador, Presenca, Time, Partida
from .forms import JogadorForm, PresencaFormSet, PartidaForm
from datetime import date, timedelta
from collections import defaultdict
import random
import itertools
import logging

logger = logging.getLogger(__name__)

class HomeView(TemplateView):
    template_name = 'volei/home.html'

class JogadorListView(ListView):
    model = Jogador
    template_name = 'volei/jogador_list.html'
    context_object_name = 'jogadores'
    
    def get_queryset(self):
        return Jogador.objects.all().order_by('-ativo', 'nome')

class JogadorCreateView(CreateView):
    model = Jogador
    form_class = JogadorForm
    template_name = 'volei/jogador_form.html'
    success_url = reverse_lazy('jogador_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Novo Jogador'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Jogador cadastrado com sucesso!')
        return super().form_valid(form)

class JogadorUpdateView(UpdateView):
    model = Jogador
    form_class = JogadorForm
    template_name = 'volei/jogador_form.html'
    success_url = reverse_lazy('jogador_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Editar Jogador'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Jogador atualizado com sucesso!')
        return super().form_valid(form)

class JogadorDeleteView(DeleteView):
    model = Jogador
    template_name = 'volei/jogador_confirm_delete.html'
    success_url = reverse_lazy('jogador_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Jogador excluído com sucesso!')
        return super().form_valid(form)

def presenca_list(request):
    presencas = Presenca.objects.filter(confirmado=True).select_related('jogador').order_by('-data')
    presencas_por_data = defaultdict(list)
    for presenca in presencas:
        presencas_por_data[presenca.data].append(presenca)
    
    return render(request, 'volei/presenca_list.html', {
        'presencas_por_data': dict(presencas_por_data)
    })

def gerenciar_presencas(request):
    data_selecionada = date.today()
    
    if request.method == 'POST':
        data_str = request.POST.get('data')
        if data_str:
            data_selecionada = date.fromisoformat(data_str)
        
        jogadores_ativos = Jogador.objects.filter(ativo=True)
        
        for jogador in jogadores_ativos:
            checkbox_name = f'jogador_{jogador.id}'
            confirmado = checkbox_name in request.POST
            
            Presenca.objects.update_or_create(
                jogador=jogador,
                data=data_selecionada,
                defaults={'confirmado': confirmado}
            )
        
        messages.success(request, f'Presenças atualizadas para {data_selecionada.strftime("%d/%m/%Y")}!')
        return redirect('presenca_list')
    
    jogadores = Jogador.objects.filter(ativo=True).order_by('nome')
    presencas_existentes = Presenca.objects.filter(data=data_selecionada, confirmado=True)
    presentes = [p.jogador.id for p in presencas_existentes]
    
    return render(request, 'volei/gerenciar_presencas.html', {
        'jogadores': jogadores,
        'data_selecionada': data_selecionada,
        'presentes': presentes
    })

def time_list(request):
    data_selecionada = request.GET.get('data')

    if data_selecionada:
        try:
            data_filtro = date.fromisoformat(data_selecionada)
        except ValueError:
            data_filtro = date.today()
    else:
        data_filtro = date.today()

    times = Time.objects.filter(data=data_filtro).prefetch_related('jogadores', 'reservas').order_by('nome')

    return render(request, 'volei/time_list.html', {
        'times': times,
        'data_selecionada': data_filtro
    })

def gerar_times(request):
    if request.method == 'POST':
        data_str = request.POST.get('data')
        if not data_str:
            messages.error(request, 'Por favor, selecione uma data.')
            return redirect('time_list')

        data_jogo = date.fromisoformat(data_str)

        Time.objects.filter(data=data_jogo).delete()

        jogadores_confirmados = list(
            Presenca.objects.filter(data=data_jogo, confirmado=True)
            .select_related('jogador')
            .values_list('jogador', flat=True)
        )

        jogadores = list(Jogador.objects.filter(id__in=jogadores_confirmados))

        if len(jogadores) < 4:
            messages.error(request, f'Necessário pelo menos 4 jogadores confirmados para gerar times. Apenas {len(jogadores)} confirmados.')
            return redirect('time_list')

        if len(jogadores) > 20:
            jogadores = selecionar_jogadores(jogadores, max_jogadores=20)
            excluidos = len(Jogador.objects.filter(id__in=jogadores_confirmados)) - 20
            messages.warning(
                request,
                f'{len(Jogador.objects.filter(id__in=jogadores_confirmados))} jogadores confirmados. Selecionados os 20 melhores '
                f'(priorizando fixos). {excluidos} jogador(es) ficaram de fora.'
            )

        num_times = min(len(jogadores) // 4, 4)

        try:
            times_gerados = gerar_times_simplificado(jogadores, data_jogo)
        except ValueError as e:
            messages.error(request, f'Erro ao gerar times: {str(e)}')
            return redirect('time_list')

        for i, (titulares, reservas_time) in enumerate(times_gerados, 1):
            time = Time.objects.create(
                data=data_jogo,
                nome=f'Time {i}'
            )
            time.jogadores.set(titulares)
            if reservas_time:
                time.reservas.set(reservas_time)

        titulares_apenas = [titulares for titulares, _ in times_gerados]
        somas = [sum(j.nivel for j in time) for time in titulares_apenas]
        diferenca_niveis = max(somas) - min(somas) if somas else 0

        messages.success(
            request,
            f'{num_times} times gerados com sucesso! | '
            f'Diferença de níveis: {diferenca_niveis}'
        )
        return redirect('time_list')

    proximas_datas = Presenca.objects.filter(confirmado=True).values_list('data', flat=True).distinct().order_by('-data')

    return render(request, 'volei/gerar_times.html', {
        'proximas_datas': proximas_datas,
        'data_sugerida': date.today()
    })
def selecionar_jogadores(jogadores, max_jogadores=20):
    """
    Seleciona até max_jogadores, priorizando fixos sobre convidados.
    Dentro de cada tipo, ordena por nível decrescente.
    """
    if len(jogadores) <= max_jogadores:
        return jogadores

    fixos = sorted(
        [j for j in jogadores if j.tipo_jogador == 'fixo'],
        key=lambda x: x.nivel,
        reverse=True
    )
    convidados = sorted(
        [j for j in jogadores if j.tipo_jogador == 'convidado'],
        key=lambda x: x.nivel,
        reverse=True
    )

    jogadores_selecionados = (fixos + convidados)[:max_jogadores]

    logger.info(f"Selecionados {len(jogadores_selecionados)} de {len(jogadores)} jogadores")

    return jogadores_selecionados


def separar_por_categoria(jogadores):
    """
    Separa jogadores em categorias para distribuição.

    Retorna dict com:
    - levantadores: lista de levantadores (todos os níveis)
    - liberos: lista de líberos (todos os níveis)
    - fixos_por_nivel: dict {nivel: [jogadores]}
    - convidados_por_nivel: dict {nivel: [jogadores]}
    """
    levantadores = []
    liberos = []
    fixos_por_nivel = defaultdict(list)
    convidados_por_nivel = defaultdict(list)

    for jogador in jogadores:
        if jogador.posicao_preferida == 'levantador':
            levantadores.append(jogador)
        elif jogador.posicao_preferida == 'libero':
            liberos.append(jogador)
        elif jogador.tipo_jogador == 'fixo':
            fixos_por_nivel[jogador.nivel].append(jogador)
        else:
            convidados_por_nivel[jogador.nivel].append(jogador)

    random.shuffle(levantadores)
    random.shuffle(liberos)

    for nivel in fixos_por_nivel:
        random.shuffle(fixos_por_nivel[nivel])
    for nivel in convidados_por_nivel:
        random.shuffle(convidados_por_nivel[nivel])

    logger.info(f"Categorias: {len(levantadores)} levantadores, {len(liberos)} líberos")

    return {
        'levantadores': levantadores,
        'liberos': liberos,
        'fixos_por_nivel': fixos_por_nivel,
        'convidados_por_nivel': convidados_por_nivel
    }


def distribuir_snake_draft(jogadores_ordenados, num_times, jogadores_por_time=4):
    """
    Distribui jogadores priorizando equilíbrio de soma de níveis.
    Cada jogador vai para o time com menor soma atual (greedy).
    Jogadores devem estar ordenados por nível decrescente.
    """
    times = [[] for _ in range(num_times)]

    for jogador in jogadores_ordenados:
        times_com_vaga = [i for i in range(num_times) if len(times[i]) < jogadores_por_time]
        if not times_com_vaga:
            break
        idx_time = min(times_com_vaga, key=lambda i: sum(j.nivel for j in times[i]))
        times[idx_time].append(jogador)
        logger.debug(f"Time {idx_time+1}: {jogador.nome} (nível {jogador.nivel})")

    return times


def distribuir_reservas_round_robin(jogadores_restantes, times):
    """
    Distribui jogadores restantes como reservas usando round-robin.
    """
    idx_time = 0
    for jogador in jogadores_restantes:
        times[idx_time].append(jogador)
        logger.debug(f"Reserva Time {idx_time+1}: {jogador.nome} (nível {jogador.nivel})")
        idx_time = (idx_time + 1) % len(times)

    return times


def validar_e_corrigir_nivel_minimo(times):
    """
    Garante que jogadores com nível < 3 sejam distribuídos:
    1. Identifica times com 2+ jogadores fracos
    2. Tenta trocar jogador fraco por jogador forte de outro time
    3. Se não conseguir corrigir, aceita e loga warning
    """
    max_tentativas = 50

    for tentativa in range(max_tentativas):
        times_com_excesso = []
        times_sem_excesso = []

        for idx, time in enumerate(times):
            count_fracos = sum(1 for j in time if j.nivel < 3)
            if count_fracos > 1:
                times_com_excesso.append((idx, count_fracos))
            else:
                times_sem_excesso.append(idx)

        if not times_com_excesso:
            logger.info(f"Distribuição de jogadores com nível < 3 está adequada")
            return times

        troca_realizada = False

        for idx_excesso, count_fracos in times_com_excesso:
            time_excesso = times[idx_excesso]

            for idx_jogador_fraco, jogador_fraco in enumerate(time_excesso):
                if jogador_fraco.nivel >= 3:
                    continue

                for idx_outro in times_sem_excesso:
                    time_outro = times[idx_outro]
                    count_fracos_outro = sum(1 for j in time_outro if j.nivel < 3)

                    if count_fracos_outro >= 1:
                        continue

                    for idx_jogador_forte, jogador_forte in enumerate(time_outro):
                        if jogador_forte.nivel < 3:
                            continue

                        time_excesso[idx_jogador_fraco], time_outro[idx_jogador_forte] = \
                            time_outro[idx_jogador_forte], time_excesso[idx_jogador_fraco]

                        novo_count_excesso = sum(1 for j in time_excesso if j.nivel < 3)
                        novo_count_outro = sum(1 for j in time_outro if j.nivel < 3)

                        if novo_count_excesso <= 1 and novo_count_outro <= 1:
                            logger.info(f"Troca: {jogador_fraco.nome} (Time {idx_excesso+1}) ↔ {jogador_forte.nome} (Time {idx_outro+1})")
                            troca_realizada = True
                            break
                        else:
                            time_excesso[idx_jogador_fraco], time_outro[idx_jogador_forte] = \
                                time_outro[idx_jogador_forte], time_excesso[idx_jogador_fraco]

                    if troca_realizada:
                        break

                if troca_realizada:
                    break

            if troca_realizada:
                break

        if not troca_realizada:
            break

    for idx, time in enumerate(times):
        count_fracos = sum(1 for j in time if j.nivel < 3)
        if count_fracos > 1:
            logger.warning(f"Time {idx+1} tem {count_fracos} jogadores com nível < 3")

    return times


def gerar_times_simplificado(jogadores_confirmados, data_jogo):
    logger.info(f"Iniciando geração simplificada com {len(jogadores_confirmados)} jogadores")

    jogadores = selecionar_jogadores(jogadores_confirmados, max_jogadores=20)

    num_times = min(len(jogadores) // 4, 4)
    if num_times == 0:
        raise ValueError("Necessário pelo menos 4 jogadores para formar 1 time")

    logger.info(f"Gerando {num_times} times")

    levantadores = sorted([j for j in jogadores if j.posicao_preferida == 'levantador'], key=lambda j: j.nivel, reverse=True)
    liberos = sorted([j for j in jogadores if j.posicao_preferida == 'libero'], key=lambda j: j.nivel, reverse=True)
    outros = sorted([j for j in jogadores if j.posicao_preferida not in ('levantador', 'libero')], key=lambda j: j.nivel, reverse=True)

    times = [[] for _ in range(num_times)]
    reservas = []

    def soma_time(i):
        return sum(j.nivel for j in times[i])

    for jogador in levantadores:
        times_sem_levantador = [i for i in range(num_times) if not any(j.posicao_preferida == 'levantador' for j in times[i])]
        if times_sem_levantador:
            idx = min(times_sem_levantador, key=soma_time)
            times[idx].append(jogador)
        else:
            reservas.append(jogador)

    for jogador in liberos:
        times_sem_libero = [i for i in range(num_times) if not any(j.posicao_preferida == 'libero' for j in times[i])]
        if times_sem_libero:
            idx = min(times_sem_libero, key=soma_time)
            times[idx].append(jogador)
        else:
            reservas.append(jogador)

    for jogador in outros:
        times_com_vaga = [i for i in range(num_times) if len(times[i]) < 4]
        if times_com_vaga:
            idx = min(times_com_vaga, key=soma_time)
            times[idx].append(jogador)
        else:
            reservas.append(jogador)

    for jogador in reservas:
        idx = min(range(num_times), key=lambda i: len(times[i]))
        times[idx].append(jogador)

    times = validar_e_corrigir_nivel_minimo(times)

    times_titulares = [time[:4] for time in times]
    times_reservas = [time[4:] for time in times]

    for i, (titulares, res) in enumerate(zip(times_titulares, times_reservas), 1):
        soma = sum(j.nivel for j in titulares)
        logger.info(f"Time {i}: {len(titulares)} titulares + {len(res)} reservas | Soma níveis: {soma}")

    return list(zip(times_titulares, times_reservas))

def editar_time(request, pk):
    time = get_object_or_404(Time, pk=pk)
    
    if request.method == 'POST':
        jogadores_ids = request.POST.getlist('jogadores')
        reservas_ids = request.POST.getlist('reservas')
        
        time.jogadores.set(jogadores_ids)
        time.reservas.set(reservas_ids)
        
        messages.success(request, 'Time atualizado com sucesso!')
        return redirect('time_list')
    
    jogadores_disponiveis = Jogador.objects.filter(
        id__in=Presenca.objects.filter(data=time.data, confirmado=True).values_list('jogador_id', flat=True)
    )
    
    return render(request, 'volei/editar_time.html', {
        'time': time,
        'jogadores_disponiveis': jogadores_disponiveis
    })

def excluir_time(request, pk):
    time = get_object_or_404(Time, pk=pk)
    data = time.data
    
    if request.method == 'POST':
        time.delete()
        messages.success(request, 'Time excluído com sucesso!')
        return redirect('time_list')
    
    return render(request, 'volei/time_confirm_delete.html', {'time': time})


def listar_partidas(request):
    """Lista todas as partidas com filtros opcionais"""
    hoje = date.today()

    partidas = Partida.objects.filter(
        start_time__date=hoje
    ).select_related(
        'time_a', 'time_b', 'vencedor'
    ).prefetch_related(
        'time_a__jogadores', 'time_b__jogadores'
    )

    status = request.GET.get('status')
    if status:
        partidas = partidas.filter(status=status)

    for partida in partidas:
        primeiro_jogador_a = partida.time_a.jogadores.first()
        partida.time_a_display = f"{partida.time_a.nome} - {primeiro_jogador_a.nome}" if primeiro_jogador_a else partida.time_a.nome

        primeiro_jogador_b = partida.time_b.jogadores.first()
        partida.time_b_display = f"{partida.time_b.nome} - {primeiro_jogador_b.nome}" if primeiro_jogador_b else partida.time_b.nome

    context = {
        'partidas': partidas,
        'status_atual': status,
    }
    return render(request, 'volei/partidas/listar.html', context)


def criar_partida(request):
    """Cria uma nova partida"""
    if request.method == 'POST':
        form = PartidaForm(request.POST)
        if form.is_valid():
            partida = form.save()
            messages.success(request, 'Partida criada com sucesso!')
            return redirect('detalhe_partida', pk=partida.pk)
    else:
        form = PartidaForm()

    context = {
        'form': form,
    }
    return render(request, 'volei/partidas/criar.html', context)


def detalhe_partida(request, pk):
    """Exibe o placar e controles da partida"""
    partida = get_object_or_404(
        Partida.objects.select_related('time_a', 'time_b', 'vencedor').prefetch_related('time_a__jogadores', 'time_b__jogadores'),
        pk=pk
    )

    eventos = partida.eventos.all().select_related('time')

    primeiro_jogador_a = partida.time_a.jogadores.first()
    time_a_display = f"{partida.time_a.nome} - {primeiro_jogador_a.nome}" if primeiro_jogador_a else partida.time_a.nome

    primeiro_jogador_b = partida.time_b.jogadores.first()
    time_b_display = f"{partida.time_b.nome} - {primeiro_jogador_b.nome}" if primeiro_jogador_b else partida.time_b.nome

    context = {
        'partida': partida,
        'eventos': eventos,
        'time_a_display': time_a_display,
        'time_b_display': time_b_display,
    }
    return render(request, 'volei/partidas/detalhe.html', context)


def iniciar_partida(request, pk):
    """Inicia uma partida agendada"""
    if request.method != 'POST':
        return redirect('detalhe_partida', pk=pk)

    partida = get_object_or_404(Partida, pk=pk)

    if partida.iniciar():
        messages.success(request, 'Partida iniciada!')
    else:
        messages.error(request, 'Não foi possível iniciar a partida.')

    return redirect('detalhe_partida', pk=pk)


def adicionar_ponto(request, pk, time_id):
    """Adiciona um ponto ao time especificado"""
    if request.method != 'POST':
        return redirect('detalhe_partida', pk=pk)

    partida = get_object_or_404(Partida, pk=pk)
    time = get_object_or_404(Time, pk=time_id)

    if partida.adicionar_ponto(time):
        if partida.status == 'finalizada':
            messages.success(
                request,
                f'Partida finalizada! Vencedor: {partida.vencedor.nome}'
            )
    else:
        messages.error(request, 'Não foi possível adicionar o ponto.')

    return redirect('detalhe_partida', pk=pk)


def desfazer_ponto(request, pk):
    """Desfaz o último ponto registrado"""
    if request.method != 'POST':
        return redirect('detalhe_partida', pk=pk)

    partida = get_object_or_404(Partida, pk=pk)

    if partida.desfazer_ultimo_ponto():
        messages.success(request, 'Último ponto desfeito!')
    else:
        messages.error(request, 'Não há pontos para desfazer.')

    return redirect('detalhe_partida', pk=pk)


def terminar_dia(request):
    """Finaliza todas as partidas do dia e gera relatório de resultados"""
    hoje = date.today()

    partidas_abertas = Partida.objects.filter(
        start_time__date=hoje,
        status__in=['agendada', 'em_andamento']
    )

    for partida in partidas_abertas:
        if partida.status == 'em_andamento':
            if partida.pontos_time_a > partida.pontos_time_b:
                partida.vencedor = partida.time_a
            elif partida.pontos_time_b > partida.pontos_time_a:
                partida.vencedor = partida.time_b

        partida.status = 'finalizada'
        if not partida.end_time:
            from django.utils import timezone
            partida.end_time = timezone.now()
        partida.save()

    partidas_finalizadas = Partida.objects.filter(
        start_time__date=hoje,
        status='finalizada'
    ).select_related('time_a', 'time_b', 'vencedor')

    times_stats = {}

    for partida in partidas_finalizadas:
        for time in [partida.time_a, partida.time_b]:
            if time.id not in times_stats:
                times_stats[time.id] = {
                    'time': time,
                    'jogos': 0,
                    'vitorias': 0,
                    'derrotas': 0,
                    'pontos_feitos': 0,
                    'pontos_sofridos': 0
                }

            times_stats[time.id]['jogos'] += 1

            if time == partida.time_a:
                times_stats[time.id]['pontos_feitos'] += partida.pontos_time_a
                times_stats[time.id]['pontos_sofridos'] += partida.pontos_time_b
                if partida.vencedor == time:
                    times_stats[time.id]['vitorias'] += 1
                else:
                    times_stats[time.id]['derrotas'] += 1
            else:
                times_stats[time.id]['pontos_feitos'] += partida.pontos_time_b
                times_stats[time.id]['pontos_sofridos'] += partida.pontos_time_a
                if partida.vencedor == time:
                    times_stats[time.id]['vitorias'] += 1
                else:
                    times_stats[time.id]['derrotas'] += 1

    for stats in times_stats.values():
        if stats['jogos'] > 0:
            stats['percentual_vitorias'] = (stats['vitorias'] / stats['jogos']) * 100
        else:
            stats['percentual_vitorias'] = 0
        stats['saldo'] = stats['pontos_feitos'] - stats['pontos_sofridos']

    ranking = sorted(
        times_stats.values(),
        key=lambda x: (x['vitorias'], x['percentual_vitorias'], x['pontos_feitos']),
        reverse=True
    )

    messages.success(request, f'{len(partidas_abertas)} partida(s) finalizada(s) com sucesso!')

    context = {
        'ranking': ranking,
        'data': hoje,
        'total_partidas': len(partidas_finalizadas)
    }

    return render(request, 'volei/partidas/relatorio_dia.html', context)
