"""Aviso al paciente por WhatsApp cuando se le da o se le cancela un turno."""

import re
from urllib.parse import quote


class NotificacionWhatsApp:
    """No envía sola: arma el enlace que abre WhatsApp con el mensaje ya escrito."""

    def __init__(self, turno):
        self.turno = turno
        self.paciente = turno.paciente

    def destino(self):
        """Número en formato internacional (549 + 10 dígitos), o "" si no es válido."""
        numero = re.sub(r"\D", "", self.paciente.telefono)
        numero = re.sub(r"^(54)?9?(?=\d{10,12}$)", "", numero).lstrip("0")
        numero = self._sin_15(numero)
        return f"549{numero}" if len(numero) == 10 else ""

    def disponible(self):
        return bool(self.destino())

    def enlace(self):
        return f"https://wa.me/{self.destino()}?text={quote(self.turno.texto_aviso())}"

    @staticmethod
    def _sin_15(numero):
        """Saca el 15 del celular, que va después de la característica: 221 15 4556677."""
        if len(numero) == 12:
            for corte in (2, 3, 4):
                if numero[corte:corte + 2] == "15":
                    return numero[:corte] + numero[corte + 2:]
        return numero
