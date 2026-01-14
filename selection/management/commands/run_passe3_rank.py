from django.core.management.base import BaseCommand
from django.db.models import Avg
from mobility.models import Campagne
from selection.models import ParametresSelection, ResultatPasse1, ResultatPasse3, AffectationFinale
from academic.models import MoyenneS3, NoteModule

# Import sécurisé pour éviter le crash si le fichier utils n'est pas encore vu par Django
try:
    from selection.utils import mediane_s3_filiere
except ImportError:
    mediane_s3_filiere = None

class Command(BaseCommand):
    help = "Passe 3 Rank: Classement avec formule EXACTE (0.8*TC + 0.2*Spec) et filtre S3"

    def handle(self, *args, **options):
        # Vérification de sécurité
        if mediane_s3_filiere is None:
            self.stdout.write(self.style.ERROR("ERREUR: Le fichier 'selection/utils.py' est introuvable. Veuillez le créer."))
            return

        campagne = Campagne.objects.filter(active=True).first()
        if not campagne:
            self.stdout.write(self.style.ERROR("Aucune campagne active."))
            return

        self.stdout.write(f"--- Calcul Classement (Formule 0.8 TC + 0.2 Spec) ---")

        # Seuil plancher S3 (Règle C1.3 du PDF utilisée comme ref)
        seuil_plancher_s3 = 12.5 

        # On prend les éligibles de la Passe 1
        admissibles = ResultatPasse1.objects.filter(campagne=campagne, eligible=True).select_related("etudiant", "etudiant__filiere")

        if not admissibles.exists():
            self.stdout.write(self.style.WARNING("Aucun étudiant éligible (Passe 1 vide)."))
            return

        classement_temp = []
        count_recales_s3 = 0

        for res_p1 in admissibles:
            etu = res_p1.etudiant
            filiere = etu.filiere

            # =========================================================
            # ÉTAPE A : VERROU S3 (Moyenne S3 >= Max(Médiane, 12.5))
            # =========================================================
            obj_s3 = MoyenneS3.objects.filter(campagne=campagne, etudiant=etu).first()
            
            # Si pas de note S3, on exclut (sécurité)
            if not obj_s3 or obj_s3.moy_s3_avant_rattrapage is None:
                self.stdout.write(self.style.WARNING(f"Exclusion {etu.cne}: Note S3 manquante."))
                self._rejeter(campagne, etu)
                count_recales_s3 += 1
                continue
            
            note_s3 = float(obj_s3.moy_s3_avant_rattrapage)

            # Calcul Médiane Filière
            mediane_fil = mediane_s3_filiere(campagne, filiere)
            if mediane_fil is None:
                seuil_s3_final = seuil_plancher_s3
            else:
                seuil_s3_final = max(mediane_fil, seuil_plancher_s3)

            # Vérification du seuil S3
            if note_s3 < seuil_s3_final:
                # Éliminé à cause du S3
                self._rejeter(campagne, etu)
                count_recales_s3 += 1
                # Log optionnel pour debug
                # self.stdout.write(f"Recalé S3: {etu.nom} ({note_s3} < {seuil_s3_final})")
                continue

            # =========================================================
            # ÉTAPE B : CALCUL DE LA NOTE DE SÉLECTION (0.8 / 0.2)
            # =========================================================
            # 1. Calcul Moyenne Tronc Commun (TC)
            # On cherche les modules de cet étudiant qui sont 'is_tc=True'
            moy_tc_agg = NoteModule.objects.filter(
                etudiant=etu, 
                module__is_tc=True,       # C'est ici que votre modèle aide !
                module__is_pfa=False
            ).aggregate(m=Avg('note'))['m']

            # 2. Calcul Moyenne Spécialité (Spec)
            # Tout ce qui n'est pas TC et pas PFA
            moy_spec_agg = NoteModule.objects.filter(
                etudiant=etu, 
                module__is_tc=False,      # Spécialité
                module__is_pfa=False
            ).aggregate(m=Avg('note'))['m']

            # Gestion des valeurs None (si notes manquantes)
            val_tc = float(moy_tc_agg) if moy_tc_agg is not None else 0.0
            val_spec = float(moy_spec_agg) if moy_spec_agg is not None else 0.0

            # Si aucune note de spécialité n'est trouvée (ex: début année), 
            # on peut utiliser la moyenne générale comme fallback, ou rester à 0.
            if moy_spec_agg is None and moy_tc_agg is not None:
                val_spec = val_tc # Fallback pour éviter de pénaliser injustement si données incomplètes

            # Formule Officielle PDF
            note_selection = (0.8 * val_tc) + (0.2 * val_spec)

            classement_temp.append({
                "etudiant": etu,
                "filiere": filiere,
                "note_a1": res_p1.moyenne_a1_sans_pfa, # Juste pour info
                "note_s3": note_s3,
                "note_selection": note_selection
            })

        # =========================================================
        # ÉTAPE C : TRI ET SAUVEGARDE
        # =========================================================
        
        # Tri décroissant sur la note de sélection calculée
        classement_temp.sort(key=lambda x: x["note_selection"], reverse=True)

        # Nettoyage table
        ResultatPasse3.objects.filter(campagne=campagne).delete()

        for idx, data in enumerate(classement_temp, start=1):
            ResultatPasse3.objects.create(
                campagne=campagne,
                etudiant=data["etudiant"],
                filiere=data["filiere"],
                rang=idx,
                note_s1=data["note_a1"],
                note_s3=data["note_s3"],
                note_selection=data["note_selection"]
            )
            # Affichage console
            self.stdout.write(f"#{idx} {data['etudiant'].nom} : {data['note_selection']:.3f} (S3={data['note_s3']})")

        self.stdout.write(self.style.SUCCESS("-" * 30))
        self.stdout.write(self.style.SUCCESS(f"CLASSEMENT TERMINÉ ✅"))
        self.stdout.write(f"Étudiants classés : {len(classement_temp)}")
        self.stdout.write(f"Recalés (Critère S3) : {count_recales_s3}")

    def _rejeter(self, campagne, etu):
        """Marque l'étudiant comme non retenu dans l'affectation finale"""
        AffectationFinale.objects.update_or_create(
            campagne=campagne, etudiant=etu,
            defaults={"statut": "NON_RETENU"}
        )