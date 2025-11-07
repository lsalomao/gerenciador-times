from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from .models import Jogador, Presenca, Time
from .forms import JogadorForm, PresencaFormSet
from datetime import date, timedelta
from collections import defaultdict
import random

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
        
        for i, (titulares, reserva) in enumerate(times_gerados, 1):
            time = Time.objects.create(
                data=data_jogo,
                nome=f'Time {i}'
            )
            time.jogadores.set(titulares)
            if reserva:
                time.reservas.add(reserva)
        
        messages.success(request, f'{num_times} times gerados com sucesso para {data_jogo.strftime("%d/%m/%Y")}!')
        return redirect('time_list')
    
    proximas_datas = Presenca.objects.filter(confirmado=True).values_list('data', flat=True).distinct().order_by('-data')
    
    return render(request, 'volei/gerar_times.html', {
        'proximas_datas': proximas_datas,
        'data_sugerida': date.today()
    })

def equilibrar_times(jogadores, num_times):
    jogadores_por_nivel = defaultdict(list)
    for jogador in jogadores:
        jogadores_por_nivel[jogador.nivel].append(jogador)
    
    for nivel in jogadores_por_nivel:
        random.shuffle(jogadores_por_nivel[nivel])
    
    times = [[] for _ in range(num_times)]
    reservas = [None for _ in range(num_times)]
    
    for nivel in sorted(jogadores_por_nivel.keys(), reverse=True):
        jogadores_nivel = jogadores_por_nivel[nivel]
        
        for jogador in jogadores_nivel:
            somas = [sum(j.nivel for j in time) for time in times]
            
            times_disponiveis = [(i, soma) for i, (time, soma) in enumerate(zip(times, somas)) if len(time) < 4]
            
            if times_disponiveis:
                idx_time = min(times_disponiveis, key=lambda x: x[1])[0]
                times[idx_time].append(jogador)
            else:
                for i, reserva in enumerate(reservas):
                    if reserva is None:
                        reservas[i] = jogador
                        break
    
    return list(zip(times, reservas))

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
