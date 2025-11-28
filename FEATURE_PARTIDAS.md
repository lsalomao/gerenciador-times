# Feature: Partidas e Placar (Ponto a Ponto)

## Resumo

Sistema completo para registro de partidas de vôlei com placar ponto a ponto em tempo real, determinação automática do vencedor conforme regras específicas e histórico para relatórios futuros.

---

## Regras do Jogo (Simplificadas)

### Formato Básico
- Partida em **set único** até 12 pontos
- Não há controle de sets múltiplos
- Não há controle de pausas ou tempos técnicos

### Regras de Vitória

#### Até 11x11
- Vence quem atingir **12 pontos primeiro**
- **Obrigatório ter 2 pontos de diferença**
- Exemplos:
  - 12x10 → Time com 12 vence
  - 12x11 → Jogo continua (diferença de apenas 1)
  - 13x11 → Time com 13 vence

#### A partir de 11x11 (Regra Especial)
- Quando o placar chega a **11x11**, a regra muda
- Vence quem chegar a **14 pontos primeiro**
- **Não há mais obrigação de 2 pontos de diferença**
- Exemplos:
  - 11x11 → Jogo continua
  - 14x11 → Time com 14 vence
  - 14x13 → Time com 14 vence
  - 13x13 → Jogo continua

---

## Funcionalidades

### 1. Criação de Partida

**Tela:** `/partidas/nova/`

**Campos:**
- Seleção do Time A (dropdown com times cadastrados)
- Seleção do Time B (dropdown com times cadastrados)

**Validações:**
- Time A e Time B devem ser diferentes
- Ambos os times devem existir no sistema

**Comportamento:**
- Cria partida com status `agendada`
- Placar inicial: 0x0
- Sem vencedor definido
- Sem horários registrados

---

### 2. Listagem de Partidas

**Tela:** `/partidas/`

**Exibição:**
- Lista todas as partidas do sistema
- Informações por partida:
  - Times envolvidos (Time A vs Time B)
  - Placar atual
  - Status (em andamento, finalizada)
  - Vencedor (se finalizada)
  - Data/hora de início (se iniciada)

**Filtros:**
- Por status (em andamento, finalizada)
- Por time específico
- Por data

**Ações:**
- Link para criar nova partida
- Link para detalhe/placar de cada partida

---

### 3. Tela de Placar (Principal)

**Tela:** `/partidas/<id>/`

#### Layout

```
┌─────────────────────────────────────────┐
│         PARTIDA - [STATUS]              │
├─────────────────────────────────────────┤
│                                         │
│   TIME A              vs      TIME B    │
│   [Nome]                      [Nome]    │
│                                         │
│     12                          10      │
│   ████████                    ██████    │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  [+1 Time A]            [+1 Time B]     │
│                                         │
│         [Desfazer Último Ponto]         │
│                                         │
│         [Iniciar Partida]               │
│                                         │
├─────────────────────────────────────────┤
│  Início: 14:30:00                       │
│  Término: --:--:--                      │
│  Vencedor: ---                          │
└─────────────────────────────────────────┘
```

#### Elementos da Interface

**Cabeçalho:**
- Título "PARTIDA"
- Status atual (badge colorido)
  - Agendada: cinza
  - Em Andamento: verde
  - Finalizada: azul

**Área de Times:**
- Nome do Time A (esquerda)
- "vs" centralizado
- Nome do Time B (direita)

**Placar:**
- Pontos do Time A (grande, destaque)
- Pontos do Time B (grande, destaque)
- Barra visual de progresso (opcional)
- Destaque para o time que está vencendo

**Botões de Ação:**

1. **Botão "Iniciar Partida"**
   - Visível apenas quando status = `agendada`
   - Cor: verde
   - Ação: POST para `/partidas/<id>/iniciar/`

2. **Botões "+1 Ponto"**
   - Dois botões: um para cada time
   - Visíveis apenas quando status = `em_andamento`
   - Grandes e fáceis de tocar (mobile-friendly)
   - Cor: azul
   - Ação: POST para `/partidas/<id>/ponto/<time_id>/`

3. **Botão "Desfazer Último Ponto"**
   - Visível apenas quando status = `em_andamento`
   - Cor: amarelo/laranja
   - Ação: POST para `/partidas/<id>/desfazer/`
   - Desabilitado se não houver pontos registrados

