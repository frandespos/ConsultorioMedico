"""
Modelos del Sistema de Turnos - Consultorio Médico El Toboso (CMET)

Pilares de POO:
- ENCAPSULAMIENTO: la lógica y las validaciones quedan dentro de cada clase
  (métodos como dar_turno(), cancelar(), acepta_obra_social()). Desde afuera
  nadie arma un turno "a mano": se le pide al Consultorio que lo haga.
  Los métodos que empiezan con _ son de uso interno.
- HERENCIA: Persona (abstracta) -> Paciente, Profesional, Secretario.
            Turno -> TurnoProgramado, TurnoPorOrden.
- POLIMORFISMO: mostrar_datos(), mostrar() y get_tipo() se redefinen en cada subclase.

Relaciones:
- ASOCIACIÓN:   ForeignKey / ManyToMany entre objetos independientes
                (Paciente-ObraSocial, Profesional-Especialidad, Turno-Paciente...).
- AGREGACIÓN:   Consultorio tiene Profesionales y Pacientes (on_delete=SET_NULL:
                si se borra el consultorio, las personas siguen existiendo).
- COMPOSICIÓN:  Profesional -> HorarioAtencion y Consultorio -> Turno
                (on_delete=CASCADE: la parte no existe sin el todo).
"""

from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from .notificaciones import NotificacionWhatsApp

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# =====================================================================
#  Clases de catálogo
# =====================================================================

class Especialidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "especialidades"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ObraSocial(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "obra social"
        verbose_name_plural = "obras sociales"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Consultorio(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.nombre

    # ---- La lógica principal está encapsulada acá ----

    def dar_turno(self, paciente, profesional, fecha, hora=None):
        """
        Crea el turno que corresponda según la modalidad del profesional ese día.
        Lanza ValidationError con el motivo si no se puede.
        """
        horario = profesional.horario_del_dia(fecha)
        if horario is None:
            raise ValidationError(f"{profesional.nombre_completo} no atiende ese día.")

        if not profesional.acepta_obra_social(paciente.obra_social):
            raise ValidationError(
                f"{profesional.nombre_completo} no atiende {paciente.obra_social}.")

        if self._turnos_activos(profesional, fecha).filter(paciente=paciente).exists():
            raise ValidationError("El paciente ya tiene un turno con ese profesional ese día.")

        # Polimorfismo: según la modalidad se crea un tipo de turno u otro
        if horario.es_con_turno():
            self._validar_hora(horario, profesional, fecha, hora)
            return TurnoProgramado.objects.create(
                consultorio=self, paciente=paciente, profesional=profesional,
                fecha=fecha, hora=hora)

        self._validar_rango_horario(horario, hora)
        numero = self._proximo_numero_orden(profesional, fecha)
        return TurnoPorOrden.objects.create(
            consultorio=self, paciente=paciente, profesional=profesional,
            fecha=fecha, numero_orden=numero, hora=hora)

    def turnos_de_la_fecha(self, fecha):
        turnos = self.turnos.filter(fecha=fecha, estado=Turno.ACTIVO)
        return [t.como_subtipo() for t in turnos]

    # ---- Métodos internos ----

    def _turnos_activos(self, profesional, fecha):
        return self.turnos.filter(profesional=profesional, fecha=fecha, estado=Turno.ACTIVO)

    def _validar_rango_horario(self, horario, hora):
        if hora is None:
            raise ValidationError("Indicá la hora del turno.")
        if not horario.incluye_hora(hora):
            raise ValidationError(
                f"La hora tiene que estar entre {horario.hora_inicio:%H:%M} "
                f"y {horario.hora_fin:%H:%M}.")

    def _validar_hora(self, horario, profesional, fecha, hora):
        self._validar_rango_horario(horario, hora)
        ocupado = TurnoProgramado.objects.filter(
            consultorio=self, profesional=profesional, fecha=fecha,
            hora=hora, estado=Turno.ACTIVO).exists()
        if ocupado:
            raise ValidationError(f"El horario {hora:%H:%M} ya está ocupado.")

    def _proximo_numero_orden(self, profesional, fecha):
        ultimo = TurnoPorOrden.objects.filter(
            consultorio=self, profesional=profesional, fecha=fecha
        ).order_by("-numero_orden").first()
        return ultimo.numero_orden + 1 if ultimo else 1


# =====================================================================
#  Personas (HERENCIA)
# =====================================================================

class Persona(models.Model):
    """Clase abstracta: no crea tabla propia ni se puede instanciar sola."""
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField("DNI", max_length=15, blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)

    class Meta:
        abstract = True

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    def mostrar_datos(self):
        raise NotImplementedError("Cada subclase tiene que implementar mostrar_datos()")

    def __str__(self):
        return self.nombre_completo


class Paciente(Persona):
    obra_social = models.ForeignKey(ObraSocial, on_delete=models.PROTECT)       # ASOCIACIÓN
    consultorio = models.ForeignKey(Consultorio, on_delete=models.SET_NULL,     # AGREGACIÓN
                                    null=True, related_name="pacientes")

    class Meta:
        ordering = ["apellido", "nombre"]
        constraints = [models.UniqueConstraint(fields=["dni"], name="dni_paciente_unico")]

    def mostrar_datos(self):
        return f"Paciente {self.nombre_completo} - DNI {self.dni} - {self.obra_social}"

    def historial(self):
        return [t.como_subtipo() for t in self.turnos.order_by("-fecha")]

    def eliminar(self):
        """Borra al paciente con su historial, salvo que tenga turnos por atender."""
        if self.turnos.filter(estado=Turno.ACTIVO, fecha__gte=date.today()).exists():
            raise ValidationError(
                f"{self.nombre_completo} tiene turnos pendientes: cancelalos antes de eliminarlo.")
        self.delete()


class Profesional(Persona):
    matricula = models.CharField("matrícula", max_length=30)
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT,    # ASOCIACIÓN
                                     related_name="profesionales")
    obras_sociales = models.ManyToManyField(ObraSocial, related_name="profesionales")  # ASOCIACIÓN
    consultorio = models.ForeignKey(Consultorio, on_delete=models.SET_NULL,     # AGREGACIÓN
                                    null=True, related_name="profesionales")

    class Meta:
        verbose_name_plural = "profesionales"
        ordering = ["especialidad__nombre", "apellido"]

    def agregar_horario(self, dia, hora_inicio, hora_fin, frecuencia, modalidad):
        # COMPOSICIÓN: el horario se crea desde el profesional y le pertenece
        return self.horarios.create(dia=dia, hora_inicio=hora_inicio, hora_fin=hora_fin,
                                    frecuencia=frecuencia, modalidad=modalidad)

    def acepta_obra_social(self, obra_social):
        return self.obras_sociales.filter(pk=obra_social.pk).exists()

    def horario_del_dia(self, fecha):
        return self.horarios.filter(dia=DIAS_SEMANA[fecha.weekday()]).first()

    def atiende_el(self, fecha):
        return self.horario_del_dia(fecha) is not None

    def mostrar_datos(self):
        return f"{self.especialidad} - {self.nombre_completo} (Mat. {self.matricula})"


class Secretario(Persona):
    """Usa el User de Django para el login: la contraseña queda hasheada (encapsulada)."""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="secretario")

    class Meta:
        verbose_name_plural = "secretarios"

    def mostrar_datos(self):
        return f"Secretario {self.nombre_completo} (usuario: {self.usuario.username})"


# =====================================================================
#  Horario de atención (COMPOSICIÓN con Profesional)
# =====================================================================

class HorarioAtencion(models.Model):
    CON_TURNO = "con_turno"
    ORDEN_LLEGADA = "orden_llegada"
    MODALIDADES = [(CON_TURNO, "Con turno"), (ORDEN_LLEGADA, "Orden de llegada")]
    FRECUENCIAS = [("semanal", "Semanal"), ("quincenal", "Cada 15 días"),
                   ("mensual", "Una vez al mes")]

    profesional = models.ForeignKey(Profesional, on_delete=models.CASCADE,      # COMPOSICIÓN
                                    related_name="horarios")
    dia = models.CharField(max_length=10, choices=[(d, d.capitalize()) for d in DIAS_SEMANA])
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    frecuencia = models.CharField(max_length=10, choices=FRECUENCIAS, default="semanal")
    modalidad = models.CharField(max_length=15, choices=MODALIDADES)

    class Meta:
        verbose_name = "horario de atención"
        verbose_name_plural = "horarios de atención"

    def es_con_turno(self):
        return self.modalidad == self.CON_TURNO

    def incluye_hora(self, hora):
        return self.hora_inicio <= hora < self.hora_fin

    def __str__(self):
        return (f"{self.get_dia_display()} {self.hora_inicio:%H:%M} a {self.hora_fin:%H:%M} "
                f"({self.get_frecuencia_display()}, {self.get_modalidad_display()})")


