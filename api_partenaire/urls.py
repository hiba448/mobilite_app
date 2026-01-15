from django.urls import path
from .views import partenaire_me, partenaire_offres, partenaire_candidats, partenaire_create_offre, partenaire_update_offre, partenaire_delete_offre

urlpatterns = [
    path("me/", partenaire_me),
    path("offres/", partenaire_offres),
    path("candidats/", partenaire_candidats),
    path('offres/create/', partenaire_create_offre),
    path('offres/update/<int:offer_id>/', partenaire_update_offre),
    path('offres/delete/<int:offer_id>/', partenaire_delete_offre),
]