"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import path, include   
from rest_framework.authtoken.views import obtain_auth_token
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('aicha/', admin.site.urls),
    path("api/token/", obtain_auth_token),
    path("api/accounts/", include("accounts.urls")),
    path("api/student/", include("api_student.urls")),
    path("api/scolarite/", include("api_scolarite.urls")),
    path("api/sri/", include("api_sri.urls")),
    path("api/comite/", include("api_comite.urls")),
    path("api/partenaire/", include("api_partenaire.urls")),
    path("api/cf/", include("api_cf.urls")),
]