# =====================================================================
#  Turnos (HERENCIA + POLIMORFISMO)
# =====================================================================

class Turno(models.Model):
    ACTIVO = "activo"
    CANCELADO = "cancelado"
    ESTADOS = [(ACTIVO, "Activo"), (CANCELADO, "Cancelado")]

    consultorio = models.ForeignKey(Consultorio, on_delete=models.CASCADE,      # COMPOSICIÓN
                                    related_name="turnos")
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE,            # ASOCIACIÓN
                                 related_name="turnos")
    profesional = models.ForeignKey(Profesional, on_delete=models.CASCADE,      # ASOCIACIÓN
                                    related_name="turnos")
    fecha = models.DateField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default=ACTIVO)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "profesional"]

    def esta_activo(self):
        return self.estado == self.ACTIVO

    def cancelar(self):
        if not self.esta_activo():
            raise ValidationError("El turno ya estaba cancelado.")
        self.estado = self.CANCELADO
        self.save()

    def como_subtipo(self):
        """Devuelve el objeto como su clase hija real (TurnoProgramado o TurnoPorOrden)."""
        if hasattr(self, "turnoprogramado"):
            return self.turnoprogramado
        if hasattr(self, "turnopororden"):
            return self.turnopororden
        return self

    def get_tipo(self):
        raise NotImplementedError

    def get_detalle(self):
        raise NotImplementedError

    def get_horario(self):
        raise NotImplementedError

    def get_linea_numero(self):
        """Línea extra del mensaje; solo la usa el turno por orden de llegada."""
        return ""

    def mostrar(self):
        return (f"{self.fecha:%d/%m/%Y} | {self.get_detalle()} | {self.profesional} "
                f"({self.profesional.especialidad}) | {self.paciente}")

    def texto_aviso(self):
        """Mensaje para el paciente; get_detalle() y get_horario() dependen del subtipo."""
        novedad = "quedó confirmado" if self.esta_activo() else "fue cancelado"
        texto = (f"Hola {self.paciente.nombre}, tu turno en {self.consultorio} {novedad}.\n"
                 f"Fecha: {DIAS_SEMANA[self.fecha.weekday()]} {self.fecha:%d/%m/%Y}\n"
                 f"Horario: {self.get_horario()}\n"
                 f"{self.get_linea_numero()}"
                 f"Profesional: {self.profesional} ({self.profesional.especialidad})")
        if not self.esta_activo():
            texto += "\nSi necesitás otro turno, comunicate con el consultorio."
        return texto

    def whatsapp(self):
        return NotificacionWhatsApp(self)

    def __str__(self):
        return self.como_subtipo().mostrar()


class TurnoProgramado(Turno):
    hora = models.TimeField()

    class Meta:
        verbose_name = "turno programado"
        verbose_name_plural = "turnos programados"

    def get_tipo(self):
        return "Con turno"

    def get_detalle(self):
        return f"{self.hora:%H:%M} hs"

    def get_horario(self):
        return self.get_detalle()


class TurnoPorOrden(Turno):
    numero_orden = models.PositiveIntegerField()
    hora = models.TimeField(null=True, blank=True)  # los turnos anteriores no la tienen

    class Meta:
        verbose_name = "turno por orden de llegada"
        verbose_name_plural = "turnos por orden de llegada"

    def get_tipo(self):
        return "Orden de llegada"

    def get_detalle(self):
        numero = f"N° {self.numero_orden}"
        return f"{numero} · {self.hora:%H:%M} hs" if self.hora else numero

    def get_horario(self):
        if self.hora:
            return f"{self.hora:%H:%M} hs"
        horario = self.profesional.horario_del_dia(self.fecha)
        if horario is None:
            return "a confirmar"
        return f"{horario.hora_inicio:%H:%M} a {horario.hora_fin:%H:%M} hs"

    def get_linea_numero(self):
        return f"Turno: N° {self.numero_orden}\n"
