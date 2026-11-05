from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from .models import (Consultorio, Especialidad, HorarioAtencion, ObraSocial, Paciente, Profesional,
                     Turno, TurnoPorOrden)
from .notificaciones import NotificacionWhatsApp


class AvisosTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretario"))
        self.consultorio = Consultorio.objects.create(nombre="CMET")
        self.obra = ObraSocial.objects.create(nombre="Particular")
        self.paciente = Paciente.objects.create(
            nombre="Ana", apellido="Gómez", dni="1", telefono="2214556677",
            obra_social=self.obra, consultorio=self.consultorio)
        self.profesional = Profesional.objects.create(
            nombre="Karina", apellido="Estilarte", matricula="1", consultorio=self.consultorio,
            especialidad=Especialidad.objects.create(nombre="Pediatría"))
        self.profesional.obras_sociales.add(self.obra)

    def _asignar(self, modalidad=HorarioAtencion.ORDEN_LLEGADA, hora="10:30"):
        self.profesional.agregar_horario("martes", time(9), time(14), "semanal", modalidad)
        return self.client.post("/turnos/nuevo/", {
            "paciente": self.paciente.pk, "profesional": self.profesional.pk,
            "fecha": "2026-11-24", "hora": hora}, follow=True)

    def test_turno_por_orden_muestra_boton_de_whatsapp(self):
        respuesta = self._asignar()
        self.assertContains(respuesta, "https://wa.me/5492214556677?text=Hola%20Ana")
        self.assertContains(respuesta, "martes%2024/11/2026")
        self.assertContains(respuesta, "Turno%3A%20N%C2%B0%201")
        self.assertContains(respuesta, "Horario%3A%2010%3A30%20hs")
        self.assertContains(respuesta, "N° 1 · 10:30 hs")
        self.assertNotContains(respuesta, "Orden%20de%20llegada")

    def test_turno_programado_informa_la_hora(self):
        respuesta = self._asignar(HorarioAtencion.CON_TURNO, "10:30")
        self.assertContains(respuesta, "Horario%3A%2010%3A30%20hs")
        self.assertNotContains(respuesta, "Turno%3A")

    def test_cancelar_ofrece_whatsapp(self):
        self._asignar()
        turno = self.paciente.turnos.get()
        respuesta = self.client.post(f"/turnos/{turno.pk}/cancelar/", follow=True)
        self.assertContains(respuesta, '<a href="https://wa.me/5492214556677?text=')
        self.assertContains(respuesta, "fue%20cancelado")
        self.assertContains(respuesta, "Horario%3A%2010%3A30%20hs")

    def test_cancelar_dos_veces_avisa_que_ya_estaba(self):
        self._asignar()
        turno = self.paciente.turnos.get()
        self.client.post(f"/turnos/{turno.pk}/cancelar/")
        respuesta = self.client.post(f"/turnos/{turno.pk}/cancelar/", follow=True)
        self.assertContains(respuesta, "ya estaba cancelado")

    def test_historial_ofrece_aviso_de_turno_cancelado(self):
        self._asignar()
        turno = self.paciente.turnos.get()
        self.client.post(f"/turnos/{turno.pk}/cancelar/")
        respuesta = self.client.get(f"/pacientes/{self.paciente.pk}/")
        self.assertContains(respuesta, "fue%20cancelado")

    def test_hora_obligatoria_tambien_por_orden_de_llegada(self):
        self._asignar(hora="")
        self.assertEqual(Turno.objects.count(), 0)

    def test_hora_fuera_del_horario_se_rechaza(self):
        respuesta = self._asignar(hora="16:00")
        self.assertEqual(Turno.objects.count(), 0)
        self.assertContains(respuesta, "tiene que estar entre 09:00 y 14:00")

    def test_por_orden_dos_pacientes_pueden_tener_la_misma_hora(self):
        self._asignar()
        otro = Paciente.objects.create(nombre="Eva", apellido="Paz", dni="2", obra_social=self.obra)
        self.client.post("/turnos/nuevo/", {
            "paciente": otro.pk, "profesional": self.profesional.pk,
            "fecha": "2026-11-24", "hora": "10:30"})
        self.assertEqual(sorted(TurnoPorOrden.objects.values_list("numero_orden", flat=True)),
                         [1, 2])

    def test_turno_viejo_sin_hora_muestra_el_horario_de_atencion(self):
        self._asignar()
        TurnoPorOrden.objects.update(hora=None)
        turno = TurnoPorOrden.objects.get()
        self.assertIn("Horario: 09:00 a 14:00 hs", turno.texto_aviso())

    def test_sin_telefono_valido_no_hay_boton(self):
        Paciente.objects.update(telefono="4556677")
        self.assertNotContains(self._asignar(), "wa.me")


class ABMPacienteTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("secretario"))
        self.consultorio = Consultorio.objects.create(nombre="CMET")
        self.obra = ObraSocial.objects.create(nombre="Particular")
        self.paciente = Paciente.objects.create(
            nombre="Ana", apellido="Gómez", dni="1", telefono="2214556677",
            obra_social=self.obra, consultorio=self.consultorio)
        self.url_eliminar = f"/pacientes/{self.paciente.pk}/eliminar/"
        self.profesional = Profesional.objects.create(
            nombre="Karina", apellido="Estilarte", matricula="1",
            especialidad=Especialidad.objects.create(nombre="Pediatría"))

    def _turno(self, fecha, estado=Turno.ACTIVO):
        return TurnoPorOrden.objects.create(
            consultorio=self.consultorio, paciente=self.paciente, profesional=self.profesional,
            fecha=fecha, numero_orden=1, estado=estado)

    def _editar(self, **cambios):
        datos = {"nombre": "Ana", "apellido": "Gómez", "dni": "1",
                 "telefono": "2214556677", "obra_social": self.obra.pk, **cambios}
        return self.client.post(f"/pacientes/{self.paciente.pk}/editar/", datos, follow=True)

    def test_editar_guarda_cambios_y_no_crea_otro(self):
        self._editar(telefono="2215550000")
        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.telefono, "2215550000")
        self.assertEqual(Paciente.objects.count(), 1)

    def test_editar_muestra_los_datos_actuales(self):
        respuesta = self.client.get(f"/pacientes/{self.paciente.pk}/editar/")
        self.assertContains(respuesta, "Editar paciente")
        self.assertContains(respuesta, 'value="Gómez"')

    def test_editar_no_permite_dni_de_otro_paciente(self):
        Paciente.objects.create(nombre="Eva", apellido="Paz", dni="2", obra_social=self.obra)
        self._editar(dni="2")
        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.dni, "1")

    def test_eliminar_borra_paciente_y_turnos_pasados(self):
        self._turno(date.today() - timedelta(days=1))
        self.client.post(self.url_eliminar)
        self.assertEqual(Paciente.objects.count(), 0)
        self.assertEqual(Turno.objects.count(), 0)

    def test_eliminar_con_turno_cancelado_se_permite(self):
        self._turno(date.today() + timedelta(days=1), Turno.CANCELADO)
        self.client.post(self.url_eliminar)
        self.assertEqual(Paciente.objects.count(), 0)

    def test_no_elimina_con_turno_pendiente(self):
        self._turno(date.today())
        respuesta = self.client.post(self.url_eliminar, follow=True)
        self.assertEqual(Paciente.objects.count(), 1)
        self.assertContains(respuesta, "tiene turnos pendientes")

    def test_eliminar_por_get_no_borra(self):
        self.client.get(self.url_eliminar)
        self.assertEqual(Paciente.objects.count(), 1)

    def test_sin_login_no_elimina(self):
        self.client.logout()
        self.client.post(self.url_eliminar)
        self.assertEqual(Paciente.objects.count(), 1)


class FormatoTelefonoTests(TestCase):
    def test_formatos(self):
        casos = {
            "2214556677": "5492214556677",
            "221-455-6677": "5492214556677",
            "(0221) 15 455-6677": "5492214556677",
            "221 15 4556677": "5492214556677",
            "11 15 2345 6789": "5491123456789",
            "2325 15 456789": "5492325456789",
            "+54 9 221 455 6677": "5492214556677",
            "54 221 455 6677": "5492214556677",
            "4556677": "",
            "": "",
        }
        for telefono, esperado in casos.items():
            with self.subTest(telefono):
                turno = type("T", (), {"paciente": Paciente(telefono=telefono)})
                self.assertEqual(NotificacionWhatsApp(turno).destino(), esperado)
