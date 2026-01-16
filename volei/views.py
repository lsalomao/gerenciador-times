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
            f'Variância interna: {detalhes["variancia_interna_media"]} | '
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

        if not hasattr(jogador, 'tipo_jogador') or not jogador.tipo_jogador:
            erros.append(f"{jogador.nome}: tipo de jogador não definido")

    return erros


def equilibrar_times(jogadores, num_times):
    """
    Algoritmo para equilibrar times de vôlei.

    Regras:
    - Cada time tem 4 titulares fixos
    - Jogadores restantes são distribuídos como reservas
    - Evita repetir posições preferidas no mesmo time
    - Jogadores "tantofaz" são distribuídos por último
    - Máximo 1 jogador com nível < 3 por time (titulares + reservas) (titulares + reservas)

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
    9. Restrição de nível: Máximo 1 jogador com nível < 3 por time (incluindo reservas) (incluindo reservas)
    """

    erros = validar_jogadores(jogadores)
    if erros:
        raise ValueError("Erros de validação: " + "; ".join(erros))

    logger.info(f"Iniciando geração de {num_times} times com {len(jogadores)} jogadores")

    jogadores_ordenados, jogadores_tantofaz = preparar_jogadores(jogadores)

    times, posicoes_por_time, jogadores_usados, tantofaz_usados = distribuir_titulares(
        jogadores_ordenados,
        jogadores_tantofaz,
        num_times
    )

    reservas = distribuir_reservas(jogadores_ordenados, jogadores_tantofaz, num_times, jogadores_usados, tantofaz_usados)

    times_completos = [times[i] + reservas[i] for i in range(num_times)]

    times_completos = corrigir_nivel_minimo(times_completos)

    times_completos = balancear_variancia_completa(times_completos)

    times_titulares = [time[:4] for time in times_completos]
    times_reservas = [time[4:] for time in times_completos]

    times_titulares = otimizar_times_simulated_annealing(times_titulares, times_reservas, max_iteracoes=500)

    logger.info(f"Times gerados com sucesso")

    return list(zip(times_titulares, times_reservas))


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

    Regra especial para levantadores:
    - Só pode repetir levantador no mesmo time se todos os times já tiverem pelo menos 1 levantador

    Retorna:
        times: Lista de times com titulares
        posicoes_por_time: Conjunto de posições por time
        jogadores_usados: Conjunto de índices dos jogadores já usados
        tantofaz_usados: Conjunto de índices dos jogadores tantofaz já usados
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

                    if jogador.posicao_preferida == 'levantador':
                        todos_tem_levantador = all('levantador' in posicoes_por_time[t] for t in range(num_times))
                        if not todos_tem_levantador:
                            continue

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

    tantofaz_usados = set()
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
                tantofaz_usados.add(idx_tantofaz)
                logger.debug(f"Time {idx_time+1}: adicionado {jogador.nome} (tantofaz, nível {jogador.nivel})")
                idx_tantofaz += 1
        rodada += 1

    validar_diversidade_minima(times)

    return times, posicoes_por_time, jogadores_usados, tantofaz_usados


