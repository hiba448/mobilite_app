import math
from django.core.management.base import BaseCommand
from mobility.models import Campagne, Desiderata, OffrePartenaire, Alignement
from selection.models import ParametresSelection, ResultatPasse3, AffectationFinale
from academic.models import Etudiant

class Command(BaseCommand):
    help = "Passe 3 (étape 2): Affectation FIFO avec Quotas (10%-30%) et Seuil Dynamique (13.5 -> 12.5)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("--- Démarrage Affectation FIFO (Quotas & Seuil Dynamique) ---"))
        
        # 1. Initialisation Campagne
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne:
            self.stdout.write(self.style.ERROR("Aucune campagne active."))
            return

        # Paramètres (Valeurs par défaut du PDF si absentes en base)
        params, _ = ParametresSelection.objects.get_or_create(campagne=campagne)
        SEUIL1 = 12.5  # Seuil d'élimination absolue (C1.3 & Règle 3.5.2)
        SEUIL2 = 13.5  # Seuil standard de sélection (Règle 4)
        
        # 2. Chargement des Capacités (Offres)
        capacities = {}
        # Priorité : OffrePartenaire, sinon Alignement (Roue de secours)
        offers = OffrePartenaire.objects.filter(campagne=campagne)
        if offers.exists():
            for off in offers:
                capacities[(off.partenaire_id, off.filiere_origine_id, off.filiere_accueil, "EC")] = off.nb_places_ec
                capacities[(off.partenaire_id, off.filiere_origine_id, off.filiere_accueil, "DD")] = off.nb_places_dd
        else:
            self.stdout.write(self.style.WARNING("⚠ Pas d'offres trouvées. Utilisation des Alignements (5 places défaut)."))
            for ali in Alignement.objects.filter(campagne=campagne):
                key = (ali.partenaire_id, ali.filiere_origine_id, ali.filiere_accueil, ali.type_mobilite)
                capacities[key] = 5

        # 3. Calcul des Quotas par Filière (Règle 3.5.1)
        # On doit savoir combien d'étudiants sont éligibles par filière pour calculer les 10% et 30%
        # On interroge ResultatPasse3 pour avoir l'effectif total classé par filière
        from django.db.models import Count
        stats_filiere = ResultatPasse3.objects.filter(campagne=campagne).values('filiere').annotate(total=Count('id'))
        
        quotas = {} # {filiere_id: {'min': 5, 'max': 15, 'assigned': 0}}
        
        for item in stats_filiere:
            f_id = item['filiere']
            total = item['total']
            
            # Formule: arrondi à partie entière + 1
            q_min = math.floor(total * 0.10) + 1
            q_max = math.floor(total * 0.30) + 1
            
            quotas[f_id] = {
                'min': q_min,
                'max': q_max,
                'assigned': 0
            }
            self.stdout.write(f"Filière ID {f_id}: Total={total} | Min={q_min} | Max={q_max}")

        # 4. Récupération du Classement Global (Déjà trié en Passe 3 Rank)
        ranked_students = ResultatPasse3.objects.filter(campagne=campagne).select_related("etudiant", "filiere").order_by("rang")
        
        if not ranked_students.exists():
            self.stdout.write(self.style.ERROR("Aucun étudiant classé. Lancez d'abord run_passe3_rank."))
            return

        # Nettoyage
        AffectationFinale.objects.filter(campagne=campagne).delete()

        # Compteurs globaux
        count_affectes = 0
        count_recales_seuil = 0
        count_recales_quota = 0
        count_attente = 0

        # 5. Boucle Principale d'Affectation (FIFO Global)
        for row in ranked_students:
            etu = row.etudiant
            filiere_id = row.filiere_id
            note = row.note_selection
            
            # Récupération des quotas de sa filière
            if filiere_id not in quotas:
                # Cas rare : étudiant d'une filière inconnue ou sans stats
                quotas[filiere_id] = {'min': 0, 'max': 999, 'assigned': 0}
            
            q_data = quotas[filiere_id]

            # --- A. Vérification QUOTA MAX (30%) ---
            if q_data['assigned'] >= q_data['max']:
                self._save_result(campagne, etu, row, "NON_RETENU", None, "Quota Max (30%) atteint")
                count_recales_quota += 1
                continue

            # --- B. Vérification SEUIL DYNAMIQUE (Règle 3.5.2) ---
            # Si Note >= 13.5 : OK
            # Si 12.5 <= Note < 13.5 : OK SEULEMENT SI le Quota Min (10%) n'est pas encore atteint
            # Si Note < 12.5 : REJET (SEUIL1 atteint)
            
            est_admissible = False
            
            if note >= SEUIL2:
                est_admissible = True
            elif note >= SEUIL1:
                # Zone de repêchage (entre 12.5 et 13.5)
                if q_data['assigned'] < q_data['min']:
                    est_admissible = True # On repêche pour atteindre les 10%
                    self.stdout.write(f" > Repêchage {etu.nom} ({note:.2f}) pour quota min filière.")
                else:
                    est_admissible = False # Quota min déjà atteint, on ne descend pas le seuil
            else:
                est_admissible = False # En dessous du plancher absolu
            
            if not est_admissible:
                self._save_result(campagne, etu, row, "NON_RETENU", None, f"Note insuffisante ({note:.2f})")
                count_recales_seuil += 1
                continue

            # --- C. Traitement des Vœux ---
            # On cherche une place libre
            choices = Desiderata.objects.filter(campagne=campagne, etudiant=etu).order_by("priorite")
            assigned = False

            for d in choices:
                key = (d.partenaire_id, filiere_id, d.filiere_accueil, d.type_mobilite)
                remaining = capacities.get(key, 0)

                if remaining > 0:
                    # ✅ AFFECTATION RÉUSSIE
                    capacities[key] = remaining - 1
                    
                    self._save_result(campagne, etu, row, "AFFECTE", d, "Affecté sur vœu " + str(d.priorite))
                    
                    q_data['assigned'] += 1 # On incrémente le compteur de la filière
                    count_affectes += 1
                    assigned = True
                    break
            
            if not assigned:
                # Admissible mais plus de place dans ses vœux
                self._save_result(campagne, etu, row, "LISTE_ATTENTE", None, "Plus de place dans les vœux")
                count_attente += 1

        # Fin
        self.stdout.write(self.style.SUCCESS("-" * 30))
        self.stdout.write(self.style.SUCCESS(f"Affectation terminée."))
        self.stdout.write(f"Affectés: {count_affectes}")
        self.stdout.write(f"Liste Attente (Places): {count_attente}")
        self.stdout.write(f"Recalés (Seuil/Note): {count_recales_seuil}")
        self.stdout.write(f"Recalés (Quota Max): {count_recales_quota}")

    def _save_result(self, campagne, etu, row_rank, statut, voeu=None, log_msg=""):
        """Helper pour sauvegarder"""
        # Mise à jour ResultatPasse3 (pour info)
        row_rank.statut = statut # Assurez-vous d'avoir ce champ, sinon ignorez
        row_rank.save()

        # Création AffectationFinale
        defaults = {
            "statut": statut,
            "partenaire": voeu.partenaire if voeu else None,
            "type_mobilite": voeu.type_mobilite if voeu else None,
            "choix_obtenu": voeu.priorite if voeu else None
        }
        
        AffectationFinale.objects.update_or_create(
            campagne=campagne,
            etudiant=etu,
            defaults=defaults
        )
        # Log optionnel
        # print(f"{etu.cne} -> {statut} ({log_msg})")