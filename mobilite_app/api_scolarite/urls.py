from django.urls import path
from .views import upload_notes_csv, upload_s3_csv

urlpatterns = [
    path("upload-notes/", upload_notes_csv),
    path("upload-s3/", upload_s3_csv),
]