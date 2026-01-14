from django.urls import path
from .views import (
    sri_dashboard,

    # générique
    sri_run_command,

    # explicites
    sri_run_passe1,
    sri_run_passe3_rank,
    sri_run_passe3_fifo,
    sri_run_passe4_convocations,
    sri_run_passe4_finalize,

    sri_open_desiderata,
    sri_close_desiderata,
)

urlpatterns = [
    path("dashboard/", sri_dashboard),

    # ✅ routes explicites (recommandées pour le front)
    path("run/passe1/", sri_run_passe1),
    path("run/passe3-rank/", sri_run_passe3_rank),
    path("run/passe3-fifo/", sri_run_passe3_fifo),
    path("run/passe4-convocations/", sri_run_passe4_convocations),
    path("run/passe4-finalize/", sri_run_passe4_finalize),

    # ✅ route générique (tu peux la garder aussi)
    path("run/<str:cmd_name>/", sri_run_command),

    path("desiderata/open/", sri_open_desiderata),
    path("desiderata/close/", sri_close_desiderata),
]