**Informações da Partida:**
- Horário de início (se iniciada)
- Horário de término (se finalizada)
- Vencedor (se finalizada)
- Duração total (se finalizada)

**Histórico de Pontos (Opcional):**
- Lista cronológica de todos os pontos
- Formato: "Ponto #1 - Time A - 14:32:15"
- Rolável se muitos pontos

---

### 4. Fluxo de Uso

#### Cenário 1: Partida Completa

1. **Criar Partida**
   - Organizador acessa `/partidas/nova/`
   - Seleciona Time A e Time B
   - Clica em "Criar"
   - Sistema cria partida com status `agendada`

2. **Iniciar Partida**
   - Organizador acessa `/partidas/<id>/`
   - Clica em "Iniciar Partida"
   - Sistema:
     - Registra `start_time` (data/hora atual)
     - Altera status para `em_andamento`
     - Exibe botões de pontuação

3. **Registrar Pontos**
   - Organizador clica em "+1 Time A" ou "+1 Time B"
   - Sistema:
     - Incrementa placar
     - Cria registro em EventoPonto
     - Verifica regras de vitória
     - Atualiza interface em tempo real

4. **Fim Automático**
   - Quando um time atinge condição de vitória
   - Sistema automaticamente:
     - Registra `end_time`
     - Define `vencedor`
     - Altera status para `finalizada`
     - Desabilita botões de pontuação
     - Exibe mensagem de vitória

#### Cenário 2: Desfazer Ponto

1. Organizador percebe erro no placar
2. Clica em "Desfazer Último Ponto"
3. Sistema:
   - Remove último EventoPonto
   - Decrementa placar do time correto
   - Recalcula condição de vitória
   - Se estava finalizada e não há mais vencedor:
     - Remove `end_time`
     - Remove `vencedor`
     - Volta status para `em_andamento`
     - Reabilita botões de pontuação

---

## Implementação Técnica

### Models Django

#### Model: Partida

```python
from django.db import models
from django.utils import timezone

class Partida(models.Model):
    STATUS_CHOICES = [
        ('em_andamento', 'Em Andamento'),
        ('finalizada', 'Finalizada'),
    ]
    
    time_a = models.ForeignKey(
        'Time', 
        on_delete=models.CASCADE, 
        related_name='partidas_como_time_a'
    )
    time_b = models.ForeignKey(
        'Time', 
        on_delete=models.CASCADE, 
        related_name='partidas_como_time_b'
    )
    pontos_time_a = models.IntegerField(default=0)
    pontos_time_b = models.IntegerField(default=0)
    vencedor = models.ForeignKey(
        'Time', 
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
        - Até 11x11: primeiro a 12 com 2 de diferença
        - A partir de 11x11: primeiro a 14 (sem exigir diferença)
        
        Returns:
            Time ou None
        """
        a = self.pontos_time_a
        b = self.pontos_time_b
        
        # Regra especial: a partir de 11x11
        if a >= 11 and b >= 11:
            # Vence quem chegar a 14 primeiro
            if a >= 14:
                return self.time_a
            elif b >= 14:
                return self.time_b
        else:
            # Regra padrão: 12 pontos com 2 de diferença
            if a >= 12 and (a - b) >= 2:
                return self.time_a
            elif b >= 12 and (b - a) >= 2:
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
            # Mantém end_time se ainda há vencedor
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
```

#### Model: EventoPonto

```python
class EventoPonto(models.Model):
    partida = models.ForeignKey(
        'Partida', 
        on_delete=models.CASCADE, 
        related_name='eventos'
    )
    time = models.ForeignKey(
        'Time', 
        on_delete=models.CASCADE
    )
    sequencia = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Evento de Ponto'
        verbose_name_plural = 'Eventos de Pontos'
        ordering = ['sequencia']
        unique_together = ['partida', 'sequencia']
    
    def __str__(self):
        return f"Ponto #{self.sequencia} - {self.time.nome}"
```

---

### Views Django

#### 1. Listar Partidas

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Partida

@login_required
def listar_partidas(request):
    """Lista todas as partidas com filtros opcionais"""
    partidas = Partida.objects.all().select_related(
        'time_a', 'time_b', 'vencedor'
    )
    
    # Filtro por status
    status = request.GET.get('status')
    if status:
        partidas = partidas.filter(status=status)
    
    context = {
        'partidas': partidas,
        'status_atual': status,
    }
    return render(request, 'partidas/listar.html', context)
