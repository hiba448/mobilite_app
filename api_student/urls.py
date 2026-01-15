from django.urls import path
from .views import (
    student_me,
    student_dashboard,
    student_get_eligible_offers,
    student_save_desiderata
)

urlpatterns = [
    # Infos de base et Timeline
    path('me/', student_me),
    path('dashboard/', student_dashboard),

    # Nouvelle gestion des vœux (Phase 2)
    path('desiderata/offres/', student_get_eligible_offers), # Récupère les offres compatibles
    path('desiderata/save/', student_save_desiderata),       # Sauvegarde les choix
]