from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.email_login, name="login"),
    path("logout/", views.email_logout, name="logout"),
    path("", views.home, name="home"),
    path("processo/<int:processo_id>/", views.processo_detail, name="processo_detail"),
    path("processo/<int:processo_id>/toggle/", views.toggle_processo, name="toggle_processo"),
    path("processo/<int:processo_id>/add-candidato/", views.add_candidato, name="add_candidato"),
    path("aplicacao/<int:aplicacao_id>/avaliar/", views.avaliar_aplicacao, name="avaliar_aplicacao"),
    path("emails/", views.manage_emails, name="manage_emails"),
]
