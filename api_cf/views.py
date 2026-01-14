from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .permissions import IsCF

from mobility.models import Campagne
from academic.models import Etudiant
from selection.models import ResultatPasse1, ResultatPasse3, AffectationFinale, ResultatEntretien
from academic.models import MoyenneS3
from selection.utils import mediane_s3_filiere


def get_active_campagne():
    return Campagne.objects.filter(active=True).first()


def get_user_filiere(user):
    # on suppose que user.profile.filiere existe (comme partenaire)
    if hasattr(user, "profile") and getattr(user.profile, "filiere", None):
        return user.profile.filiere
    return None


@api_view(["GET"])
@permission_classes([IsCF])
def cf_dashboard(request):
    c = get_active_campagne()
    f = get_user_filiere(request.user)

    if not c:
        return Response({"detail": "Aucune campagne active."}, status=200)

    deadline_open = False
    if c.date_ouverture_desiderata and c.date_cloture_desiderata:
        now = timezone.now()
        deadline_open = (c.date_ouverture_desiderata <= now <= c.date_cloture_desiderata)

    # stats filière
    etus = Etudiant.objects.filter(filiere=f) if f else Etudiant.objects.none()
    nb_etudiants = etus.count()

    nb_eligibles = ResultatPasse1.objects.filter(campagne=c, etudiant__filiere=f, eligible=True).count() if f else 0
    nb_non_eligibles = ResultatPasse1.objects.filter(campagne=c, etudiant__filiere=f, eligible=False).count() if f else 0

    nb_ranked = ResultatPasse3.objects.filter(campagne=c, filiere=f).count() if f else 0

    nb_affect_non_publie = AffectationFinale.objects.filter(campagne=c, etudiant__filiere=f, statut="NON_PUBLIE").count() if f else 0
    nb_affect_attente = AffectationFinale.objects.filter(campagne=c, etudiant__filiere=f, statut="LISTE_ATTENTE").count() if f else 0
    nb_affect_non = AffectationFinale.objects.filter(campagne=c, etudiant__filiere=f, statut="NON_RETENU").count() if f else 0
    nb_affect_ok = AffectationFinale.objects.filter(campagne=c, etudiant__filiere=f, statut="AFFECTE").count() if f else 0

    # médiane S3 filière (si dispo)
    med = None
    if f:
        med = mediane_s3_filiere(c, f)

    return Response({
        "campagne_active": {
            "id": c.id,
            "annee": c.annee,
            "deadline_desiderata_open": deadline_open,
        },
        "filiere": (f.nom if f else None),
        "stats": {
            "nb_etudiants": nb_etudiants,
            "passe1": {"eligibles": nb_eligibles, "non_eligibles": nb_non_eligibles},
            "ranking_passe3": nb_ranked,
            "affectations": {
                "non_publie": nb_affect_non_publie,
                "liste_attente": nb_affect_attente,
                "non_retenu": nb_affect_non,
                "affecte": nb_affect_ok,
            },
            "mediane_s3": med,
        }
    }, status=200)


@api_view(["GET"])
@permission_classes([IsCF])
def cf_students(request):
    """
    Liste des étudiants de la filière du CF avec infos utiles.
    """
    c = get_active_campagne()
    f = get_user_filiere(request.user)

    if not c or not f:
        return Response([], status=200)

    qs = Etudiant.objects.filter(filiere=f).order_by("cne")

    data = []
    for e in qs:
        p1 = ResultatPasse1.objects.filter(campagne=c, etudiant=e).first()
        p3 = ResultatPasse3.objects.filter(campagne=c, etudiant=e).first()
        aff = AffectationFinale.objects.filter(campagne=c, etudiant=e).select_related("partenaire").first()
        ent = ResultatEntretien.objects.filter(campagne=c, etudiant=e).first()
        s3 = MoyenneS3.objects.filter(campagne=c, etudiant=e).first()

        data.append({
            "cne": e.cne,
            "nom": e.nom,
            "prenom": e.prenom,
            "filiere": f.nom,
            "passe1_eligible": (p1.eligible if p1 else None),
            "note_selection": (float(p3.note_selection) if p3 and p3.note_selection is not None else None),
            "rang": (p3.rang if p3 else None),
            "affectation": {
                "statut": (aff.statut if aff else None),
                "partenaire": (aff.partenaire.nom_ecole if aff and aff.partenaire else None),
                "type_mobilite": (aff.type_mobilite if aff else None),
                "choix_obtenu": (aff.choix_obtenu if aff else None),
            },
            "entretien_decision": (ent.decision if ent else None),
            "moy_s3": (float(s3.moy_s3_avant_rattrapage) if s3 else None),
        })

    return Response(data, status=200)
