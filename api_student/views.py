from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from mobility.models import Campagne, Desiderata, Alignement
from selection.models import ResultatPasse1, ResultatPasse3, AffectationFinale
from academic.models import Etudiant

from .serializers import StudentMeSerializer, DesiderataSerializer


def get_active_campaign():
    return Campagne.objects.filter(active=True).first()


def is_desiderata_window_open(c: Campagne) -> bool:
    """
    True si now est entre date_ouverture_desiderata et date_cloture_desiderata.
    Compatible dates naïves / aware (timezone).
    """
    if not c or not c.date_ouverture_desiderata or not c.date_cloture_desiderata:
        return False

    now = timezone.now()
    start = c.date_ouverture_desiderata
    end = c.date_cloture_desiderata

    # rendre comparables (aware)
    if timezone.is_naive(start):
        start = timezone.make_aware(start)
    if timezone.is_naive(end):
        end = timezone.make_aware(end)

    return start <= now <= end


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_me(request):
    c = get_active_campaign()

    # rôle via Profile
    prof = getattr(request.user, "profile", None)
    role_value = prof.role if prof else None

    # user -> etudiant
    etu = Etudiant.objects.filter(user=request.user).select_related("filiere").first()

    eligible = False
    rang = None
    statut_aff = None

    if c and etu:
        eligible = ResultatPasse1.objects.filter(
            campagne=c, etudiant=etu, eligible=True
        ).exists()

        rp3 = ResultatPasse3.objects.filter(campagne=c, etudiant=etu).first()
        if rp3:
            rang = getattr(rp3, "rang", None)

        aff = AffectationFinale.objects.filter(campagne=c, etudiant=etu).first()
        if aff:
            statut_aff = getattr(aff, "statut", None)

    deadline_open = is_desiderata_window_open(c) if c else False

    payload = {
        "username": request.user.username,
        "role": role_value,
        "cne": etu.cne if etu else None,
        "filiere": etu.filiere.nom if (etu and etu.filiere) else None,
        "eligible_passe1": eligible,
        "statut": statut_aff,
        "rang": rang,
        "campagne_active": f"Mobilité {c.annee}" if c else None,
        "deadline_desiderata_open": deadline_open,
    }
    return Response(StudentMeSerializer(payload).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def student_desiderata(request):
    c = get_active_campaign()
    if not c:
        return Response({"detail": "Aucune campagne active."}, status=status.HTTP_400_BAD_REQUEST)

    etu = Etudiant.objects.filter(user=request.user).select_related("filiere").first()
    if not etu:
        return Response({"detail": "Aucun étudiant lié à ce compte."}, status=status.HTTP_400_BAD_REQUEST)

    # éligibilité passe 1
    if not ResultatPasse1.objects.filter(campagne=c, etudiant=etu, eligible=True).exists():
        return Response({"detail": "Étudiant non éligible (Passe 1)."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        des = (
            Desiderata.objects
            .filter(campagne=c, etudiant=etu)
            .order_by("priorite")
            .select_related("partenaire")
        )
        out = [
            {
                "priorite": d.priorite,
                "partenaire": d.partenaire.nom_ecole,
                "filiere_accueil": d.filiere_accueil,
                "type_mobilite": d.type_mobilite,
                "statut": getattr(d, "statut", None),
            }
            for d in des
        ]
        return Response(out, status=status.HTTP_200_OK)

    # POST : saisie / remplacement desiderata
    if not is_desiderata_window_open(c):
        return Response({"detail": "Deadline dépassée. Modification interdite."}, status=status.HTTP_403_FORBIDDEN)

    ser = DesiderataSerializer(data=request.data, many=True)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    # Validation : alignement obligatoire
    for item in data:
        partenaire_nom = item["partenaire"]
        filiere_accueil = item["filiere_accueil"]
        type_mobilite = item["type_mobilite"]

        ok = Alignement.objects.filter(
            campagne=c,
            filiere_origine=etu.filiere,
            partenaire__nom_ecole=partenaire_nom,
            filiere_accueil=filiere_accueil,
            type_mobilite=type_mobilite,
        ).exists()

        if not ok:
            return Response(
                {"detail": f"Choix non autorisé par l’alignement: {partenaire_nom} / {filiere_accueil} / {type_mobilite}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Remplacement complet
    Desiderata.objects.filter(campagne=c, etudiant=etu).delete()

    for item in data:
        # on récupère partenaire_id via alignement
        partenaire_id = (
            Alignement.objects.filter(
                campagne=c,
                filiere_origine=etu.filiere,
                partenaire__nom_ecole=item["partenaire"],
                filiere_accueil=item["filiere_accueil"],
                type_mobilite=item["type_mobilite"],
            )
            .values_list("partenaire_id", flat=True)
            .first()
        )

        Desiderata.objects.create(
            campagne=c,
            etudiant=etu,
            priorite=item["priorite"],
            partenaire_id=partenaire_id,
            filiere_accueil=item["filiere_accueil"],
            type_mobilite=item["type_mobilite"],
            statut="SAISI",
        )

    return Response({"detail": "Desiderata enregistrés."}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def participants_above(request):
    c = get_active_campaign()
    if not c:
        return Response([], status=status.HTTP_200_OK)

    etu = Etudiant.objects.filter(user=request.user).first()
    if not etu:
        return Response([], status=status.HTTP_200_OK)

    rp3 = ResultatPasse3.objects.filter(campagne=c, etudiant=etu).first()
    rang = getattr(rp3, "rang", None) if rp3 else None
    if rang is None:
        return Response([], status=status.HTTP_200_OK)

    better = ResultatPasse3.objects.filter(campagne=c, rang__lt=rang).order_by("rang")

    # anonymisé : seulement rang
    return Response([{"rang": x.rang} for x in better], status=status.HTTP_200_OK)