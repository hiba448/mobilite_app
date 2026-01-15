from django.utils import timezone
from django.core.management import call_command
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .permissions import IsSRI

# Imports des modèles
from mobility.models import Campagne, Desiderata, OffrePartenaire, Partenaire
from academic.models import Etudiant
from selection.models import (
    ParametresSelection,
    ResultatPasse1,
    ResultatPasse3,
    AffectationFinale,
    ConvocationEntretien,
    ResultatEntretien,
    DossierEtudiant # On ajoute juste ça au cas où
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
        # C'est ici que ça capture l'erreur si le script run_passe1 plante !
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
    nb_desid_valides = Desiderata.objects.filter(campagne=c).count() 

    nb_offres = OffrePartenaire.objects.filter(campagne=c).count()
    nb_partenaires = Partenaire.objects.count()

    nb_ranked = ResultatPasse3.objects.filter(campagne=c).count()

    nb_affect_non_publie = AffectationFinale.objects.filter(campagne=c, statut="NON_PUBLIE").count()
    nb_affect_attente = AffectationFinale.objects.filter(campagne=c, statut="LISTE_ATTENTE").count()
    nb_affect_non = AffectationFinale.objects.filter(campagne=c, statut="NON_RETENU").count()
    nb_affect_final = AffectationFinale.objects.filter(campagne=c, statut="AFFECTE").count()

    nb_convocations = ConvocationEntretien.objects.filter(campagne=c).count()
    nb_resultats_entretien = ResultatEntretien.objects.filter(campagne=c).count()

    # --- CORRECTION ICI : Utilisation du Singleton ---
    # Avant c'était : params, _ = ParametresSelection.objects.get_or_create(campagne=c)
    # Maintenant :
    params = ParametresSelection.get_solo()

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
            # Mapping vers tes noms de variables frontend
            "seuil1": params.seuil_eligibilite_p1,
            "seuil2": params.seuil_admissibilite_p2,
            "min_pct": getattr(params, 'min_pct', 10),
            "max_pct": getattr(params, 'max_pct', 30),
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

@api_view(["POST"])
@permission_classes([IsSRI])
def sri_run_command(request, cmd_name):
    ok, payload, code = run_cmd(cmd_name)
    return Response(payload, status=code)

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

# Routes Ouverture/Fermeture Desiderata
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

@api_view(["GET"])
@permission_classes([IsSRI])
def sri_details(request, data_type):
    c = get_active_campagne()
    if not c:
        return Response([])

    data = []

    if data_type == "eligibles":
        results = ResultatPasse1.objects.filter(campagne=c, eligible=True).select_related('etudiant__filiere')
        for r in results:
            data.append({
                "cne": r.etudiant.cne,
                "nom": r.etudiant.nom,
                "prenom": r.etudiant.prenom,
                "filiere": r.etudiant.filiere.nom if r.etudiant.filiere else "N/A",
                "score_1": r.moyenne_a1_sans_pfa, 
                "motif": "OK"
            })

    elif data_type == "recales":
        results = ResultatPasse1.objects.filter(campagne=c, eligible=False).select_related('etudiant__filiere')
        for r in results:
            data.append({
                "cne": r.etudiant.cne,
                "nom": r.etudiant.nom,
                "prenom": r.etudiant.prenom,
                "filiere": r.etudiant.filiere.nom if r.etudiant.filiere else "N/A",
                "score_1": r.moyenne_a1_sans_pfa,
                "motif": r.motif_refus
            })

    elif data_type == "classement":
        results = ResultatPasse3.objects.filter(campagne=c).order_by('rang').select_related('etudiant__filiere')
        for r in results:
            data.append({
                "rang": r.rang,
                "cne": r.etudiant.cne,
                "nom": f"{r.etudiant.nom} {r.etudiant.prenom}",
                "filiere": r.etudiant.filiere.nom if r.etudiant.filiere else "N/A",
                "score_total": r.note_selection,
            })

    elif data_type == "affectations":
        results = AffectationFinale.objects.filter(campagne=c).select_related('etudiant', 'partenaire')
        for r in results:
            dest = "-"
            if r.partenaire:
                dest = f"{r.partenaire.nom_ecole} ({r.type_mobilite})"
            
            data.append({
                "cne": r.etudiant.cne,
                "nom": f"{r.etudiant.nom} {r.etudiant.prenom}",
                "statut": r.statut,
                "destination": dest
            })

    return Response(data, status=200)


@api_view(["POST"])
@permission_classes([IsSRI])
def sri_reset_campaign(request):
    c = get_active_campagne()
    if not c:
        return Response({"detail": "Aucune campagne active."}, status=400)

    try:
        count_convoc = ConvocationEntretien.objects.filter(campagne=c).delete()[0]
        count_aff = AffectationFinale.objects.filter(campagne=c).delete()[0]
        count_rank = ResultatPasse3.objects.filter(campagne=c).delete()[0]
        count_p1 = ResultatPasse1.objects.filter(campagne=c).delete()[0]
        
        # On remet aussi à zéro les Dossiers pour être propre
        DossierEtudiant.objects.filter(campagne=c).update(
            eligible=None, motif=None, moyenne_calculee_p1=None,
            score_academique_p2=None, score_global=None, classement=None, decision_finale=None
        )

        msg = (
            f"Réinitialisation réussie ✅\n"
            f"- {count_convoc} Convocations supprimées\n"
            f"- {count_aff} Affectations supprimées\n"
            f"- {count_rank} Rangs supprimés\n"
            f"- {count_p1} Résultats éligibilité supprimés"
        )
        return Response({"ok": True, "detail": msg}, status=200)

    except Exception as e:
        return Response({"ok": False, "detail": str(e)}, status=500)

# ====================
# API POUR MODIFIER LES SEUILS (Indispensable)
# ====================
@api_view(['GET', 'POST'])
@permission_classes([IsSRI])
def manage_params(request):
    params = ParametresSelection.get_solo()

    if request.method == 'GET':
        return Response({
            "seuil_eligibilite_p1": params.seuil_eligibilite_p1,
            "seuil_admissibilite_p2": params.seuil_admissibilite_p2
        })

    elif request.method == 'POST':
        try:
            s1 = request.data.get('seuil1')
            s2 = request.data.get('seuil2')
            if s1 is not None: params.seuil_eligibilite_p1 = float(s1)
            if s2 is not None: params.seuil_admissibilite_p2 = float(s2)
            params.save()
            return Response({"message": "OK"})
        except ValueError:
            return Response({"error": "Erreur"}, status=400)


# ====================
# Dashboard Comité
# ====================
@api_view(["GET"])
@permission_classes([IsSRI]) 
def comite_dashboard(request):
    c = get_active_campagne()
    if not c: return Response([])

    candidats = AffectationFinale.objects.filter(
        campagne=c, 
        statut="CONVOQUE"
    ).select_related('etudiant', 'etudiant__filiere', 'partenaire')

    data = []
    for aff in candidats:
        deja_note = ResultatEntretien.objects.filter(campagne=c, etudiant=aff.etudiant).exists()
        data.append({
            "id": aff.etudiant.id,
            "cne": aff.etudiant.cne,
            "nom": aff.etudiant.nom,
            "prenom": aff.etudiant.prenom,
            "filiere": aff.etudiant.filiere.nom if aff.etudiant.filiere else "N/A",
            "destination": f"{aff.partenaire.nom_ecole} ({aff.type_mobilite})" if aff.partenaire else "Liste d'attente",
            "deja_note": deja_note
        })
    return Response(data, status=200)

@api_view(["POST"])
@permission_classes([IsSRI])
def comite_save_note(request):
    c = get_active_campagne()
    etudiant_id = request.data.get("etudiant_id")
    decision = request.data.get("decision")
    commentaire = request.data.get("commentaire", "")
    score_motivation = request.data.get("score_motivation", 0) 
    
    try:
        etu = Etudiant.objects.get(id=etudiant_id)
        ResultatEntretien.objects.update_or_create(
            campagne=c,
            etudiant=etu,
            defaults={
                "decision": decision,
                "commentaire": commentaire,
                "score": score_motivation,
                "present": True
            }
        )
        nouvel_statut = "ADMIS_DEFINITIF" if decision == "VALIDE" else "NON_RETENU"
        AffectationFinale.objects.filter(campagne=c, etudiant=etu).update(statut=nouvel_statut)
        return Response({"ok": True}, status=200)

    except Exception as e:
        return Response({"ok": False, "error": str(e)}, status=500)

from academic.models import Filiere
from mobility.models import OffrePartenaire

@api_view(['GET', 'POST'])
@permission_classes([IsSRI])
def manage_matrix(request):
    c = get_active_campagne()
    if not c: return Response({"detail": "Pas de campagne"}, 400)
    
    if request.method == 'GET':
        # On charge les offres
        offres = OffrePartenaire.objects.filter(campagne=c).select_related('partenaire').prefetch_related('filieres_ensias')
        
        data = []
        for o in offres:
            ids_filieres = list(o.filieres_ensias.values_list('id', flat=True))
            
            # Transition douce (si ancien champ)
            if not ids_filieres and hasattr(o, 'filiere_origine') and o.filiere_origine:
                ids_filieres = [o.filiere_origine.id]

            data.append({
                "id": o.id,
                "partenaire": o.partenaire.nom_ecole,
                # ❌ J'AI SUPPRIMÉ LA LIGNE "VILLE" ICI
                "specialite_partenaire": o.filiere_accueil,
                "ids_filieres": ids_filieres,
                "places_ec": o.nb_places_ec,
                "places_dd": o.nb_places_dd,
            })
        return Response(data, status=200)

    elif request.method == 'POST':
        offre_id = request.data.get("offre_id")
        filiere_ids = request.data.get("filiere_ids", []) 
        
        try:
            offre = OffrePartenaire.objects.get(id=offre_id)
            offre.filieres_ensias.set(filiere_ids)
            
            # Nettoyage ancien champ
            if hasattr(offre, 'filiere_origine'):
                offre.filiere_origine = None 
            
            offre.save()
            return Response({"message": "Alignement mis à jour !"}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
from academic.models import Filiere

@api_view(['GET'])
@permission_classes([IsSRI])
def get_all_filieres(request):
    """Renvoie la liste des filières (ID + Nom) pour les menus déroulants"""
    filieres = Filiere.objects.all().values('id', 'nom')
    return Response(list(filieres))