```

#### 2. Criar Partida

```python
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Partida, Time
from .forms import PartidaForm

@login_required
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
    return render(request, 'partidas/criar.html', context)
```

#### 3. Detalhe da Partida (Placar)

```python
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Partida

@login_required
def detalhe_partida(request, pk):
    """Exibe o placar e controles da partida"""
    partida = get_object_or_404(
        Partida.objects.select_related('time_a', 'time_b', 'vencedor'),
        pk=pk
    )
    
    # Busca histórico de pontos
    eventos = partida.eventos.all().select_related('time')
    
    context = {
        'partida': partida,
        'eventos': eventos,
    }
    return render(request, 'partidas/detalhe.html', context)
```

#### 4. Iniciar Partida

```python
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Partida

@login_required
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
```

#### 5. Adicionar Ponto

```python
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Partida, Time

@login_required
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
```

#### 6. Desfazer Ponto

```python
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Partida

@login_required
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
```

---

### Forms Django

```python
from django import forms
from .models import Partida, Time

class PartidaForm(forms.ModelForm):
    class Meta:
        model = Partida
        fields = ['time_a', 'time_b']
        widgets = {
            'time_a': forms.Select(attrs={
                'class': 'form-control',
            }),
            'time_b': forms.Select(attrs={
                'class': 'form-control',
            }),
        }
        labels = {
            'time_a': 'Time A',
            'time_b': 'Time B',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        time_a = cleaned_data.get('time_a')
        time_b = cleaned_data.get('time_b')
        
        if time_a and time_b and time_a == time_b:
            raise forms.ValidationError(
                'Os times devem ser diferentes!'
            )
        
        return cleaned_data
```

---

### URLs

```python
from django.urls import path
from . import views

app_name = 'partidas'

urlpatterns = [
    # Listagem e criação
    path('', views.listar_partidas, name='listar_partidas'),
    path('nova/', views.criar_partida, name='criar_partida'),
    
    # Detalhe e ações
    path('<int:pk>/', views.detalhe_partida, name='detalhe_partida'),
    path('<int:pk>/iniciar/', views.iniciar_partida, name='iniciar_partida'),
    path('<int:pk>/ponto/<int:time_id>/', views.adicionar_ponto, name='adicionar_ponto'),
    path('<int:pk>/desfazer/', views.desfazer_ponto, name='desfazer_ponto'),
]
```

---

### Templates

#### Base: partidas/base.html

```html
{% extends 'base.html' %}

{% block extra_css %}
<style>
    .placar-container {
        text-align: center;
        padding: 2rem;
    }
    
    .placar-times {
        display: flex;
        justify-content: space-around;
        align-items: center;
        margin: 2rem 0;
    }
    
    .placar-time {
        flex: 1;
        text-align: center;
    }
    
    .placar-time h2 {
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .placar-pontos {
        font-size: 4rem;
        font-weight: bold;
        color: #333;
    }
    
    .placar-vencedor {
        color: #28a745;
    }
    
    .placar-vs {
        font-size: 2rem;
        color: #666;
        padding: 0 2rem;
    }
    
    .botoes-acao {
        display: flex;
        gap: 1rem;
        justify-content: center;
        margin: 2rem 0;
        flex-wrap: wrap;
    }
    
    .btn-ponto {
        font-size: 1.5rem;
        padding: 1rem 2rem;
        min-width: 200px;
    }
    
    .btn-desfazer {
        background-color: #ffc107;
        border-color: #ffc107;
        color: #000;
    }
    
    .btn-desfazer:hover {
        background-color: #e0a800;
        border-color: #d39e00;
    }
    
    .info-partida {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-top: 2rem;
    }
    
    .historico-pontos {
        max-height: 300px;
        overflow-y: auto;
        margin-top: 2rem;
    }
    
    .badge-status {
        font-size: 1rem;
        padding: 0.5rem 1rem;
    }
    
    @media (max-width: 768px) {
        .placar-times {
            flex-direction: column;
        }
        
        .placar-vs {
            padding: 1rem 0;
        }
        
        .placar-pontos {
            font-size: 3rem;
        }
        
        .btn-ponto {
            min-width: 100%;
        }
    }
</style>
{% endblock %}
```

#### Template: partidas/listar.html

```html
{% extends 'partidas/base.html' %}

{% block title %}Partidas{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>Partidas</h1>
        <a href="{% url 'partidas:criar_partida' %}" class="btn btn-primary">
            Nova Partida
        </a>
    </div>
    
    <!-- Filtros -->
    <div class="mb-4">
        <div class="btn-group" role="group">
            <a href="{% url 'partidas:listar_partidas' %}" 
               class="btn btn-outline-secondary {% if not status_atual %}active{% endif %}">
                Todas
            </a>
            <a href="{% url 'partidas:listar_partidas' %}?status=agendada" 
               class="btn btn-outline-secondary {% if status_atual == 'agendada' %}active{% endif %}">
                Agendadas
            </a>
            <a href="{% url 'partidas:listar_partidas' %}?status=em_andamento" 
               class="btn btn-outline-secondary {% if status_atual == 'em_andamento' %}active{% endif %}">
                Em Andamento
            </a>
            <a href="{% url 'partidas:listar_partidas' %}?status=finalizada" 
               class="btn btn-outline-secondary {% if status_atual == 'finalizada' %}active{% endif %}">
                Finalizadas
            </a>
        </div>
    </div>
    
    <!-- Lista de Partidas -->
    {% if partidas %}
        <div class="row">
            {% for partida in partidas %}
            <div class="col-md-6 mb-3">
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <h5 class="card-title mb-0">
                                {{ partida.time_a.nome }} vs {{ partida.time_b.nome }}
                            </h5>
                            <span class="badge 
                                {% if partida.status == 'agendada' %}bg-secondary
                                {% elif partida.status == 'em_andamento' %}bg-success
                                {% else %}bg-primary{% endif %}">
                                {{ partida.get_status_display }}
                            </span>
                        </div>
                        
                        <div class="text-center my-3">
                            <h2>
                                {{ partida.pontos_time_a }} x {{ partida.pontos_time_b }}
                            </h2>
                        </div>
                        
                        {% if partida.status == 'finalizada' %}
                            <p class="text-center text-success mb-2">
                                <strong>Vencedor: {{ partida.vencedor.nome }}</strong>
                            </p>
                        {% endif %}
                        
                        {% if partida.start_time %}
                            <p class="text-muted small mb-1">
                                Início: {{ partida.start_time|date:"d/m/Y H:i" }}
                            </p>
                        {% endif %}
                        
                        {% if partida.end_time %}
                            <p class="text-muted small mb-1">
                                Término: {{ partida.end_time|date:"d/m/Y H:i" }}
                            </p>
                            <p class="text-muted small mb-1">
                                Duração: {{ partida.duracao }}
                            </p>
                        {% endif %}
                        
                        <a href="{% url 'partidas:detalhe_partida' partida.pk %}" 
                           class="btn btn-sm btn-outline-primary mt-2">
                            Ver Detalhes
                        </a>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="alert alert-info">
            Nenhuma partida encontrada.
        </div>
    {% endif %}
</div>
{% endblock %}
```

#### Template: partidas/criar.html

```html
{% extends 'partidas/base.html' %}

{% block title %}Nova Partida{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <h1 class="mb-4">Nova Partida</h1>
            
            <form method="post">
                {% csrf_token %}
                
                {% if form.non_field_errors %}
                    <div class="alert alert-danger">
                        {{ form.non_field_errors }}
                    </div>
                {% endif %}
                
                <div class="mb-3">
                    <label for="{{ form.time_a.id_for_label }}" class="form-label">
                        {{ form.time_a.label }}
                    </label>
                    {{ form.time_a }}
                    {% if form.time_a.errors %}
                        <div class="text-danger">{{ form.time_a.errors }}</div>
                    {% endif %}
                </div>
                
                <div class="mb-3">
                    <label for="{{ form.time_b.id_for_label }}" class="form-label">
                        {{ form.time_b.label }}
                    </label>
                    {{ form.time_b }}
                    {% if form.time_b.errors %}
                        <div class="text-danger">{{ form.time_b.errors }}</div>
                    {% endif %}
                </div>
                
                <div class="d-flex gap-2">
                    <button type="submit" class="btn btn-primary">
                        Criar Partida
                    </button>
                    <a href="{% url 'partidas:listar_partidas' %}" class="btn btn-secondary">
                        Cancelar
                    </a>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

#### Template: partidas/detalhe.html

```html
{% extends 'partidas/base.html' %}

{% block title %}{{ partida.time_a.nome }} vs {{ partida.time_b.nome }}{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="placar-container">
        <!-- Cabeçalho -->
        <div class="d-flex justify-content-between align-items-center mb-4">
            <a href="{% url 'partidas:listar_partidas' %}" class="btn btn-outline-secondary">
                ← Voltar
            </a>
            <span class="badge badge-status
                {% if partida.status == 'agendada' %}bg-secondary
                {% elif partida.status == 'em_andamento' %}bg-success
                {% else %}bg-primary{% endif %}">
                {{ partida.get_status_display }}
            </span>
        </div>
        
        <!-- Placar -->
        <div class="placar-times">
            <div class="placar-time">
                <h2>{{ partida.time_a.nome }}</h2>
                <div class="placar-pontos {% if partida.vencedor == partida.time_a %}placar-vencedor{% endif %}">
                    {{ partida.pontos_time_a }}
                </div>
            </div>
            
            <div class="placar-vs">vs</div>
            
            <div class="placar-time">
                <h2>{{ partida.time_b.nome }}</h2>
                <div class="placar-pontos {% if partida.vencedor == partida.time_b %}placar-vencedor{% endif %}">
                    {{ partida.pontos_time_b }}
                </div>
            </div>
        </div>
        
        <!-- Mensagens -->
        {% if messages %}
            {% for message in messages %}
                <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            {% endfor %}
        {% endif %}
        
        <!-- Botões de Ação -->
        <div class="botoes-acao">
            {% if partida.status == 'agendada' %}
                <form method="post" action="{% url 'partidas:iniciar_partida' partida.pk %}">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-success btn-lg">
                        Iniciar Partida
                    </button>
                </form>
            {% elif partida.status == 'em_andamento' %}
                <form method="post" action="{% url 'partidas:adicionar_ponto' partida.pk partida.time_a.pk %}">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-primary btn-ponto">
                        +1 {{ partida.time_a.nome }}
                    </button>
                </form>
                
                <form method="post" action="{% url 'partidas:adicionar_ponto' partida.pk partida.time_b.pk %}">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-primary btn-ponto">
                        +1 {{ partida.time_b.nome }}
                    </button>
                </form>
                
                {% if partida.pode_desfazer %}
                    <form method="post" action="{% url 'partidas:desfazer_ponto' partida.pk %}" 
                          onsubmit="return confirm('Deseja realmente desfazer o último ponto?');">
                        {% csrf_token %}
                        <button type="submit" class="btn btn-desfazer btn-lg">
                            Desfazer Último Ponto
                        </button>
                    </form>
                {% endif %}
            {% endif %}
        </div>
        
        <!-- Informações da Partida -->
        <div class="info-partida">
            <div class="row">
                {% if partida.start_time %}
                    <div class="col-md-4">
                        <strong>Início:</strong><br>
                        {{ partida.start_time|date:"d/m/Y H:i:s" }}
                    </div>
                {% endif %}
                
                {% if partida.end_time %}
                    <div class="col-md-4">
                        <strong>Término:</strong><br>
                        {{ partida.end_time|date:"d/m/Y H:i:s" }}
                    </div>
                    <div class="col-md-4">
                        <strong>Duração:</strong><br>
                        {{ partida.duracao }}
                    </div>
                {% endif %}
                
                {% if partida.vencedor %}
                    <div class="col-12 mt-3">
                        <h4 class="text-success">
                            🏆 Vencedor: {{ partida.vencedor.nome }}
                        </h4>
                    </div>
                {% endif %}
            </div>
        </div>
        
        <!-- Histórico de Pontos -->
        {% if eventos %}
            <div class="historico-pontos">
                <h5 class="mt-4 mb-3">Histórico de Pontos</h5>
                <div class="list-group">
                    {% for evento in eventos %}
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between">
                                <span>
                                    <strong>Ponto #{{ evento.sequencia }}</strong> - 
                                    {{ evento.time.nome }}
                                </span>
                                <small class="text-muted">
                                    {{ evento.timestamp|date:"H:i:s" }}
                                </small>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            </div>
        {% endif %}
    </div>
</div>
{% endblock %}
```

---

## Migrations

### Migration: criar_models_partida

```python
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('app_name', 'previous_migration'),
    ]

    operations = [
        migrations.CreateModel(
            name='Partida',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pontos_time_a', models.IntegerField(default=0)),
                ('pontos_time_b', models.IntegerField(default=0)),
                ('start_time', models.DateTimeField(blank=True, null=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('agendada', 'Agendada'), ('em_andamento', 'Em Andamento'), ('finalizada', 'Finalizada')], default='agendada', max_length=20)),
                ('time_a', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='partidas_como_time_a', to='app_name.time')),
                ('time_b', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='partidas_como_time_b', to='app_name.time')),
                ('vencedor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vitorias', to='app_name.time')),
            ],
            options={
                'verbose_name': 'Partida',
                'verbose_name_plural': 'Partidas',
                'ordering': ['-start_time'],
            },
        ),
        migrations.CreateModel(
            name='EventoPonto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequencia', models.IntegerField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('partida', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='eventos', to='app_name.partida')),
                ('time', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app_name.time')),
            ],
            options={
                'verbose_name': 'Evento de Ponto',
                'verbose_name_plural': 'Eventos de Pontos',
                'ordering': ['sequencia'],
                'unique_together': {('partida', 'sequencia')},
            },
        ),
    ]
```

---

## Admin Django

```python
from django.contrib import admin
from .models import Partida, EventoPonto

@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'time_a', 
        'time_b', 
        'placar', 
        'status', 
        'vencedor',
        'start_time'
    ]
    list_filter = ['status', 'start_time']
    search_fields = [
        'time_a__nome', 
        'time_b__nome'
    ]
    readonly_fields = [
        'pontos_time_a', 
        'pontos_time_b', 
        'vencedor',
        'start_time',
        'end_time'
    ]
    
    def placar(self, obj):
        return f"{obj.pontos_time_a} x {obj.pontos_time_b}"
    placar.short_description = 'Placar'

@admin.register(EventoPonto)
class EventoPontoAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'partida',
        'sequencia',
        'time',
        'timestamp'
    ]
    list_filter = ['partida', 'time', 'timestamp']
    readonly_fields = ['timestamp']
```

---

## Testes

### Testes de Model

```python
from django.test import TestCase
from django.utils import timezone
from .models import Partida, EventoPonto, Time

class PartidaModelTest(TestCase):
    
    def setUp(self):
        self.time_a = Time.objects.create(nome="Time A", data=timezone.now().date())
        self.time_b = Time.objects.create(nome="Time B", data=timezone.now().date())
        self.partida = Partida.objects.create(
            time_a=self.time_a,
            time_b=self.time_b
        )
    
    def test_criar_partida(self):
        """Testa criação de partida"""
        self.assertEqual(self.partida.status, 'agendada')
        self.assertEqual(self.partida.pontos_time_a, 0)
        self.assertEqual(self.partida.pontos_time_b, 0)
        self.assertIsNone(self.partida.vencedor)
    
    def test_iniciar_partida(self):
        """Testa início de partida"""
        self.assertTrue(self.partida.iniciar())
        self.assertEqual(self.partida.status, 'em_andamento')
        self.assertIsNotNone(self.partida.start_time)
    
    def test_adicionar_ponto(self):
        """Testa adição de ponto"""
        self.partida.iniciar()
        self.assertTrue(self.partida.adicionar_ponto(self.time_a))
        self.assertEqual(self.partida.pontos_time_a, 1)
        self.assertEqual(self.partida.eventos.count(), 1)
    
    def test_vitoria_12x10(self):
        """Testa vitória com 12x10"""
        self.partida.iniciar()
        
        # Time A faz 12 pontos
        for _ in range(12):
            self.partida.adicionar_ponto(self.time_a)
        
        # Time B faz 10 pontos
        for _ in range(10):
            self.partida.adicionar_ponto(self.time_b)
        
        self.assertEqual(self.partida.status, 'finalizada')
        self.assertEqual(self.partida.vencedor, self.time_a)
    
    def test_nao_vence_12x11(self):
        """Testa que 12x11 não é vitória"""
        self.partida.iniciar()
        
        # Time A faz 12 pontos
        for _ in range(12):
            self.partida.adicionar_ponto(self.time_a)
        
        # Time B faz 11 pontos
        for _ in range(11):
            self.partida.adicionar_ponto(self.time_b)
        
        self.assertEqual(self.partida.status, 'em_andamento')
        self.assertIsNone(self.partida.vencedor)
    
    def test_vitoria_14x13_apos_11x11(self):
        """Testa vitória 14x13 após 11x11"""
        self.partida.iniciar()
        
        # Ambos fazem 11 pontos
        for _ in range(11):
            self.partida.adicionar_ponto(self.time_a)
            self.partida.adicionar_ponto(self.time_b)
        
        # Time A faz mais 3 pontos (chega a 14)
        for _ in range(3):
            self.partida.adicionar_ponto(self.time_a)
        
        # Time B faz mais 2 pontos (chega a 13)
        for _ in range(2):
            self.partida.adicionar_ponto(self.time_b)
        
        self.assertEqual(self.partida.status, 'finalizada')
        self.assertEqual(self.partida.vencedor, self.time_a)
    
    def test_desfazer_ponto(self):
        """Testa desfazer ponto"""
        self.partida.iniciar()
        self.partida.adicionar_ponto(self.time_a)
        self.partida.adicionar_ponto(self.time_b)
        
        self.assertTrue(self.partida.desfazer_ultimo_ponto())
        self.assertEqual(self.partida.pontos_time_b, 0)
        self.assertEqual(self.partida.eventos.count(), 1)
    
    def test_desfazer_volta_em_andamento(self):
        """Testa que desfazer pode voltar partida para em andamento"""
        self.partida.iniciar()
        
        # Time A faz 12 pontos
        for _ in range(12):
            self.partida.adicionar_ponto(self.time_a)
        
        # Partida finalizada
        self.assertEqual(self.partida.status, 'finalizada')
        
        # Desfaz último ponto
        self.partida.desfazer_ultimo_ponto()
        
        # Volta para em andamento
        self.assertEqual(self.partida.status, 'em_andamento')
        self.assertIsNone(self.partida.vencedor)
```

---

## Segurança e Permissões

### Decorators Personalizados

```python
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect

def organizador_required(view_func):
    """Decorator para verificar se usuário é organizador"""
    def check_organizador(user):
        return user.is_authenticated and (
            user.is_staff or 
            hasattr(user, 'is_organizador') and user.is_organizador
        )
    
    decorated_view = user_passes_test(
        check_organizador,
        login_url='/login/'
    )(view_func)
    
    return decorated_view
```

### Uso nos Views

```python
@organizador_required
def criar_partida(request):
    # ... código da view
    pass

@organizador_required
def iniciar_partida(request, pk):
    # ... código da view
    pass
```

---

## Melhorias Futuras

### Fase 2 (Não Implementar Agora)

1. **Estatísticas Completas**
   - Dashboard com gráficos
   - Ranking de times
   - Histórico de confrontos
   - Média de pontos por partida

2. **Relatórios**
   - Exportação para PDF
   - Exportação para Excel
   - Relatórios personalizados

3. **Tempo Real**
   - WebSockets para atualização automática
   - Múltiplos usuários visualizando simultaneamente
   - Notificações push

4. **Recursos Avançados**
   - Controle de sets múltiplos
   - Pausas e tempos técnicos
   - Substituições de jogadores
   - Estatísticas individuais de jogadores

5. **Mobile App**
   - App nativo iOS/Android
   - Modo offline
   - Sincronização automática

---

## Checklist de Implementação

- [ ] Criar models Partida e EventoPonto
- [ ] Criar e aplicar migrations
- [ ] Implementar métodos de lógica de negócio no model
- [ ] Criar forms
- [ ] Criar views (listar, criar, detalhe, ações)
- [ ] Configurar URLs
- [ ] Criar templates (listar, criar, detalhe)
- [ ] Adicionar CSS responsivo
- [ ] Configurar admin
- [ ] Implementar permissões
- [ ] Escrever testes unitários
- [ ] Testar fluxo completo manualmente
- [ ] Validar regras de vitória
- [ ] Testar função desfazer
- [ ] Testar responsividade mobile
- [ ] Documentar código

---

## Notas de Implementação

1. **Ordem de Implementação Sugerida:**
   - Models → Migrations → Admin → Forms → Views → URLs → Templates → Testes

2. **Pontos de Atenção:**
   - Validar sempre que time_a ≠ time_b
   - Garantir atomicidade nas operações de ponto
   - Testar extensivamente as regras de vitória
   - Implementar confirmação antes de desfazer ponto
   - Considerar race conditions em ambiente multi-usuário

3. **Performance:**
   - Usar select_related para evitar N+1 queries
   - Indexar campos de busca frequente
   - Considerar cache para listagem de partidas

4. **UX:**
   - Feedback visual imediato ao adicionar ponto
   - Confirmação antes de ações irreversíveis
   - Mensagens claras de sucesso/erro
   - Interface intuitiva e responsiva
