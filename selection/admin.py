from django.contrib import admin
from .models import (
    ParametresSelection,
    DossierEtudiant,
    ResultatPasse1,    # ✅ On l'a gardé
    ResultatPasse3,    # ✅ On l'a gardé
    ConvocationEntretien,
    ResultatEntretien, # ✅ On l'a gardé
    AffectationFinale
)

@admin.register(ParametresSelection)
class ParametresSelectionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'seuil_eligibilite_p1')

@admin.register(DossierEtudiant)
class DossierEtudiantAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'campagne', 'moyenne_calculee_p1', 'eligible', 'decision_finale')
    list_filter = ('campagne', 'eligible', 'redoublement_a1', 'blame')
    search_fields = ('etudiant__cne',)

@admin.register(ResultatPasse1)
class ResultatPasse1Admin(admin.ModelAdmin):
    list_display = ('etudiant', 'eligible', 'moyenne_a1_sans_pfa')

@admin.register(ResultatPasse3)
class ResultatPasse3Admin(admin.ModelAdmin):
    list_display = ('etudiant', 'score_final', 'rang')

@admin.register(ConvocationEntretien)
class ConvocationEntretienAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'statut_convocation', 'date_entretien')

@admin.register(AffectationFinale)
class AffectationFinaleAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'partenaire', 'statut')