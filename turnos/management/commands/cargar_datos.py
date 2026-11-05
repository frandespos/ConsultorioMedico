"""
Carga los profesionales reales del CMET, obras sociales y el usuario del secretario.
Los pacientes se registran desde el sistema.

Uso:  python manage.py cargar_datos
"""

from datetime import time

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from turnos.models import (Consultorio, Especialidad, HorarioAtencion, ObraSocial, Paciente,
                           Profesional, Secretario)

T = HorarioAtencion.CON_TURNO
O = HorarioAtencion.ORDEN_LLEGADA

# (especialidad, nombre, apellido, obras sociales, [(día, inicio, fin, frecuencia, modalidad)])
# Las horas de fin que no figuran en la cartelería son estimadas.
PROFESIONALES = [
    ("Médico clínico", "Valeria", "Segurado", ["Agremiación Médica"],
     [("martes", time(9), time(15), "semanal", T), ("jueves", time(9), time(15), "semanal", T)]),
    ("Pediatría", "Karina", "Estilarte", ["Agremiación Médica"],
     [("martes", time(9), time(14), "semanal", O), ("jueves", time(9), time(14), "semanal", O),
      ("viernes", time(16), time(19), "semanal", O)]),
    ("Pediatría del Neurodesarrollo", "Liliana", "Rodríguez", [],
     [("martes", time(9), time(12), "mensual", T)]),
    ("Cardiología adultos", "Pablo", "Guenaga", ["Agremiación Médica"],
     [("lunes", time(9), time(12), "semanal", O)]),
    ("Cardiología infantil", "Fernando", "Pavone", ["Agremiación Médica"],
     [("martes", time(8, 30), time(11, 30), "mensual", O)]),
    ("Ginecología y obstetricia", "Marianela", "Figueroa", ["Agremiación Médica"],
     [("jueves", time(9), time(11, 30), "semanal", T)]),
    ("Dermatología", "Guillermina", "Nave", ["Agremiación Médica"],
     [("martes", time(9), time(12), "quincenal", O)]),
    ("Oftalmología", "Patricia", "Chayle", ["Agremiación Médica"],
     [("martes", time(9), time(12), "semanal", O)]),
    ("Ecografías", "Karina", "Ditella", ["Agremiación Médica"],
     [("lunes", time(9), time(12), "semanal", O)]),
    ("Fonoaudiología", "Claudia", "Arcaro", [],
     [("lunes", time(9), time(12), "semanal", T), ("viernes", time(9), time(12), "semanal", T)]),
    ("Psicopedagogía", "Marilina", "Borda", [],
     [("lunes", time(9), time(12), "semanal", T), ("viernes", time(9), time(12), "semanal", T)]),
    ("Psicología", "Felicitas", "Jamar", [], [("lunes", time(9), time(13), "semanal", T)]),
    ("Psicología", "Romina", "Paoli", [], [("lunes", time(14), time(18), "semanal", T)]),
    ("Traumatología y Ozonoterapia", "Darío", "Barrios", ["Agremiación Médica"],
     [("lunes", time(10), time(15), "semanal", O)]),
    ("Nutrición", "Tamara", "Oses", [], [("viernes", time(16), time(19), "semanal", T)]),
    ("Psicología", "Fiorella", "Petitto", [], [("viernes", time(16), time(19), "semanal", T)]),
]

class Command(BaseCommand):
    help = "Carga los datos iniciales del consultorio"

    @transaction.atomic
    def handle(self, *args, **options):
        consultorio, _ = Consultorio.objects.get_or_create(nombre="Consultorio Médico El Toboso")

        obras = {n: ObraSocial.objects.get_or_create(nombre=n)[0]
                 for n in ["Agremiación Médica", "Particular"]}

        for i, (esp, nombre, apellido, obras_prof, horarios) in enumerate(PROFESIONALES, 1):
            especialidad, _ = Especialidad.objects.get_or_create(nombre=esp)
            prof, creado = Profesional.objects.get_or_create(
                nombre=nombre, apellido=apellido,
                defaults={"especialidad": especialidad, "matricula": f"MP-{i:04d}",
                          "consultorio": consultorio})
            if creado:
                prof.obras_sociales.set([obras[o] for o in obras_prof] + [obras["Particular"]])
                for h in horarios:
                    prof.agregar_horario(*h)

        if not User.objects.filter(username="secretario").exists():
            user = User.objects.create_user("secretario", password="cmet2026")
            Secretario.objects.create(nombre="Secretario", apellido="CMET", usuario=user)

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {Profesional.objects.count()} profesionales, "
            f"{Especialidad.objects.count()} especialidades, {Paciente.objects.count()} pacientes. "
            "Usuario: secretario / cmet2026"))