def balancear_variancia_completa(times):
    """
    Reduz a variância interna dos times fazendo trocas estratégicas.
    Trabalha com times completos (titulares + reservas).
    Objetivo: evitar times com jogadores muito fortes e muito fracos juntos.
    Respeita a regra de máximo 1 jogador com nível < 3 por time.
    Respeita a regra de levantadores: só repete se todos os times tiverem pelo menos 1.
    """
    max_tentativas = 50
    melhorias = 0

    for tentativa in range(max_tentativas):
        melhor_troca = None
        melhor_reducao = 0

        variancias_antes = []
        for time in times:
            if len(time) > 1:
                niveis = [j.nivel for j in time]
                media = sum(niveis) / len(niveis)
                var = sum((n - media) ** 2 for n in niveis) / len(niveis)
                variancias_antes.append(var)

        variancia_total_antes = sum(variancias_antes)

        for i in range(len(times)):
            for j in range(i + 1, len(times)):
                for idx_i in range(len(times[i])):
                    for idx_j in range(len(times[j])):
                        jogador_i = times[i][idx_i]
                        jogador_j = times[j][idx_j]

                        times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]

                        nivel_baixo_i = sum(1 for jog in times[i] if jog.nivel < 3)
                        nivel_baixo_j = sum(1 for jog in times[j] if jog.nivel < 3)

                        if nivel_baixo_i > 1 or nivel_baixo_j > 1:
                            times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]
                            continue

                        if not validar_regra_levantador(times):
                            times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]
                            continue

                        variancias_depois = []
                        for time in times:
                            if len(time) > 1:
                                niveis = [jog.nivel for jog in time]
                                media = sum(niveis) / len(niveis)
                                var = sum((n - media) ** 2 for n in niveis) / len(niveis)
                                variancias_depois.append(var)

                        variancia_total_depois = sum(variancias_depois)
                        reducao = variancia_total_antes - variancia_total_depois

                        if reducao > melhor_reducao:
                            melhor_reducao = reducao
                            melhor_troca = (i, j, idx_i, idx_j)

                        times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]

        if melhor_troca and melhor_reducao > 0.01:
            i, j, idx_i, idx_j = melhor_troca
            jogador_i = times[i][idx_i]
            jogador_j = times[j][idx_j]
            times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]
            melhorias += 1
            logger.info(f"Balanceamento de variância: {jogador_i.nome} (Time {i+1}) ↔ {jogador_j.nome} (Time {j+1}) - Redução: {melhor_reducao:.3f}")
        else:
            break

    if melhorias > 0:
        logger.info(f"Balanceamento inicial concluído: {melhorias} trocas realizadas")

    return times


def distribuir_reservas(jogadores_ordenados, jogadores_tantofaz, num_times, jogadores_usados, tantofaz_usados):
    """
    Distribui jogadores restantes como reservas.

    Retorna:
        reservas: Lista de reservas por time
    """
    reservas = [[] for _ in range(num_times)]
    idx_time_reserva = 0

    for idx in range(len(jogadores_ordenados)):
        if idx not in jogadores_usados:
            reservas[idx_time_reserva].append(jogadores_ordenados[idx])
            idx_time_reserva = (idx_time_reserva + 1) % num_times

    for idx in range(len(jogadores_tantofaz)):
        if idx not in tantofaz_usados:
            reservas[idx_time_reserva].append(jogadores_tantofaz[idx])
            idx_time_reserva = (idx_time_reserva + 1) % num_times

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


def validar_nivel_minimo(times):
    """
    Valida se cada time tem no máximo 1 jogador com nível menor que 3.
    Retorna True se válido, False caso contrário.
    """
    for idx, time in enumerate(times):
        jogadores_nivel_baixo = sum(1 for j in time if j.nivel < 3)
        if jogadores_nivel_baixo > 1:
            logger.warning(f"Time {idx+1} tem {jogadores_nivel_baixo} jogadores com nível < 3")
            return False
    return True


def validar_regra_levantador(times):
    """
    Valida a regra especial de levantadores:
    - Só pode ter 2+ levantadores no mesmo time se TODOS os times tiverem pelo menos 1 levantador
    Retorna True se válido, False caso contrário.
    """
    levantadores_por_time = []
    for time in times:
        count = sum(1 for j in time if hasattr(j, 'posicao_preferida') and j.posicao_preferida == 'levantador')
        levantadores_por_time.append(count)

    todos_tem_levantador = all(count >= 1 for count in levantadores_por_time)

    for idx, count in enumerate(levantadores_por_time):
        if count > 1 and not todos_tem_levantador:
            logger.warning(f"Time {idx+1} tem {count} levantadores, mas nem todos os times têm pelo menos 1")
            return False

    return True


