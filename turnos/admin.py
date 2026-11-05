from django.contrib import admin

from .models import (Consultorio, Especialidad, HorarioAtencion, ObraSocial, Paciente,
                     Profesional, Secretario, TurnoPorOrden, TurnoProgramado)


class HorarioInline(admin.TabularInline):
    model = HorarioAtencion
    extra = 0


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = ["apellido", "nombre", "especialidad", "matricula"]
    list_filter = ["especialidad"]
    filter_horizontal = ["obras_sociales"]
    inlines = [HorarioInline]


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ["apellido", "nombre", "dni", "telefono", "obra_social"]
    search_fields = ["apellido", "nombre", "dni"]


@admin.register(TurnoProgramado)
class TurnoProgramadoAdmin(admin.ModelAdmin):
    list_display = ["fecha", "hora", "profesional", "paciente", "estado"]
    list_filter = ["fecha", "estado", "profesional"]


@admin.register(TurnoPorOrden)
class TurnoPorOrdenAdmin(admin.ModelAdmin):
    list_display = ["fecha", "numero_orden", "profesional", "paciente", "estado"]
    list_filter = ["fecha", "estado", "profesional"]


admin.site.register([Consultorio, Especialidad, ObraSocial, Secretario])
