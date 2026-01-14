from django.core.management.base import BaseCommand
from django.db.models import Avg
from selection.models import ParametresSelection, DossierEtudiant, ResultatPasse1
from mobility.models import Campagne
from academic.models import NoteModule, Etudiant

class Command(BaseCommand):
    help = "Passe 1: Calcul éligibilité basé sur les notes importées par la Scolarité"

    def handle(self, *args, **options):
        # 1. Récupérer la campagne active
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne:
            self.stdout.write(self.style.ERROR("Aucune campagne active."))
            return

        # 2. Récupérer le Seuil (ex: 12.00)
        params, _ = ParametresSelection.objects.get_or_create(campagne=campagne)
        seuil1 = params.seuil1
        
        self.stdout.write(f"--- Démarrage Passe 1 (Seuil: {seuil1}) ---")

        # 3. On récupère TOUS les étudiants présents dans le système
        etudiants = Etudiant.objects.all()
        
        count_ok = 0
        count_ko = 0

        for etu in etudiants:
            # A. On s'assure qu'un dossier administratif existe (création auto si absent)
            # Cela permet d'éviter les erreurs si on a juste importé les notes mais pas créé de dossier
            dossier, _ = DossierEtudiant.objects.get_or_create(
                campagne=campagne,
                etudiant=etu,
                defaults={"redoublement_a1": False, "blame": False}
            )

            # ==============================================================================
            # B. C'EST ICI QU'ON RECUPERE LES NOTES IMPORTEES PAR LA SCOLARITE
            # ==============================================================================
            # On cherche dans NoteModule toutes les lignes liées à cet étudiant (etu)
            # On exclut les modules marqués comme "PFA" (is_pfa=False)
            moyenne_query = NoteModule.objects.filter(etudiant=etu, module__is_pfa=False)
            
            # Calcul de la moyenne arithmétique
            moyenne = moyenne_query.aggregate(m=Avg("note")).get("m")

            if moyenne is None:
                # Cas où l'étudiant existe mais n'a aucune note importée
                eligible = False
                motif = "Aucune note importée pour cet étudiant."
                moyenne_val = 0.0
            else:
                moyenne_val = float(moyenne)

                # C. Vérification des critères
                if dossier.redoublement_a1:
                    eligible = False
                    motif = "Recalé : Redoublement A1"
                elif dossier.blame:
                    eligible = False
                    motif = "Recalé : Blâme disciplinaire"
                elif moyenne_val < seuil1:
                    eligible = False
                    motif = f"Moyenne insuffisante ({moyenne_val:.2f} < {seuil1})"
                else:
                    eligible = True
                    motif = "OK"

            # 4. Sauvegarde du résultat final
            ResultatPasse1.objects.update_or_create(
                campagne=campagne,
                etudiant=etu,
                defaults={
                    "moyenne_a1_sans_pfa": moyenne_val,
                    "eligible": eligible,
                    "motif_refus": motif,
                },
            )

            if eligible:
                count_ok += 1
                self.stdout.write(f"✅ {etu.nom} {etu.prenom} : {moyenne_val:.2f} -> ÉLIGIBLE")
            else:
                count_ko += 1
                # On affiche les rejetés pour comprendre pourquoi
                if moyenne_val > 0: 
                     self.stdout.write(f"❌ {etu.nom} {etu.prenom} : {moyenne_val:.2f} -> {motif}")

        self.stdout.write(self.style.SUCCESS("-" * 30))
        self.stdout.write(self.style.SUCCESS(f"TOTAL ÉLIGIBLES : {count_ok}"))
        self.stdout.write(self.style.SUCCESS(f"TOTAL RECALÉS   : {count_ko}"))