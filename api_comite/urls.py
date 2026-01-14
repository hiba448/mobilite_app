from django.urls import path
from .views import comite_dashboard, comite_convocations, comite_save_resultat

urlpatterns = [
    path("dashboard/", comite_dashboard),
    path("convocations/", comite_convocations),
    path("resultats/", comite_save_resultat),
]