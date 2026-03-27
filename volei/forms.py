from django import forms
from .models import Jogador, Presenca, Time, Partida

class JogadorForm(forms.ModelForm):
    class Meta:
        model = Jogador
        fields = ['nome', 'nivel', 'posicao_preferida', 'tipo_jogador', 'ativo', 'data_nascimento']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do jogador'}),
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'posicao_preferida': forms.Select(attrs={'class': 'form-select'}),
            'tipo_jogador': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
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


class PartidaForm(forms.ModelForm):
    class Meta:
        model = Partida
        fields = ['time_a', 'time_b']
        widgets = {
            'time_a': forms.Select(attrs={
                'class': 'form-select',
            }),
            'time_b': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        labels = {
            'time_a': 'Time A',
            'time_b': 'Time B',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from datetime import date
        hoje = date.today()
        times_hoje = Time.objects.filter(data=hoje).prefetch_related('jogadores')
        self.fields['time_a'].queryset = times_hoje
        self.fields['time_b'].queryset = times_hoje

        self.fields['time_a'].label_from_instance = self.label_time_com_jogador
        self.fields['time_b'].label_from_instance = self.label_time_com_jogador

    def label_time_com_jogador(self, obj):
        primeiro_jogador = obj.jogadores.first()
        if primeiro_jogador:
            return f"{obj.nome} - {primeiro_jogador.nome}"
        return obj.nome

    def clean(self):
        cleaned_data = super().clean()
        time_a = cleaned_data.get('time_a')
        time_b = cleaned_data.get('time_b')

        if time_a and time_b and time_a == time_b:
            raise forms.ValidationError(
                'Os times devem ser diferentes!'
            )

        return cleaned_data