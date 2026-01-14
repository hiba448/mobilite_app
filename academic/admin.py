from django.contrib import admin
from .models import Filiere, Module, Etudiant, NoteModule

admin.site.register(Filiere)
admin.site.register(Module)
admin.site.register(Etudiant)
admin.site.register(NoteModule)