from django.utils import timezone
from django.core.management import call_command
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .permissions import IsSRI
from selection.models import ResultatEntretien, AffectationFinale, ConvocationEntretien
from academic.models import Etudiant
# Imports des modèles
from mobility.models import Campagne, Desiderata, OffrePartenaire, Partenaire, Alignement
from academic.models import Etudiant
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
    # Note: Vérifiez si vous avez un champ 'statut' dans Desiderata, sinon retirez le filter statut="VALIDE"
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

# Routes Run Command
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

# =========================================================
#  ZONE CORRIGÉE POUR L'ERREUR D'ATTRIBUTS
# =========================================================

@api_view(["GET"])
@permission_classes([IsSRI])
def sri_details(request, data_type):
    c = get_active_campagne()
    if not c:
        return Response([])

    data = []

    # 1. Liste des Éligibles
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

    # 2. Liste des Recalés (C'EST CE BLOC QUI MANQUAIT)
    elif data_type == "recales":
        results = ResultatPasse1.objects.filter(campagne=c, eligible=False).select_related('etudiant__filiere')
        for r in results:
            data.append({
                "cne": r.etudiant.cne,
                "nom": r.etudiant.nom,
                "prenom": r.etudiant.prenom,
                "filiere": r.etudiant.filiere.nom if r.etudiant.filiere else "N/A",
                "score_1": r.moyenne_a1_sans_pfa,
                "motif": r.motif_refus  # Affiche la raison (Redoublement, Note < 12.5...)
            })

    # 3. Classement Global
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

    # 4. Affectations Finales
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
from selection.models import ConvocationEntretien, ResultatEntretien, AffectationFinale

@api_view(["GET"])
@permission_classes([IsSRI]) # Ou une permission spécifique IsComite si vous en avez une
def comite_dashboard(request):
    """Renvoie la liste des étudiants convoqués pour le comité."""
    c = get_active_campagne()
    if not c:
        return Response([])

    # On récupère ceux qui ont le statut 'CONVOQUE' dans AffectationFinale
    # (C'est le statut qu'on a défini dans la Passe 4)
    candidats = AffectationFinale.objects.filter(
        campagne=c, 
        statut="CONVOQUE"
    ).select_related('etudiant', 'etudiant__filiere', 'partenaire')

    data = []
    for aff in candidats:
        # On regarde s'il a déjà une note d'entretien
        deja_note = ResultatEntretien.objects.filter(campagne=c, etudiant=aff.etudiant).exists()
        
        data.append({
            "id": aff.etudiant.id,
            "cne": aff.etudiant.cne,
            "nom": aff.etudiant.nom,
            "prenom": aff.etudiant.prenom,
            "filiere": aff.etudiant.filiere.nom,
            "destination": f"{aff.partenaire.nom_ecole} ({aff.type_mobilite})" if aff.partenaire else "Liste d'attente",
            "deja_note": deja_note
        })

    return Response(data, status=200)

@api_view(["POST"])
@permission_classes([IsSRI])
def comite_save_note(request):
    """Enregistre la décision du comité (Entretien)"""
    c = get_active_campagne()
    etudiant_id = request.data.get("etudiant_id")
    decision = request.data.get("decision") # 'VALIDE' ou 'REFUSE'
    commentaire = request.data.get("commentaire", "")
    
    # Critères PDF 
    score_motivation = request.data.get("score_motivation", 0) 
    
    try:
        etu = Etudiant.objects.get(id=etudiant_id)
        
        # 1. Sauvegarder le résultat de l'entretien
        ResultatEntretien.objects.update_or_create(
            campagne=c,
            etudiant=etu,
            defaults={
                "decision": decision,
                "commentaire": commentaire,
                "score": score_motivation, # On stocke une note globale ou spécifique
                "present": True
            }
        )

        # 2. Mettre à jour le statut final (Important pour la publication)
        # Si Validé -> 'ADMIS_DEFINITIF'
        # Si Refusé -> 'NON_RETENU' (Désistement ou échec entretien)
        nouvel_statut = "ADMIS_DEFINITIF" if decision == "VALIDE" else "NON_RETENU"
        
        AffectationFinale.objects.filter(campagne=c, etudiant=etu).update(
            statut=nouvel_statut
        )

        return Response({"ok": True}, status=200)

    except Exception as e:
        return Response({"ok": False, "error": str(e)}, status=500)     

