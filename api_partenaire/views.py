from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from mobility.models import Campagne, Partenaire, OffrePartenaire
from selection.models import AffectationFinale

from .permissions import IsPartenaire
from .serializers import OffrePartenaireSerializer, CandidatPartenaireSerializer


def get_active_campagne():
    return Campagne.objects.filter(active=True).first()


def get_user_partenaire(user):
    if hasattr(user, "profile") and getattr(user.profile, "partenaire", None):
        return user.profile.partenaire
    return None

@api_view(["GET"])
@permission_classes([IsPartenaire])
def partenaire_me(request):
    p = get_user_partenaire(request.user)
    c = get_active_campagne()

    deadline_open = False
    if c and c.date_ouverture_desiderata and c.date_cloture_desiderata:
        now = timezone.now()
        deadline_open = (c.date_ouverture_desiderata <= now <= c.date_cloture_desiderata)

    return Response({
        "username": request.user.username,
        "partenaire": (p.nom_ecole if p else None),
        "campagne_active": (getattr(c, "annee", None) if c else None),
        "deadline_desiderata_open": deadline_open,
    }, status=200)


@api_view(["GET"])
@permission_classes([IsPartenaire])
def partenaire_offres(request):
    c = get_active_campagne()
    if not c:
        return Response([], status=200)

    p = get_user_partenaire(request.user)
    if not p:
        return Response({"detail": "Aucun partenaire lié à cet utilisateur."}, status=400)

    qs = OffrePartenaire.objects.filter(campagne=c, partenaire=p).select_related("partenaire", "filiere_origine")
    return Response(OffrePartenaireSerializer(qs, many=True).data, status=200)


@api_view(["GET"])
@permission_classes([IsPartenaire])
def partenaire_candidats(request):
    c = get_active_campagne()
    if not c:
        return Response([], status=200)

    p = get_user_partenaire(request.user)
    if not p:
        return Response({"detail": "Aucun partenaire lié à cet utilisateur."}, status=400)

    qs = AffectationFinale.objects.filter(campagne=c, partenaire=p).select_related("etudiant", "etudiant__filiere")
    # Tri: statut puis rang/choix si tu veux (simple ici)
    qs = qs.order_by("statut", "choix_obtenu", "etudiant__cne")

    return Response(CandidatPartenaireSerializer(qs, many=True).data, status=200)