from django.urls import path
from .views import cf_dashboard, cf_students

urlpatterns = [
    path("dashboard/", cf_dashboard),
    path("students/", cf_students),
]