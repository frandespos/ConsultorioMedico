# Sistema de Turnos - Consultorio Médico El Toboso (CMET)

Parcial  - Algoritmos y Estructuras de Datos III - ISFT N° 210



### Requisitos

- [Python](https://www.python.org/downloads/) 3.10 o superior. 
- [Git](https://git-scm.com/downloads).

Para comprobar que están instalados:

```bash
python3 --version
git --version
```

### Instalación


```bash
cd ~/Documents
git clone https://github.com/frandespos/ConsultorioMedico.git
cd ConsultorioMedico
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_datos
python manage.py runserver
```

En Windows, usar `python` en lugar de `python3` y activar el entorno con `venv\Scripts\activate`.

### Ingreso

Entrar a http://127.0.0.1:8000 con usuario `secretario` y contraseña `cmet2026`.

El sistema arranca con los profesionales y las obras sociales cargados, pero sin pacientes ni turnos.

### Para volver a abrirlo

```bash
cd ~/Documents/ConsultorioMedico
source venv/bin/activate
python manage.py runserver
```

Para detener el servidor, presionar `Ctrl + C`.

### Tests

```bash
python manage.py test
```

## Avisos al paciente

En la Agenda y el Historial hay un botón que abre WhatsApp con el mensaje del turno ya escrito, y al cancelar aparece un enlace para avisar por ese medio. El enlace lo arma `NotificacionWhatsApp` en `turnos/notificaciones.py`.

## Dónde está la POO

Todo el modelo está en `turnos/models.py`.

| Concepto | Dónde |
|---|---|
| Encapsulamiento | La lógica de turnos está dentro de `Consultorio.dar_turno()` con métodos internos `_validar_hora()`, `_proximo_numero_orden()`. La contraseña la maneja `User` de Django (hasheada). |
| Herencia | `Persona` (abstracta) → `Paciente`, `Profesional`, `Secretario`. `Turno` → `TurnoProgramado`, `TurnoPorOrden` |
| Polimorfismo | `mostrar_datos()`, `get_tipo()`, `get_detalle()` redefinidos en cada subclase |
| Asociación | `Turno`–`Paciente`, `Turno`–`Profesional`, `Profesional`–`Especialidad`, `Paciente`/`Profesional`–`ObraSocial` |
| Agregación | `Consultorio` → `Profesional`, `Paciente` (`on_delete=SET_NULL`) |
| Composición | `Profesional` → `HorarioAtencion`, `Consultorio` → `Turno` (`on_delete=CASCADE`) |
