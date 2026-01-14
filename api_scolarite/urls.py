from django.urls import path
from .views import import_admin_csv, import_notes_csv

urlpatterns = [
    path('import-csv/', import_notes_csv),
    path('import-admin/', import_admin_csv),  # <--- NOUVELLE ROUTE
    path('import-csv/', import_notes_csv),
]