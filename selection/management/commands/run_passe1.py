from django.core.management.base import BaseCommand
from django.db.models import Avg
from academic.models import Etudiant, NoteModule
# Import les DEUX modèles
from selection.models import DossierEtudiant, ParametresSelection, ResultatPasse1 
from mobility.models import Campagne

class Command(BaseCommand):
    help = "Exécute la Passe 1"

    def handle(self, *args, **options):
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne: return

        # === C'EST ICI QUE CA PLANTAIT AVANT ===
        # On utilise get_solo() maintenant !
        params = ParametresSelection.get_solo()
        SEUIL = params.seuil_eligibilite_p1

        dossiers = DossierEtudiant.objects.filter(campagne=campagne)
        
        # On nettoie la table de résultats temporaire
        ResultatPasse1.objects.filter(campagne=campagne).delete()

        for dossier in dossiers:
            etu = dossier.etudiant
            
            # 1. Vérif Admin
            if dossier.redoublement_a1:
                dossier.eligible = False
                dossier.motif = "Recalé : Redoublement"
                dossier.save()
                # On crée l'entrée dans ResultatPasse1 pour le dashboard
                ResultatPasse1.objects.create(campagne=campagne, etudiant=etu, eligible=False, motif_refus="Redoublement", moyenne_a1_sans_pfa=0)
                continue

            if dossier.blame:
                dossier.eligible = False
                dossier.motif = "Recalé : Blâme"
                dossier.save()
                ResultatPasse1.objects.create(campagne=campagne, etudiant=etu, eligible=False, motif_refus="Blâme", moyenne_a1_sans_pfa=0)
                continue

            # 2. Calcul
            notes = NoteModule.objects.filter(campagne=campagne, etudiant=etu, module__is_pfa=False)
            if not notes.exists():
                continue

            moyenne = notes.aggregate(Avg('note'))['note__avg'] or 0.0
            dossier.moyenne_calculee_p1 = moyenne

            if moyenne >= SEUIL:
                dossier.eligible = True
                dossier.motif = "ADMIS"
            else:
                dossier.eligible = False
                dossier.motif = f"Moyenne < {SEUIL}"
            
            dossier.save()

            # IMPORTANT : On remplit ResultatPasse1 pour que ton Dashboard affiche les stats
            ResultatPasse1.objects.create(
                campagne=campagne,
                etudiant=etu,
                eligible=dossier.eligible,
                moyenne_a1_sans_pfa=moyenne,
                motif_refus=dossier.motif if not dossier.eligible else ""
            )

        self.stdout.write(self.style.SUCCESS(f"Passe 1 Terminée avec Seuil {SEUIL}"))