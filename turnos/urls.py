from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.LoginConIntentos.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("turnos/nuevo/", views.dar_turno, name="dar_turno"),
    path("turnos/<int:pk>/cancelar/", views.cancelar_turno, name="cancelar_turno"),
    path("pacientes/", views.pacientes, name="pacientes"),
    path("pacientes/nuevo/", views.nuevo_paciente, name="nuevo_paciente"),
    path("pacientes/<int:pk>/", views.historial, name="historial"),
    path("pacientes/<int:pk>/editar/", views.editar_paciente, name="editar_paciente"),
    path("pacientes/<int:pk>/eliminar/", views.eliminar_paciente, name="eliminar_paciente"),
    path("profesionales/", views.profesionales, name="profesionales"),
]
