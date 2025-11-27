from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from .models import Jogador, Presenca, Time
from .forms import JogadorForm, PresencaFormSet
from datetime import date, timedelta
from collections import defaultdict
import random
import itertools

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
        
        if len(jogadores) < 10:
            messages.error(request, f'Necessário pelo menos 10 jogadores confirmados. Apenas {len(jogadores)} confirmados.')
            return redirect('time_list')
        
        num_times = len(jogadores) // 5
        if num_times > 4:
            num_times = 4
        
        times_gerados = equilibrar_times(jogadores, num_times)

        for i, (titulares, reservas_time) in enumerate(times_gerados, 1):
            time = Time.objects.create(
                data=data_jogo,
                nome=f'Time {i}'
            )
            time.jogadores.set(titulares)
            if reservas_time:
                time.reservas.set(reservas_time)
        
        messages.success(request, f'{num_times} times gerados com sucesso para {data_jogo.strftime("%d/%m/%Y")}!')
        return redirect('time_list')
    
    proximas_datas = Presenca.objects.filter(confirmado=True).values_list('data', flat=True).distinct().order_by('-data')
    
    return render(request, 'volei/gerar_times.html', {
        'proximas_datas': proximas_datas,
        'data_sugerida': date.today()
    })

def equilibrar_times(jogadores, num_times):
    """
    Algoritmo para equilibrar times de vôlei.

    Regras:
    - Cada time tem 4 titulares fixos
    - Jogadores restantes são distribuídos como reservas

    Exemplos:
    - 20 jogadores → 4 times (4 titulares + 1 reserva cada)
    - 19 jogadores → 4 times (4 titulares cada + 3 reservas distribuídos)
    - 18 jogadores → 4 times (4 titulares cada + 2 reservas distribuídos)
    - 16 jogadores → 4 times (4 titulares cada, sem reservas)
    - 10 jogadores → 2 times (4 titulares + 1 reserva cada)

    Melhorias implementadas:
    1. Snake Draft: Distribui jogadores em padrão serpente (1→2→3→3→2→1)
    2. Balanceamento por nível: Agrupa jogadores por nível antes de distribuir
    3. Otimização por swaps: Após distribuição inicial, tenta trocar jogadores para melhorar equilíbrio
    4. Múltiplas métricas: Considera soma total e desvio padrão entre times
    """

    # Agrupa jogadores por nível
    jogadores_por_nivel = defaultdict(list)
    for jogador in jogadores:
        jogadores_por_nivel[jogador.nivel].append(jogador)

    # Embaralha cada grupo para aleatoriedade
    for nivel in jogadores_por_nivel:
        random.shuffle(jogadores_por_nivel[nivel])

    # Inicializa times e reservas
    times = [[] for _ in range(num_times)]
    reservas = [[] for _ in range(num_times)]
    jogadores_por_time = 4  # 4 titulares por time (fixo)

    # Lista ordenada de jogadores (do maior para o menor nível)
    jogadores_ordenados = []
    for nivel in sorted(jogadores_por_nivel.keys(), reverse=True):
        jogadores_ordenados.extend(jogadores_por_nivel[nivel])

    # Snake Draft: distribui TITULARES em padrão serpente
    idx_jogador = 0
    rodada = 0

    while idx_jogador < len(jogadores_ordenados) and any(len(time) < jogadores_por_time for time in times):
        if rodada % 2 == 0:
            # Ida: 0 → 1 → 2 → 3
            for idx_time in range(num_times):
                if idx_jogador >= len(jogadores_ordenados):
                    break
                if len(times[idx_time]) < jogadores_por_time:
                    times[idx_time].append(jogadores_ordenados[idx_jogador])
                    idx_jogador += 1
        else:
            # Volta: 3 → 2 → 1 → 0
            for idx_time in range(num_times - 1, -1, -1):
                if idx_jogador >= len(jogadores_ordenados):
                    break
                if len(times[idx_time]) < jogadores_por_time:
                    times[idx_time].append(jogadores_ordenados[idx_jogador])
                    idx_jogador += 1
        rodada += 1

    # Distribui RESERVAS (jogadores que sobraram após preencher os titulares)
    idx_time_reserva = 0
    while idx_jogador < len(jogadores_ordenados):
        reservas[idx_time_reserva].append(jogadores_ordenados[idx_jogador])
        idx_time_reserva = (idx_time_reserva + 1) % num_times
        idx_jogador += 1

    # Otimização por swaps: tenta melhorar o equilíbrio trocando jogadores entre times
    times = otimizar_times_com_swaps(times, max_iteracoes=100)

    # Retorna times com suas respectivas reservas
    return list(zip(times, reservas))


def calcular_metricas_times(times):
    """Calcula métricas de equilíbrio dos times."""
    somas = [sum(j.nivel for j in time) for time in times]

    if not somas:
        return 0, 0

    # Diferença entre o time mais forte e o mais fraco
    diferenca_max = max(somas) - min(somas)

    # Desvio padrão das somas
    media = sum(somas) / len(somas)
    variancia = sum((s - media) ** 2 for s in somas) / len(somas)
    desvio_padrao = variancia ** 0.5

    return diferenca_max, desvio_padrao


def otimizar_times_com_swaps(times, max_iteracoes=100):
    """
    Tenta melhorar o equilíbrio dos times trocando jogadores entre eles.

    Estratégia:
    - Tenta trocar 1 jogador entre 2 times
    - Aceita a troca se melhorar as métricas de equilíbrio
    - Repete até não encontrar melhorias ou atingir max_iteracoes
    """
    melhor_times = [time[:] for time in times]  # Cópia profunda
    melhor_diferenca, melhor_desvio = calcular_metricas_times(melhor_times)

    melhorou = True
    iteracoes = 0

    while melhorou and iteracoes < max_iteracoes:
        melhorou = False
        iteracoes += 1

        # Tenta trocar jogadores entre cada par de times
        for i, j in itertools.combinations(range(len(times)), 2):
            # Tenta trocar cada jogador do time i com cada jogador do time j
            for idx_i, jogador_i in enumerate(times[i]):
                for idx_j, jogador_j in enumerate(times[j]):
                    # Faz a troca temporária
                    times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]

                    # Calcula novas métricas
                    nova_diferenca, novo_desvio = calcular_metricas_times(times)

                    # Se melhorou, mantém a troca
                    if nova_diferenca < melhor_diferenca or (nova_diferenca == melhor_diferenca and novo_desvio < melhor_desvio):
                        melhor_diferenca = nova_diferenca
                        melhor_desvio = novo_desvio
                        melhorou = True
                        melhor_times = [time[:] for time in times]
                    else:
                        # Desfaz a troca
                        times[i][idx_i], times[j][idx_j] = times[j][idx_j], times[i][idx_i]

        if melhorou:
            times = [time[:] for time in melhor_times]

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
