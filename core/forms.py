from django import forms

from .criterios import get_areas_disponiveis
from .models import AllowedEmail, Processo


class EmailOnlyLoginForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=254)


class ProcessoForm(forms.ModelForm):
    class Meta:
        model = Processo
        fields = ["nome", "area", "job_title", "admission_category", "senioridade", "local"]

    area = forms.ChoiceField(choices=[], required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["area"].choices = [(a, a) for a in get_areas_disponiveis()]


class CandidatoAplicacaoForm(forms.Form):
    nome = forms.CharField(max_length=255)
    email = forms.EmailField()
    linkedin = forms.URLField(required=False)
    greenhouse_id = forms.URLField(required=False)
    pbix_file = forms.URLField(required=False)
    optional_file = forms.URLField(required=False)


class AllowedEmailForm(forms.ModelForm):
    class Meta:
        model = AllowedEmail
        fields = ["email", "role"]
