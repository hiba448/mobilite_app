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
    # Ta fonction de debug qui marche bien
    print(f"--- DEBUG PARTENAIRE pour {user.username} ---")
    if hasattr(user, 'profile') and hasattr(user.profile, 'partenaire'):
        return user.profile.partenaire
    if hasattr(user, 'partenaire'):
        return user.partenaire
    if hasattr(user, 'partenaire_profile'):
        if hasattr(user.partenaire_profile, 'partenaire'): 
            return user.partenaire_profile.partenaire
        return user.partenaire_profile
    return None

# ... (Les fonctions partenaire_me, partenaire_offres, partenaire_candidats restent inchangées) ...
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
    if not c: return Response([], status=200)
    p = get_user_partenaire(request.user)
    if not p: return Response({"detail": "Aucun partenaire lié."}, status=400)
    
    # On adapte pour éviter l'erreur si filiere_origine n'existe plus
    # On récupère juste les objets
    qs = OffrePartenaire.objects.filter(campagne=c, partenaire=p)
    return Response(OffrePartenaireSerializer(qs, many=True).data, status=200)

@api_view(["GET"])
@permission_classes([IsPartenaire])
def partenaire_candidats(request):
    c = get_active_campagne()
    if not c: return Response([], status=200)
    p = get_user_partenaire(request.user)
    if not p: return Response({"detail": "Aucun partenaire lié."}, status=400)
    qs = AffectationFinale.objects.filter(campagne=c, partenaire=p).select_related("etudiant", "etudiant__filiere")
    qs = qs.order_by("statut", "choix_obtenu", "etudiant__cne")
    return Response(CandidatPartenaireSerializer(qs, many=True).data, status=200)


# =========================================================
# ✅ LA FONCTION CORRIGÉE
# =========================================================

@api_view(['POST'])
@permission_classes([IsPartenaire])
def partenaire_create_offre(request):
    p = get_user_partenaire(request.user)
    if not p:
        return Response({"detail": "Compte non lié à un partenaire."}, status=403)

    c = get_active_campagne()
    if not c:
        return Response({"detail": "Aucune campagne active."}, status=400)

    try:
        filiere_accueil = request.data.get("specialite_accueil")
        nb_ec = int(request.data.get("places_ec", 0))
        nb_dd = int(request.data.get("places_dd", 0))

        if not filiere_accueil:
            return Response({"detail": "Le nom de la spécialité est obligatoire."}, status=400)

        # ✅ CORRECTION ICI : On ne passe plus 'filiere_origine'
        offre = OffrePartenaire.objects.create(
            campagne=c,
            partenaire=p,
            filiere_accueil=filiere_accueil,
            nb_places_ec=nb_ec,
            nb_places_dd=nb_dd
            # On a supprimé la ligne filiere_origine=None qui faisait planter
        )

        return Response({
            "message": "Offre créée avec succès ! Elle est en attente de validation par le SRI.",
            "id": offre.id
        }, status=201)

    except ValueError:
        return Response({"detail": "Les nombres de places doivent être des entiers."}, status=400)
    except Exception as e:
        # Affiche l'erreur exacte dans la console Django pour déboguer si besoin
        print(f"ERREUR CREATE OFFRE: {str(e)}")
        return Response({"detail": str(e)}, status=500)

# ... Imports existants ...
from django.shortcuts import get_object_or_404

@api_view(['POST']) # On utilise POST pour simplifier (ou PUT)
@permission_classes([IsPartenaire])
def partenaire_update_offre(request, offer_id):
    p = get_user_partenaire(request.user)
    if not p: return Response({"detail": "Non autorisé"}, 403)

    # On récupère l'offre en vérifiant qu'elle appartient bien à ce partenaire
    offre = get_object_or_404(OffrePartenaire, id=offer_id, partenaire=p)

    try:
        # Mise à jour des champs
        offre.filiere_accueil = request.data.get("specialite_accueil", offre.filiere_accueil)
        offre.nb_places_ec = int(request.data.get("places_ec", offre.nb_places_ec))
        offre.nb_places_dd = int(request.data.get("places_dd", offre.nb_places_dd))
        
        offre.save()
        
        return Response({"message": "Offre mise à jour avec succès !"}, status=200)

    except ValueError:
        return Response({"detail": "Les places doivent être des nombres entiers."}, status=400)
    except Exception as e:
        return Response({"detail": str(e)}, status=500)

@api_view(['DELETE'])
@permission_classes([IsPartenaire])
def partenaire_delete_offre(request, offer_id):
    p = get_user_partenaire(request.user)
    if not p: return Response({"detail": "Non autorisé"}, 403)

    # On récupère l'offre en s'assurant qu'elle appartient à ce partenaire
    offre = get_object_or_404(OffrePartenaire, id=offer_id, partenaire=p)

    try:
        offre.delete()
        return Response({"message": "Offre supprimée avec succès."}, status=200)
    except Exception as e:
        return Response({"detail": str(e)}, status=500)