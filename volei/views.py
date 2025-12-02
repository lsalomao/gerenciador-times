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
    times = Time.objects.all().prefetch_related('jogadores', 'reservas').order_by('-data', 'nome')
    times_por_data = defaultdict(list)
    for time in times:
        times_por_data[time.data].append(time)
    
    return render(request, 'volei/time_list.html', {
        'times_por_data': dict(times_por_data)
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

        if len(jogadores) < 16:
            messages.error(request, f'Necessário pelo menos 16 jogadores confirmados para gerar 4 times. Apenas {len(jogadores)} confirmados.')
            return redirect('time_list')

        if len(jogadores) > 20:
            jogadores_fixos = sorted(
                [j for j in jogadores if j.tipo_jogador == 'fixo'],
                key=lambda x: x.nivel,
                reverse=True
            )
            jogadores_convidados = sorted(
                [j for j in jogadores if j.tipo_jogador == 'convidado'],
                key=lambda x: x.nivel,
                reverse=True
            )

            jogadores_selecionados = (jogadores_fixos + jogadores_convidados)[:20]

            excluidos = len(jogadores) - 20
            messages.warning(
                request,
                f'{len(jogadores)} jogadores confirmados. Selecionados os 20 melhores '
                f'(priorizando fixos). {excluidos} jogador(es) ficaram de fora.'
            )
            jogadores = jogadores_selecionados

        num_times = min(len(jogadores) // 4, 4)

        try:
            times_gerados = equilibrar_times(jogadores, num_times)
        except ValueError as e:
            messages.error(request, f'Erro ao gerar times: {str(e)}')
            return redirect('time_list')

        titulares_apenas = [titulares for titulares, _ in times_gerados]
        score_final, detalhes = calcular_metricas_times(titulares_apenas)

        for i, (titulares, reservas_time) in enumerate(times_gerados, 1):
            time = Time.objects.create(
                data=data_jogo,
                nome=f'Time {i}'
            )
            time.jogadores.set(titulares)
            if reservas_time:
                time.reservas.set(reservas_time)

        score_percentual = int(score_final * 100)
        messages.success(
            request,
            f'{num_times} times gerados com sucesso! '
            f'Score de equilíbrio: {score_percentual}% | '
            f'Diferença de níveis: {detalhes["diferenca_niveis"]} | '
            f'Diversidade: {detalhes["diversidade_media"]} | '
            f'Equilíbrio fixos/convidados: {detalhes["equilibrio_fixos"]}'
        )
        return redirect('time_list')
    
    proximas_datas = Presenca.objects.filter(confirmado=True).values_list('data', flat=True).distinct().order_by('-data')
    
    return render(request, 'volei/gerar_times.html', {
        'proximas_datas': proximas_datas,
        'data_sugerida': date.today()
    })

def validar_jogadores(jogadores):
    erros = []

    if not jogadores:
        erros.append("Nenhum jogador fornecido")
        return erros

    for jogador in jogadores:
        if not hasattr(jogador, 'nivel') or jogador.nivel not in range(1, 6):
            erros.append(f"{jogador.nome}: nível inválido (deve ser entre 1 e 5)")

        if not hasattr(jogador, 'posicao_preferida') or not jogador.posicao_preferida:
            erros.append(f"{jogador.nome}: posição preferida não definida")

        if not hasattr(jogador, 'tipo_jogador') or not jogador.tipo_jogador:
            erros.append(f"{jogador.nome}: tipo de jogador não definido")

    posicoes_validas = set(j.posicao_preferida for j in jogadores if hasattr(j, 'posicao_preferida') and j.posicao_preferida and j.posicao_preferida != 'tantofaz')
    if len(posicoes_validas) < 2:
        erros.append("Necessário pelo menos 2 posições diferentes entre os jogadores (exceto 'tantofaz')")

    return erros


def equilibrar_times(jogadores, num_times):
    """
    Algoritmo para equilibrar times de vôlei.

    Regras:
    - Cada time tem 4 titulares fixos
    - Jogadores restantes são distribuídos como reservas
    - Evita repetir posições preferidas no mesmo time
    - Jogadores "tantofaz" são distribuídos por último

    Exemplos:
    - 20 jogadores → 4 times (4 titulares + 1 reserva cada)
    - 19 jogadores → 4 times (4 titulares cada + 3 reservas distribuídos)
    - 18 jogadores → 4 times (4 titulares cada + 2 reservas distribuídos)
    - 16 jogadores → 4 times (4 titulares cada, sem reservas)
    - 10 jogadores → 2 times (4 titulares + 1 reserva cada)

    Melhorias implementadas:
    1. Snake Draft: Distribui jogadores em padrão serpente (1→2→3→3→2→1)
    2. Balanceamento por nível: Agrupa jogadores por nível antes de distribuir
    3. Balanceamento por posição: Evita repetir posições no mesmo time
    4. Priorização: Jogadores com posição definida antes de "tantofaz"
    5. Otimização por swaps: Após distribuição inicial, tenta trocar jogadores para melhorar equilíbrio
    6. Múltiplas métricas: Considera soma total e desvio padrão entre times
    7. Pré-indexação: Otimiza busca de jogadores por posição (O(1) vs O(n))
    8. Early stopping: Para otimização quando não há melhoria significativa
    """

    erros = validar_jogadores(jogadores)
    if erros:
        raise ValueError("Erros de validação: " + "; ".join(erros))

    logger.info(f"Iniciando geração de {num_times} times com {len(jogadores)} jogadores")

    jogadores_ordenados, jogadores_tantofaz = preparar_jogadores(jogadores)

    times, posicoes_por_time = distribuir_titulares(
        jogadores_ordenados,
        jogadores_tantofaz,
        num_times
    )

    reservas = distribuir_reservas(jogadores_ordenados, jogadores_tantofaz, num_times)

    times = otimizar_times_simulated_annealing(times, max_iteracoes=500)

    logger.info(f"Times gerados com sucesso")

    return list(zip(times, reservas))


def preparar_jogadores(jogadores):
    """
    Separa e ordena jogadores por tipo e posição.

    Retorna:
        jogadores_ordenados: Lista ordenada (fixos com posição → convidados com posição)
        jogadores_tantofaz: Lista ordenada (fixos tantofaz → convidados tantofaz)
    """
    fixos_com_posicao = [j for j in jogadores if j.tipo_jogador == 'fixo' and j.posicao_preferida and j.posicao_preferida != 'tantofaz']
    convidados_com_posicao = [j for j in jogadores if j.tipo_jogador == 'convidado' and j.posicao_preferida and j.posicao_preferida != 'tantofaz']
    fixos_tantofaz = [j for j in jogadores if j.tipo_jogador == 'fixo' and (not j.posicao_preferida or j.posicao_preferida == 'tantofaz')]
    convidados_tantofaz = [j for j in jogadores if j.tipo_jogador == 'convidado' and (not j.posicao_preferida or j.posicao_preferida == 'tantofaz')]

    fixos_por_nivel = defaultdict(list)
    for jogador in fixos_com_posicao:
        fixos_por_nivel[jogador.nivel].append(jogador)

    convidados_por_nivel = defaultdict(list)
    for jogador in convidados_com_posicao:
        convidados_por_nivel[jogador.nivel].append(jogador)

    for nivel in fixos_por_nivel:
        random.shuffle(fixos_por_nivel[nivel])
    for nivel in convidados_por_nivel:
        random.shuffle(convidados_por_nivel[nivel])

    jogadores_ordenados = []
    for nivel in sorted(fixos_por_nivel.keys(), reverse=True):
        jogadores_ordenados.extend(fixos_por_nivel[nivel])
    for nivel in sorted(convidados_por_nivel.keys(), reverse=True):
        jogadores_ordenados.extend(convidados_por_nivel[nivel])

    fixos_tantofaz_ordenados = sorted(fixos_tantofaz, key=lambda j: j.nivel, reverse=True)
    convidados_tantofaz_ordenados = sorted(convidados_tantofaz, key=lambda j: j.nivel, reverse=True)
    jogadores_tantofaz = fixos_tantofaz_ordenados + convidados_tantofaz_ordenados

    logger.debug(f"Jogadores preparados: {len(jogadores_ordenados)} com posição, {len(jogadores_tantofaz)} tantofaz")

    return jogadores_ordenados, jogadores_tantofaz


def distribuir_titulares(jogadores_ordenados, jogadores_tantofaz, num_times):
    """
    Distribui titulares usando Snake Draft com pré-indexação de posições.

    Retorna:
        times: Lista de times com titulares
        posicoes_por_time: Conjunto de posições por time
    """
    times = [[] for _ in range(num_times)]
    posicoes_por_time = [set() for _ in range(num_times)]
    jogadores_por_time = 4

    jogadores_usados = set()
    idx_por_posicao = defaultdict(list)

    for idx, jogador in enumerate(jogadores_ordenados):
        idx_por_posicao[jogador.posicao_preferida].append(idx)

    rodada = 0
    total_distribuidos = 0
    total_necessario = num_times * jogadores_por_time

    while total_distribuidos < total_necessario and (len(jogadores_usados) < len(jogadores_ordenados) or any(len(time) < jogadores_por_time for time in times)):
        ordem_times = range(num_times) if rodada % 2 == 0 else range(num_times - 1, -1, -1)

        for idx_time in ordem_times:
            if len(times[idx_time]) >= jogadores_por_time:
                continue

            jogador_adicionado = False

            for idx_jogador in range(len(jogadores_ordenados)):
                if idx_jogador in jogadores_usados:
                    continue

                jogador = jogadores_ordenados[idx_jogador]

                if jogador.posicao_preferida not in posicoes_por_time[idx_time]:
                    times[idx_time].append(jogador)
                    posicoes_por_time[idx_time].add(jogador.posicao_preferida)
                    jogadores_usados.add(idx_jogador)
                    total_distribuidos += 1
                    logger.debug(f"Time {idx_time+1}: adicionado {jogador.nome} ({jogador.posicao_preferida}, nível {jogador.nivel})")
                    jogador_adicionado = True
                    break

            if not jogador_adicionado:
                for idx_jogador in range(len(jogadores_ordenados)):
                    if idx_jogador in jogadores_usados:
                        continue

                    jogador = jogadores_ordenados[idx_jogador]
                    times[idx_time].append(jogador)
                    posicoes_por_time[idx_time].add(jogador.posicao_preferida)
                    jogadores_usados.add(idx_jogador)
                    total_distribuidos += 1
                    logger.warning(f"Time {idx_time+1}: posição {jogador.posicao_preferida} repetida para {jogador.nome}")
                    jogador_adicionado = True
                    break

            if total_distribuidos >= total_necessario:
                break

        rodada += 1

        if rodada > 100:
            logger.error("Loop infinito detectado na distribuição de titulares")
            break

    idx_tantofaz = 0
    rodada = 0

    while idx_tantofaz < len(jogadores_tantofaz) and any(len(time) < jogadores_por_time for time in times):
        ordem_times = range(num_times) if rodada % 2 == 0 else range(num_times - 1, -1, -1)

        for idx_time in ordem_times:
            if idx_tantofaz >= len(jogadores_tantofaz):
                break
            if len(times[idx_time]) < jogadores_por_time:
                jogador = jogadores_tantofaz[idx_tantofaz]
                times[idx_time].append(jogador)
                logger.debug(f"Time {idx_time+1}: adicionado {jogador.nome} (tantofaz, nível {jogador.nivel})")
                idx_tantofaz += 1
        rodada += 1

    validar_diversidade_minima(times)

    return times, posicoes_por_time


def distribuir_reservas(jogadores_ordenados, jogadores_tantofaz, num_times):
    """
    Distribui jogadores restantes como reservas.

    Retorna:
        reservas: Lista de reservas por time
    """
    reservas = [[] for _ in range(num_times)]
    idx_time_reserva = 0

    titulares_count = num_times * 4

    for idx in range(titulares_count, len(jogadores_ordenados)):
        if idx < len(jogadores_ordenados):
            reservas[idx_time_reserva].append(jogadores_ordenados[idx])
            idx_time_reserva = (idx_time_reserva + 1) % num_times

    tantofaz_usados = min(titulares_count, len(jogadores_ordenados))
    idx_tantofaz = max(0, titulares_count - len(jogadores_ordenados))

    while idx_tantofaz < len(jogadores_tantofaz):
        reservas[idx_time_reserva].append(jogadores_tantofaz[idx_tantofaz])
        idx_time_reserva = (idx_time_reserva + 1) % num_times
        idx_tantofaz += 1

    logger.debug(f"Reservas distribuídas: {sum(len(r) for r in reservas)} jogadores")

    return reservas


def validar_diversidade_minima(times):
    """
    Valida se cada time tem diversidade mínima de posições.
    Lança exceção se algum time tiver menos de 2 posições diferentes.
    """
    for idx, time in enumerate(times):
        posicoes_unicas = set(
            j.posicao_preferida for j in time
            if hasattr(j, 'posicao_preferida') and j.posicao_preferida and j.posicao_preferida != 'tantofaz'
        )
        if len(posicoes_unicas) < 2:
            logger.error(f"Time {idx+1} tem apenas {len(posicoes_unicas)} posição(ões) única(s)")
            raise ValueError(f"Time {idx+1} não possui diversidade mínima de posições (mínimo: 2 posições diferentes)")


def calcular_metricas_times(times):
    """
    Calcula métricas avançadas de equilíbrio dos times.

    Retorna:
        score_final (float): Score composto de 0 a 1 (quanto maior, melhor)
        detalhes (dict): Dicionário com métricas individuais

    Métricas consideradas:
    - 40% equilíbrio de níveis (diferença entre times)
    - 30% diversidade de posições (variedade no time)
    - 20% proporção fixos/convidados (distribuição equilibrada)
    - 10% desvio padrão geral
    """
    if not times or not any(times):
        return 0.0, {}

    # Métrica 1: Equilíbrio de níveis (40%)
    somas = [sum(j.nivel for j in time) for time in times]
    diferenca_niveis = max(somas) - min(somas)
    score_niveis = max(0, 1 - (diferenca_niveis / 10))

    # Métrica 2: Diversidade de posições (30%)
    diversidades = []
    for time in times:
        posicoes_unicas = len(set(
            j.posicao_preferida for j in time
            if hasattr(j, 'posicao_preferida') and j.posicao_preferida and j.posicao_preferida != 'tantofaz'
        ))
        diversidades.append(posicoes_unicas / 4)
    score_posicoes = sum(diversidades) / len(diversidades) if diversidades else 0

    # Métrica 3: Proporção fixos/convidados (20%)
    proporcoes = []
    for time in times:
        if len(time) > 0:
            fixos = sum(1 for j in time if hasattr(j, 'tipo_jogador') and j.tipo_jogador == 'fixo')
            proporcoes.append(fixos / len(time))

    if proporcoes:
        desvio_proporcao = max(proporcoes) - min(proporcoes)
        score_proporcao = max(0, 1 - desvio_proporcao)
    else:
        score_proporcao = 0

    # Métrica 4: Desvio padrão das somas (10%)
    media = sum(somas) / len(somas)
    variancia = sum((s - media) ** 2 for s in somas) / len(somas)
    desvio_padrao = variancia ** 0.5
    score_desvio = max(0, 1 - (desvio_padrao / 5))

    # Score final ponderado
    score_final = (
        0.4 * score_niveis +
        0.3 * score_posicoes +
        0.2 * score_proporcao +
        0.1 * score_desvio
    )

    detalhes = {
        'diferenca_niveis': diferenca_niveis,
        'diversidade_media': round(score_posicoes, 2),
        'equilibrio_fixos': round(score_proporcao, 2),
        'desvio_padrao': round(desvio_padrao, 2),
        'somas_niveis': somas
    }

    return score_final, detalhes


def otimizar_times_simulated_annealing(times, max_iteracoes=500, temperatura_inicial=1.0, taxa_resfriamento=0.95):
    """
    Otimiza o equilíbrio dos times usando Simulated Annealing com early stopping.

    Vantagens sobre swaps simples:
    - Aceita soluções piores temporariamente para escapar de mínimos locais
    - Temperatura controla a probabilidade de aceitar soluções piores
    - Mais eficiente e explora melhor o espaço de soluções
    - Early stopping: para quando não há melhoria significativa

    Parâmetros:
    - max_iteracoes: número máximo de tentativas (padrão: 500)
    - temperatura_inicial: temperatura inicial (controla aceitação de soluções piores)
    - taxa_resfriamento: taxa de redução da temperatura a cada iteração
    """
    import math

    melhor_times = [time[:] for time in times]
    melhor_score, _ = calcular_metricas_times(melhor_times)

    times_atual = [time[:] for time in times]
    score_atual = melhor_score
    temperatura = temperatura_inicial

    iteracoes_sem_melhoria = 0
    limite_early_stopping = 100

    logger.info(f"Iniciando otimização: score inicial = {melhor_score:.4f}")

    for iteracao in range(max_iteracoes):
        i, j = random.sample(range(len(times_atual)), 2)

        if not times_atual[i] or not times_atual[j]:
            continue

        idx_i = random.randint(0, len(times_atual[i]) - 1)
        idx_j = random.randint(0, len(times_atual[j]) - 1)

        times_atual[i][idx_i], times_atual[j][idx_j] = times_atual[j][idx_j], times_atual[i][idx_i]

        novo_score, _ = calcular_metricas_times(times_atual)

        delta = novo_score - score_atual

        if delta > 0 or random.random() < math.exp(delta / temperatura):
            score_atual = novo_score

            if novo_score > melhor_score:
                melhoria = novo_score - melhor_score
                melhor_score = novo_score
                melhor_times = [time[:] for time in times_atual]
                iteracoes_sem_melhoria = 0
                logger.debug(f"Iteração {iteracao}: nova melhor solução = {melhor_score:.4f} (+{melhoria:.4f})")
            else:
                iteracoes_sem_melhoria += 1
        else:
            times_atual[i][idx_i], times_atual[j][idx_j] = times_atual[j][idx_j], times_atual[i][idx_i]
            iteracoes_sem_melhoria += 1

        if iteracoes_sem_melhoria >= limite_early_stopping:
            logger.info(f"Early stopping na iteração {iteracao}: sem melhoria por {limite_early_stopping} iterações")
            break

        temperatura *= taxa_resfriamento

    return melhor_times

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
    )

    status = request.GET.get('status')
    if status:
        partidas = partidas.filter(status=status)

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
        Partida.objects.select_related('time_a', 'time_b', 'vencedor'),
        pk=pk
    )

    eventos = partida.eventos.all().select_related('time')

    context = {
        'partida': partida,
        'eventos': eventos,
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
            messages.success(request, f'Ponto para {time.nome}!')
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
