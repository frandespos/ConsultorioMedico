from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html

from .forms import PacienteForm, TurnoForm
from .models import Consultorio, Especialidad, Paciente, Turno


def _consultorio():
    return Consultorio.objects.first()


def _confirmacion_cancelado(turno):
    """Lleva el enlace de WhatsApp porque el turno cancelado desaparece de la agenda."""
    whatsapp = turno.whatsapp()
    if not whatsapp.disponible():
        return "Turno cancelado."
    return format_html('Turno cancelado. <a href="{}" target="_blank" rel="noopener" '
                       'class="alert-link">Avisar por WhatsApp</a>', whatsapp.enlace())


@login_required
def inicio(request):
    """Pantalla principal: turnos del día elegido (por defecto, hoy)."""
    texto = request.GET.get("fecha")
    fecha = datetime.strptime(texto, "%Y-%m-%d").date() if texto else date.today()
    turnos = _consultorio().turnos_de_la_fecha(fecha)  # cada uno ya como su subtipo
    return render(request, "turnos/inicio.html", {"turnos": turnos, "fecha": fecha})


@login_required
def dar_turno(request):
    form = TurnoForm(request.POST or None, initial={"paciente": request.GET.get("paciente")})
    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        try:
            turno = _consultorio().dar_turno(datos["paciente"], datos["profesional"],
                                             datos["fecha"], datos["hora"])
            messages.success(request, f"Turno asignado: {turno.mostrar()}")
            return redirect(f"/?fecha={datos['fecha']:%Y-%m-%d}")
        except ValidationError as e:
            messages.error(request, e.messages[0])
    return render(request, "turnos/dar_turno.html", {"form": form})


@login_required
def cancelar_turno(request, pk):
    turno = get_object_or_404(Turno, pk=pk).como_subtipo()
    if request.method == "POST":
        try:
            turno.cancelar()
            messages.success(request, _confirmacion_cancelado(turno))
        except ValidationError as e:
            messages.error(request, e.messages[0])
    return redirect(request.POST.get("volver") or "inicio")


@login_required
def pacientes(request):
    q = request.GET.get("q", "")
    lista = Paciente.objects.select_related("obra_social")
    if q:
        lista = lista.filter(apellido__icontains=q) | lista.filter(dni__icontains=q)
    return render(request, "turnos/pacientes.html", {"pacientes": lista, "q": q})


@login_required
def nuevo_paciente(request):
    form = PacienteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        paciente = form.save(commit=False)
        paciente.consultorio = _consultorio()
        paciente.save()
        messages.success(request, f"Paciente registrado: {paciente.mostrar_datos()}")
        return redirect("pacientes")
    return render(request, "turnos/nuevo_paciente.html",
                  {"form": form, "titulo": "Registrar paciente"})


@login_required
def editar_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    form = PacienteForm(request.POST or None, instance=paciente)
    if request.method == "POST" and form.is_valid():
        paciente = form.save()
        messages.success(request, f"Paciente actualizado: {paciente.mostrar_datos()}")
        return redirect("pacientes")
    return render(request, "turnos/nuevo_paciente.html",
                  {"form": form, "titulo": "Editar paciente"})


@login_required
def eliminar_paciente(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    if request.method == "POST":
        nombre = paciente.nombre_completo
        try:
            paciente.eliminar()
            messages.success(request, f"Paciente eliminado: {nombre}.")
        except ValidationError as e:
            messages.error(request, e.messages[0])
    return redirect("pacientes")


@login_required
def historial(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    return render(request, "turnos/historial.html",
                  {"paciente": paciente, "turnos": paciente.historial()})


@login_required
def profesionales(request):
    especialidades = Especialidad.objects.prefetch_related(
        "profesionales__horarios", "profesionales__obras_sociales")
    return render(request, "turnos/profesionales.html", {"especialidades": especialidades})