def corrigir_nivel_minimo(times):
    """
    Corrige times que têm mais de 1 jogador com nível < 3,
    tentando trocar com jogadores de outros times.
    Considera titulares + reservas juntos.
    """
    if validar_nivel_minimo(times) and validar_regra_levantador(times):
        return times

    logger.info("Iniciando correção de distribuição de jogadores com nível < 3")

    max_tentativas = 500
    tentativa = 0
    melhorias = 0

    while (not validar_nivel_minimo(times) or not validar_regra_levantador(times)) and tentativa < max_tentativas:
        tentativa += 1
        troca_realizada = False

        for i in range(len(times)):
            jogadores_baixo_i = sum(1 for j in times[i] if j.nivel < 3)

            if jogadores_baixo_i <= 1:
                continue

            for j in range(len(times)):
                if i == j:
                    continue

                jogadores_baixo_j = sum(1 for jog in times[j] if jog.nivel < 3)

                for idx_i, jogador_i in enumerate(times[i]):
                    if jogador_i.nivel >= 3:
                        continue

                    for idx_j, jogador_j in enumerate(times[j]):
                        if jogador_j.nivel >= 3:
                            times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]

                            novo_baixo_i = sum(1 for jog in times[i] if jog.nivel < 3)
                            novo_baixo_j = sum(1 for jog in times[j] if jog.nivel < 3)

                            if novo_baixo_i < jogadores_baixo_i and novo_baixo_j <= 1:
                                if validar_regra_levantador(times):
                                    logger.info(f"Correção nível: {jogador_i.nome} (Time {i+1}) ↔ {jogador_j.nome} (Time {j+1})")
                                    melhorias += 1
                                    troca_realizada = True
                                    break
                                else:
                                    times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]
                            else:
                                times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]

                    if troca_realizada:
                        break

                if troca_realizada:
                    break

            if troca_realizada:
                break

        if not troca_realizada:
            for i in range(len(times)):
                jogadores_baixo_i = sum(1 for j in times[i] if j.nivel < 3)

                if jogadores_baixo_i <= 1:
                    continue

                for j in range(len(times)):
                    if i == j:
                        continue

                    jogadores_baixo_j = sum(1 for jog in times[j] if jog.nivel < 3)

                    if jogadores_baixo_j >= jogadores_baixo_i:
                        continue

                    for idx_i, jogador_i in enumerate(times[i]):
                        if jogador_i.nivel >= 3:
                            continue

                        for idx_j, jogador_j in enumerate(times[j]):
                            times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]

                            novo_baixo_i = sum(1 for jog in times[i] if jog.nivel < 3)
                            novo_baixo_j = sum(1 for jog in times[j] if jog.nivel < 3)

                            if novo_baixo_i < jogadores_baixo_i and novo_baixo_j < jogadores_baixo_j + 2:
                                if validar_regra_levantador(times):
                                    logger.info(f"Correção flexível: {jogador_i.nome} (Time {i+1}) ↔ {jogador_j.nome} (Time {j+1})")
                                    melhorias += 1
                                    troca_realizada = True
                                    break
                                else:
                                    times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]
                            else:
                                times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]

                        if troca_realizada:
                            break

                    if troca_realizada:
                        break

                if troca_realizada:
                    break

        if not troca_realizada:
            break

    if melhorias > 0:
        logger.info(f"Correção de nível concluída: {melhorias} trocas realizadas")

    if not validar_nivel_minimo(times):
        logger.warning("Não foi possível corrigir completamente a distribuição de jogadores com nível < 3")
        logger.warning("Continuando com a melhor distribuição possível")

    return times


