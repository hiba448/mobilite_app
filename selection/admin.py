from django.contrib import admin
from .models import (
    ParametresSelection, DossierEtudiant, ResultatPasse1,
    ResultatPasse3, ConvocationEntretien, ResultatEntretien, AffectationFinale
)

admin.site.register(ParametresSelection)
admin.site.register(DossierEtudiant)
admin.site.register(ResultatPasse1)
admin.site.register(ResultatPasse3)
admin.site.register(ConvocationEntretien)
admin.site.register(ResultatEntretien)
admin.site.register(AffectationFinale)
