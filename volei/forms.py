from django import forms
from .models import Jogador, Presenca, Time

class JogadorForm(forms.ModelForm):
    class Meta:
        model = Jogador
        fields = ['nome', 'nivel', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do jogador'}),
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class PresencaForm(forms.ModelForm):
    class Meta:
        model = Presenca
        fields = ['jogador', 'confirmado']
        widgets = {
            'jogador': forms.HiddenInput(),
            'confirmado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

PresencaFormSet = forms.modelformset_factory(
    Presenca,
    form=PresencaForm,
    extra=0
)