def calcular_metricas_times(times):
    """
    Calcula métricas avançadas de equilíbrio dos times.

    Retorna:
        score_final (float): Score composto de 0 a 1 (quanto maior, melhor)
        detalhes (dict): Dicionário com métricas individuais

    Métricas consideradas:
    - 30% equilíbrio de níveis entre times (diferença de somas)
    - 25% equilíbrio interno dos times (baixa variância dentro de cada time)
    - 20% diversidade de posições (variedade no time)
    - 15% proporção fixos/convidados (distribuição equilibrada)
    - 10% desvio padrão geral entre times
    """
    if not times or not any(times):
        return 0.0, {}

    # Métrica 1: Equilíbrio de níveis entre times (30%)
    somas = [sum(j.nivel for j in time) for time in times]
    diferenca_niveis = max(somas) - min(somas)
    score_niveis = max(0, 1 - (diferenca_niveis / 10))

    # Métrica 2: Equilíbrio interno dos times - penaliza alta variância (25%)
    variancias_internas = []
    for time in times:
        if len(time) > 1:
            niveis = [j.nivel for j in time]
            media_time = sum(niveis) / len(niveis)
            variancia_time = sum((n - media_time) ** 2 for n in niveis) / len(niveis)
            variancias_internas.append(variancia_time)

    if variancias_internas:
        variancia_media = sum(variancias_internas) / len(variancias_internas)
        score_variancia_interna = max(0, 1 - (variancia_media / 2))
    else:
        score_variancia_interna = 1.0

    # Métrica 3: Diversidade de posições (20%)
    diversidades = []
    for time in times:
        posicoes_unicas = len(set(
            j.posicao_preferida for j in time
            if hasattr(j, 'posicao_preferida') and j.posicao_preferida and j.posicao_preferida != 'tantofaz'
        ))
        diversidades.append(posicoes_unicas / 4)
    score_posicoes = sum(diversidades) / len(diversidades) if diversidades else 0

    # Métrica 4: Proporção fixos/convidados (15%)
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

    # Métrica 5: Desvio padrão das somas entre times (10%)
    media = sum(somas) / len(somas)
    variancia = sum((s - media) ** 2 for s in somas) / len(somas)
    desvio_padrao = variancia ** 0.5
    score_desvio = max(0, 1 - (desvio_padrao / 5))

    # Score final ponderado
    score_final = (
        0.30 * score_niveis +
        0.25 * score_variancia_interna +
        0.20 * score_posicoes +
        0.15 * score_proporcao +
        0.10 * score_desvio
    )

    detalhes = {
        'diferenca_niveis': diferenca_niveis,
        'variancia_interna_media': round(variancia_media if variancias_internas else 0, 2),
        'diversidade_media': round(score_posicoes, 2),
        'equilibrio_fixos': round(score_proporcao, 2),
        'desvio_padrao': round(desvio_padrao, 2),
        'somas_niveis': somas
    }

    return score_final, detalhes


def otimizar_times_simulated_annealing(times_titulares, times_reservas, max_iteracoes=500, temperatura_inicial=1.0, taxa_resfriamento=0.95):
    """
    Otimiza o equilíbrio dos times usando Simulated Annealing com early stopping.

    Vantagens sobre swaps simples:
    - Aceita soluções piores temporariamente para escapar de mínimos locais
    - Temperatura controla a probabilidade de aceitar soluções piores
    - Mais eficiente e explora melhor o espaço de soluções
    - Early stopping: para quando não há melhoria significativa
    - Respeita a regra: máximo 1 jogador com nível < 3 por time (titulares + reservas)
    - Respeita a regra de levantadores: só repete se todos os times tiverem pelo menos 1

    Parâmetros:
    - max_iteracoes: número máximo de tentativas (padrão: 500)
    - temperatura_inicial: temperatura inicial (controla aceitação de soluções piores)
    - taxa_resfriamento: taxa de redução da temperatura a cada iteração
    """
    import math

    times_completos = [times_titulares[i] + times_reservas[i] for i in range(len(times_titulares))]

    melhor_times = [time[:] for time in times_titulares]
    melhor_score, _ = calcular_metricas_times(melhor_times)

    times_atual = [time[:] for time in times_titulares]
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

        times_completos_temp = [times_atual[k] + times_reservas[k] for k in range(len(times_atual))]
        if not validar_nivel_minimo(times_completos_temp):
            times_atual[i][idx_i], times_atual[j][idx_j] = times_atual[j][idx_j], times_atual[i][idx_i]
            continue

        if not validar_regra_levantador(times_completos_temp):
            times_atual[i][idx_i], times_atual[j][idx_j] = times_atual[j][idx_j], times_atual[i][idx_i]
            continue

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
