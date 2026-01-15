from django.urls import path
from .views import (
    manage_effectifs, 
    import_notes_s3, 
    import_notes_1a,
    # Assure-toi que ces vues existent aussi dans views.py si tu les utilises :
    import_admin_csv, 
    #import_notes_csv 
)

urlpatterns = [
    # 1. Gestion des Effectifs
    path('effectifs/', manage_effectifs),  # <--- Correction ici (C'était manage-effectifs/)

    # 2. Imports Phase 3
    path('import/s3/', import_notes_s3),   # <--- Correction ici (C'était import-notes-s3/)
    path('import/1a/', import_notes_1a),   # <--- Correction ici (C'était import-notes-1a/)

    # 3. Imports Legacy (Anciens)
    path('import-admin/', import_admin_csv),
    #path('import-csv/', import_notes_csv),
]