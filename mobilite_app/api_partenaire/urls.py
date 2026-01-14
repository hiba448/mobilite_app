from django.urls import path
from .views import partenaire_me, partenaire_offres, partenaire_candidats

urlpatterns = [
    path("me/", partenaire_me),
    path("offres/", partenaire_offres),
    path("candidats/", partenaire_candidats),
]