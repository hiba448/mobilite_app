from django.utils import timezone
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Imports des modèles
from mobility.models import Campagne, Desiderata, OffrePartenaire
from selection.models import (
    ResultatPasse1, 
    ResultatPasse3, 
    AffectationFinale, 
    ConvocationEntretien, 
    ResultatEntretien,
    DossierEtudiant
)
from .permissions import IsStudent

def get_active_campaign():
    return Campagne.objects.filter(active=True).first()

def is_desiderata_window_open(c: Campagne) -> bool:
    if not c or not c.date_ouverture_desiderata or not c.date_cloture_desiderata:
        return False
    now = timezone.now()
    return c.date_ouverture_desiderata <= now <= c.date_cloture_desiderata

# =========================================================
# 1. INFOS ETUDIANT & DASHBOARD
# =========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_me(request):
    c = get_active_campaign()
    user = request.user
    
    if hasattr(user, 'etudiant'):
        etu = user.etudiant
        filiere = etu.filiere.nom if etu.filiere else "N/A"
        cne = etu.cne
    else:
        etu = None
        filiere = None
        cne = None

    role_value = user.profile.role if hasattr(user, "profile") else None
    deadline_open = is_desiderata_window_open(c) if c else False

    return Response({
        "username": user.username,
        "role": role_value,
        "cne": cne,
        "filiere": filiere,
        "campagne_active": f"Mobilité {c.annee}" if c else None,
        "deadline_desiderata_open": deadline_open,
    })


@api_view(['GET'])
@permission_classes([IsStudent])
def student_dashboard(request):
    user = request.user
    etu = user.etudiant
    c = get_active_campaign()
    
    if not c: return Response({"error": "Aucune campagne active"}, 404)

    # Récupération des infos
    dossier = DossierEtudiant.objects.filter(campagne=c, etudiant=etu).first()
    p1 = ResultatPasse1.objects.filter(campagne=c, etudiant=etu).first()
    p3 = ResultatPasse3.objects.filter(campagne=c, etudiant=etu).first()
    aff = AffectationFinale.objects.filter(campagne=c, etudiant=etu).select_related("partenaire").first()
    convoc = ConvocationEntretien.objects.filter(campagne=c, etudiant=etu).first()
    res_oral = ResultatEntretien.objects.filter(campagne=c, etudiant=etu).first()

    data = {
        "etudiant": {
            "nom": etu.nom,
            "prenom": etu.prenom,
            "cne": etu.cne,
            "filiere": etu.filiere.nom if etu.filiere else "N/A"
        },
        "campagne": {
            "annee": getattr(c, "annee", "En cours"),
            "titre": str(c)
        },
        "statuts": {
            "passe1": {
                "traite": p1 is not None,
                "eligible": p1.eligible if p1 else False,
                "moyenne": p1.moyenne_a1_sans_pfa if p1 else None,
                "motif": p1.motif_refus if p1 else None
            },
            "passe3_rank": {
                "traite": p3 is not None,
                "rang": p3.rang if p3 else None,
                "score": p3.note_selection if p3 else None,
            },
            "passe3_fifo": {
                "traite": aff is not None,
                "statut": aff.statut if aff else "EN_ATTENTE",
                "partenaire": aff.partenaire.nom_ecole if (aff and aff.partenaire) else None,
                "type_mobilite": aff.type_mobilite if aff else None
            },
            "passe4_entretien": {
                "convoque": convoc is not None,
                "message": convoc.message if convoc else None,
                "decision_finale": res_oral.decision if res_oral else None
            }
        }
    }
    return Response(data)


# =========================================================
# 2. GESTION DES VŒUX (CORRIGÉ)
# =========================================================

@api_view(['GET'])
@permission_classes([IsStudent])
def student_get_eligible_offers(request):
    etudiant = request.user.etudiant
    campagne = get_active_campaign()
    
    if not campagne: return Response({"detail": "Off"}, 404)

    # 1. Récupérer les offres compatibles
    offres = OffrePartenaire.objects.filter(
        campagne=campagne,
        filieres_ensias=etudiant.filiere 
    ).select_related('partenaire').distinct()

    offres_data = []
    for o in offres:
        if o.nb_places_ec > 0:
            offres_data.append({
                "id_offre": o.id, "type": "EC",
                "partenaire": o.partenaire.nom_ecole, "specialite": o.filiere_accueil,
                "places": o.nb_places_ec
            })
        if o.nb_places_dd > 0:
            offres_data.append({
                "id_offre": o.id, "type": "DD",
                "partenaire": o.partenaire.nom_ecole, "specialite": o.filiere_accueil,
                "places": o.nb_places_dd
            })

    # 2. ✅ CORRECTION : Récupérer les vœux déjà enregistrés !
    mes_voeux = Desiderata.objects.filter(campagne=campagne, etudiant=etudiant).order_by('priorite')
    
    voeux_data = []
    for v in mes_voeux:
        # On doit retrouver l'ID de l'offre originale pour que le React puisse afficher "Ajouté"
        offre_originale = OffrePartenaire.objects.filter(
            campagne=campagne,
            partenaire=v.partenaire,
            filiere_accueil=v.filiere_accueil
        ).first()

        voeux_data.append({
            "id_offre": offre_originale.id if offre_originale else None, # L'ID MANQUANT
            "priorite": v.priorite,
            "partenaire": v.partenaire.nom_ecole,
            "type": v.type_mobilite,
            "specialite": v.filiere_accueil
        })
            
    return Response({
        "offres_compatibles": offres_data, 
        "mes_voeux": voeux_data,  # <-- On envoie maintenant la vraie liste
        "is_open": is_desiderata_window_open(campagne)
    })


@api_view(['POST'])
@permission_classes([IsStudent])
def student_save_desiderata(request):
    etudiant = request.user.etudiant
    campagne = get_active_campaign()
    
    if not campagne:
        return Response({"detail": "Aucune campagne active."}, status=400)

    # Si tu veux bloquer la saisie après la date, décommente ceci :
    # if not is_desiderata_window_open(campagne):
    #     return Response({"detail": "La période de saisie est fermée."}, status=403)

    choices = request.data.get('choices', []) 
    
    if not isinstance(choices, list):
        return Response({"detail": "Format invalide."}, status=400)

    try:
        with transaction.atomic():
            # 1. Nettoyage
            Desiderata.objects.filter(campagne=campagne, etudiant=etudiant).delete()

            saved_count = 0
            
            # 2. Création
            for index, item in enumerate(choices):
                offre_id = item.get('id_offre')
                type_mob = item.get('type')

                if not offre_id or not type_mob: continue

                try:
                    offre = OffrePartenaire.objects.get(id=offre_id)
                except OffrePartenaire.DoesNotExist:
                    continue

                Desiderata.objects.create(
                    campagne=campagne,
                    etudiant=etudiant,
                    partenaire=offre.partenaire,
                    filiere_accueil=offre.filiere_accueil,
                    type_mobilite=type_mob,
                    priorite=index + 1,
                    statut='VALIDE'
                )
                saved_count += 1

        return Response({"message": f"{saved_count} vœux enregistrés avec succès !"}, status=200)

    except Exception as e:
        print(f"ERREUR SAVE DESIDERATA: {str(e)}")
        return Response({"detail": "Erreur serveur lors de l'enregistrement."}, status=500)