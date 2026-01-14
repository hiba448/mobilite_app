from django.urls import path
from .views import student_me, student_desiderata, participants_above, student_options,student_dashboard

urlpatterns = [
    path("me/", student_me),
    path("desiderata/", student_desiderata),
    path("options/", student_options),  
    path("participants-above/", participants_above),
    path("me/", student_me),
    path("dashboard/", student_dashboard),
]
