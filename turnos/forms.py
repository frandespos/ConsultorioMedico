from django import forms

from .models import Paciente, Profesional


class HoraWidget(forms.MultiWidget):
    """Dos listas en formato 24 hs: el selector del navegador depende de la compu (a.m./p.m.)."""
    HORAS = [("", "Hora")] + [(f"{h:02d}", f"{h:02d}") for h in range(8, 21)]
    MINUTOS = [("", "Min")] + [(f"{m:02d}", f"{m:02d}") for m in range(0, 60, 5)]

    def __init__(self, attrs=None):
        super().__init__([forms.Select(choices=self.HORAS), forms.Select(choices=self.MINUTOS)],
                         attrs)

    def decompress(self, value):
        if not value:
            return [None, None]
        texto = value.strftime("%H:%M") if hasattr(value, "strftime") else str(value)
        return texto.split(":")[:2]

    def value_from_datadict(self, data, files, name):
        hora, minutos = super().value_from_datadict(data, files, name)
        return f"{hora}:{minutos}" if hora and minutos else ""


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ["nombre", "apellido", "dni", "telefono", "obra_social"]


class TurnoForm(forms.Form):
    paciente = forms.ModelChoiceField(queryset=Paciente.objects.all())
    profesional = forms.ModelChoiceField(
        queryset=Profesional.objects.select_related("especialidad"))
    fecha = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    hora = forms.TimeField(widget=HoraWidget)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profesional"].label_from_instance = lambda p: p.mostrar_datos()
        self.fields["paciente"].label_from_instance = (
            lambda p: f"{p.apellido}, {p.nombre} - DNI {p.dni} ({p.obra_social})")
