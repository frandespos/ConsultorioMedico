from django import forms

from .models import Paciente, Profesional


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ["nombre", "apellido", "dni", "telefono", "obra_social"]


class TurnoForm(forms.Form):
    paciente = forms.ModelChoiceField(queryset=Paciente.objects.all())
    profesional = forms.ModelChoiceField(
        queryset=Profesional.objects.select_related("especialidad"))
    fecha = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    hora = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profesional"].label_from_instance = lambda p: p.mostrar_datos()
        self.fields["paciente"].label_from_instance = (
            lambda p: f"{p.apellido}, {p.nombre} - DNI {p.dni} ({p.obra_social})")
