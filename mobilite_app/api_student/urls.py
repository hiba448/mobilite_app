from django.urls import path
from .views import student_me, student_desiderata, participants_above

urlpatterns = [
    path("me/", student_me),
    path("desiderata/", student_desiderata),
    path("participants-above/", participants_above),
]