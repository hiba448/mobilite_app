from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from mobility.models import Campagne
from selection.models import ConvocationEntretien, ResultatEntretien
from .permissions import IsComite
from .serializers import ConvocationSerializer, ResultatEntretienSerializer


def get_active_campagne():
    return Campagne.objects.filter(active=True).first()


@api_view(["GET"])
@permission_classes([IsComite])
def comite_dashboard(request):
    c = get_active_campagne()
    if not c:
        return Response({"detail": "Aucune campagne active."}, status=200)

    convoc = ConvocationEntretien.objects.filter(campagne=c).count()
    res = ResultatEntretien.objects.filter(campagne=c).count()
    retenus = ResultatEntretien.objects.filter(campagne=c, decision="RETENU").count()
    elimines = ResultatEntretien.objects.filter(campagne=c, decision="ELIMINE").count()
    attente = ResultatEntretien.objects.filter(campagne=c, decision="EN_ATTENTE").count()

    return Response({
        "campagne": {"id": c.id, "annee": getattr(c, "annee", None), "active": c.active},
        "stats": {
            "entretiens": {
                "convocations": convoc,
                "resultats": res,
                "retenus": retenus,
                "elimines": elimines,
                "en_attente": attente,
            }
        }
    }, status=200)


@api_view(["GET"])
@permission_classes([IsComite])
def comite_convocations(request):
    c = get_active_campagne()
    if not c:
        return Response([], status=200)

    qs = ConvocationEntretien.objects.filter(campagne=c).select_related("etudiant", "etudiant__filiere").order_by("etudiant__cne")
    data = ConvocationSerializer(qs, many=True).data
    return Response(data, status=200)


@api_view(["POST"])
@permission_classes([IsComite])
def comite_save_resultat(request):
    """
    Body JSON attendu:
    {
      "etudiant": 1,
      "present": true,
      "engagement_financier_ok": true,
      "motivation_ok": true,
      "decision": "RETENU"   // ou "ELIMINE" ou "EN_ATTENTE"
    }
    """
    c = get_active_campagne()
    if not c:
        return Response({"detail": "Aucune campagne active."}, status=400)

    etudiant_id = request.data.get("etudiant")
    if not etudiant_id:
        return Response({"detail": "Champ 'etudiant' obligatoire."}, status=400)

    # On vérifie que l'étudiant est convoqué
    ConvocationEntretien.objects.filter(campagne=c, etudiant_id=etudiant_id).get()

    obj, _ = ResultatEntretien.objects.update_or_create(
        campagne=c,
        etudiant_id=etudiant_id,
        defaults={
            "present": bool(request.data.get("present")),
            "engagement_financier_ok": bool(request.data.get("engagement_financier_ok")),
            "motivation_ok": bool(request.data.get("motivation_ok")),
            "decision": request.data.get("decision"),
        }
    )

    return Response(ResultatEntretienSerializer(obj).data, status=200)