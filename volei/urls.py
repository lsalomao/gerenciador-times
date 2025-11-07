from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('jogadores/', views.JogadorListView.as_view(), name='jogador_list'),
    path('jogadores/novo/', views.JogadorCreateView.as_view(), name='jogador_create'),
    path('jogadores/<int:pk>/editar/', views.JogadorUpdateView.as_view(), name='jogador_update'),
    path('jogadores/<int:pk>/excluir/', views.JogadorDeleteView.as_view(), name='jogador_delete'),
    path('presencas/', views.presenca_list, name='presenca_list'),
    path('presencas/gerenciar/', views.gerenciar_presencas, name='gerenciar_presencas'),
    path('times/', views.time_list, name='time_list'),
    path('times/gerar/', views.gerar_times, name='gerar_times'),
    path('times/<int:pk>/editar/', views.editar_time, name='editar_time'),
    path('times/<int:pk>/excluir/', views.excluir_time, name='excluir_time'),
]