@api_view(["GET"])
@permission_classes([IsSRI]) 
def comite_dashboard(request):
    """Renvoie la liste des étudiants convoqués pour le comité."""
    c = get_active_campagne()
    if not c:
        return Response([])

    # On récupère ceux qui ont le statut 'CONVOQUE' dans AffectationFinale
    candidats = AffectationFinale.objects.filter(
        campagne=c, 
        statut="CONVOQUE"
    ).select_related('etudiant', 'etudiant__filiere', 'partenaire')

    data = []
    for aff in candidats:
        # On regarde s'il a déjà une note d'entretien
        deja_note = ResultatEntretien.objects.filter(campagne=c, etudiant=aff.etudiant).exists()
        
        data.append({
            "id": aff.etudiant.id,
            "cne": aff.etudiant.cne,
            "nom": aff.etudiant.nom,
            "prenom": aff.etudiant.prenom,
            "filiere": aff.etudiant.filiere.nom,
            "destination": f"{aff.partenaire.nom_ecole} ({aff.type_mobilite})" if aff.partenaire else "Liste d'attente",
            "deja_note": deja_note
        })

    return Response(data, status=200)

@api_view(["POST"])
@permission_classes([IsSRI])
def comite_save_note(request):
    """Enregistre la décision du comité (Entretien)"""
    c = get_active_campagne()
    etudiant_id = request.data.get("etudiant_id")
    decision = request.data.get("decision") # 'VALIDE' ou 'REFUSE'
    commentaire = request.data.get("commentaire", "")
    score_motivation = request.data.get("score_motivation", 0) 
    
    try:
        etu = Etudiant.objects.get(id=etudiant_id)
        
        # 1. Sauvegarder le résultat de l'entretien
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

        # 2. Mettre à jour le statut final (Important pour la publication)
        nouvel_statut = "ADMIS_DEFINITIF" if decision == "VALIDE" else "NON_RETENU"
        
        AffectationFinale.objects.filter(campagne=c, etudiant=etu).update(
            statut=nouvel_statut
        )

        return Response({"ok": True}, status=200)

    except Exception as e:
        return Response({"ok": False, "error": str(e)}, status=500)

from selection.models import DossierEtudiant, ConvocationEntretien # Assurez-vous d'importer tous les modèles

@api_view(["POST"])
@permission_classes([IsSRI])
def sri_reset_campaign(request):
    """
    DANGER : Supprime tous les résultats calculés pour la campagne active.
    Ne supprime PAS les Desiderata ni les Notes, pour permettre de relancer l'algo.
    """
    c = get_active_campagne()
    if not c:
        return Response({"detail": "Aucune campagne active."}, status=400)

    try:
        # 1. Supprimer les Convocations (Passe 4)
        count_convoc = ConvocationEntretien.objects.filter(campagne=c).delete()[0]

        # 2. Supprimer les Affectations Finales (Passe 3 FIFO)
        count_aff = AffectationFinale.objects.filter(campagne=c).delete()[0]

        # 3. Supprimer le Classement (Passe 3 Rank)
        count_rank = ResultatPasse3.objects.filter(campagne=c).delete()[0]

        # 4. Supprimer les résultats d'éligibilité (Passe 1)
        count_p1 = ResultatPasse1.objects.filter(campagne=c).delete()[0]
        

        msg = (
            f"Réinitialisation réussie ✅\n"
            f"- {count_convoc} Convocations supprimées\n"
            f"- {count_aff} Affectations supprimées\n"
            f"- {count_rank} Rangs supprimés\n"
            f"- {count_p1} Résultats éligibilité supprimés\n"

        )
        return Response({"ok": True, "detail": msg}, status=200)

    except Exception as e:
        return Response({"ok": False, "detail": str(e)}, status=500)