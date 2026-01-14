from django.utils import timezone
from django.core.management import call_command

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .permissions import IsSRI

from mobility.models import Campagne, Desiderata, OffrePartenaire, Partenaire
from selection.models import (
    ParametresSelection,
    ResultatPasse1,
    ResultatPasse3,
    AffectationFinale,
    ConvocationEntretien,
    ResultatEntretien,
)


ALLOWED_COMMANDS = {
    "run_passe1",
    "run_passe3_rank",
    "run_passe3_fifo",
    "run_passe4_convocations",
    "run_passe4_finalize",
}


def get_active_campagne():
    return Campagne.objects.filter(active=True).first()


def run_cmd(cmd_name: str):
    """Helper: exécute une commande si autorisée."""
    if cmd_name not in ALLOWED_COMMANDS:
        return False, {"detail": "Commande non autorisée."}, 400
    try:
        call_command(cmd_name)
        return True, {"ok": True, "command": cmd_name}, 200
    except Exception as e:
        return False, {"ok": False, "command": cmd_name, "error": str(e)}, 500


@api_view(["GET"])
@permission_classes([IsSRI])
def sri_dashboard(request):
    c = get_active_campagne()
    if not c:
        return Response({"detail": "Aucune campagne active."}, status=200)

    now = timezone.now()
    deadline_open = False
    if c.date_ouverture_desiderata and c.date_cloture_desiderata:
        deadline_open = (c.date_ouverture_desiderata <= now <= c.date_cloture_desiderata)

    # Stats
    nb_passe1_eligibles = ResultatPasse1.objects.filter(campagne=c, eligible=True).count()
    nb_passe1_non_eligibles = ResultatPasse1.objects.filter(campagne=c, eligible=False).count()

    nb_desid_total = Desiderata.objects.filter(campagne=c).count()
    nb_desid_valides = Desiderata.objects.filter(campagne=c, statut="VALIDE").count()

    nb_offres = OffrePartenaire.objects.filter(campagne=c).count()
    nb_partenaires = Partenaire.objects.count()

    nb_ranked = ResultatPasse3.objects.filter(campagne=c).count()

    nb_affect_non_publie = AffectationFinale.objects.filter(campagne=c, statut="NON_PUBLIE").count()
    nb_affect_attente = AffectationFinale.objects.filter(campagne=c, statut="LISTE_ATTENTE").count()
    nb_affect_non = AffectationFinale.objects.filter(campagne=c, statut="NON_RETENU").count()
    nb_affect_final = AffectationFinale.objects.filter(campagne=c, statut="AFFECTE").count()

    nb_convocations = ConvocationEntretien.objects.filter(campagne=c).count()
    nb_resultats_entretien = ResultatEntretien.objects.filter(campagne=c).count()

    params, _ = ParametresSelection.objects.get_or_create(campagne=c)

    return Response({
        "campagne": {
            "id": c.id,
            "annee": getattr(c, "annee", None),
            "active": c.active,
            "date_ouverture_desiderata": c.date_ouverture_desiderata,
            "date_cloture_desiderata": c.date_cloture_desiderata,
            "deadline_desiderata_open": deadline_open,
        },
        "parametres_selection": {
            "seuil1": float(params.seuil1),
            "seuil2": float(params.seuil2),
            "min_pct": float(params.min_pct),
            "max_pct": float(params.max_pct),
        },
        "stats": {
            "passe1": {
                "eligibles": nb_passe1_eligibles,
                "non_eligibles": nb_passe1_non_eligibles,
            },
            "desiderata": {
                "total": nb_desid_total,
                "valides": nb_desid_valides,
            },
            "offres": nb_offres,
            "partenaires": nb_partenaires,
            "ranking_passe3": nb_ranked,
            "affectations": {
                "non_publie": nb_affect_non_publie,
                "liste_attente": nb_affect_attente,
                "non_retenu": nb_affect_non,
                "affecte": nb_affect_final,
            },
            "entretiens": {
                "convocations": nb_convocations,
                "resultats": nb_resultats_entretien,
            }
        }
    }, status=200)


# ✅ Route générique (on la garde)
@api_view(["POST"])
@permission_classes([IsSRI])
def sri_run_command(request, cmd_name):
    ok, payload, code = run_cmd(cmd_name)
    return Response(payload, status=code)


# ✅ Routes explicites (plus simples pour le front)
@api_view(["POST"])
@permission_classes([IsSRI])
def sri_run_passe1(request):
    ok, payload, code = run_cmd("run_passe1")
    return Response(payload, status=code)


@api_view(["POST"])
@permission_classes([IsSRI])
def sri_run_passe3_rank(request):
    ok, payload, code = run_cmd("run_passe3_rank")
    return Response(payload, status=code)


@api_view(["POST"])
@permission_classes([IsSRI])
def sri_run_passe3_fifo(request):
    ok, payload, code = run_cmd("run_passe3_fifo")
    return Response(payload, status=code)


@api_view(["POST"])
@permission_classes([IsSRI])
def sri_run_passe4_convocations(request):
    ok, payload, code = run_cmd("run_passe4_convocations")
    return Response(payload, status=code)


@api_view(["POST"])
@permission_classes([IsSRI])
def sri_run_passe4_finalize(request):
    ok, payload, code = run_cmd("run_passe4_finalize")
    return Response(payload, status=code)


@api_view(["POST"])
@permission_classes([IsSRI])
def sri_open_desiderata(request):
    c = get_active_campagne()
    if not c:
        return Response({"detail": "Aucune campagne active."}, status=400)

    now = timezone.now()
    close = now + timezone.timedelta(days=7)

    c.date_ouverture_desiderata = now
    c.date_cloture_desiderata = close
    c.save()

    return Response({"ok": True, "opened": c.date_ouverture_desiderata, "closes": c.date_cloture_desiderata}, status=200)


@api_view(["POST"])
@permission_classes([IsSRI])
def sri_close_desiderata(request):
    c = get_active_campagne()
    if not c:
        return Response({"detail": "Aucune campagne active."}, status=400)

    c.date_cloture_desiderata = timezone.now()
    c.save()
    return Response({"ok": True, "closed": c.date_cloture_desiderata}, status=200)