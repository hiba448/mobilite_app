from django.core.management.base import BaseCommand
from django.db.models import Avg
from academic.models import Etudiant, NoteModule
from selection.models import DossierEtudiant, ParametresSelection, ResultatPasse1 
from mobility.models import Campagne

class Command(BaseCommand):
    help = "Exécute la Passe 1"

    def handle(self, *args, **options):
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne: 
            self.stdout.write(self.style.ERROR("Aucune campagne active"))
            return

        params = ParametresSelection.get_solo()
        SEUIL = params.seuil_eligibilite_p1

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"DÉBUT PASSE 1 - Seuil: {SEUIL}")
        self.stdout.write(f"{'='*80}\n")

        dossiers = DossierEtudiant.objects.filter(campagne=campagne)
        
        # On nettoie la table de résultats temporaire
        ResultatPasse1.objects.filter(campagne=campagne).delete()

        count_traites = 0
        count_admis = 0

        for dossier in dossiers:
            etu = dossier.etudiant
            
            # DEBUG SPÉCIAL POUR CNE001
            if etu.cne == "CNE001":
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"🔍 TRAITEMENT DE CNE001")
                self.stdout.write(f"{'='*60}")
            
            # 1. Vérif Admin
            if dossier.redoublement_a1:
                dossier.eligible = False
                dossier.motif = "Recalé : Redoublement"
                dossier.save()
                ResultatPasse1.objects.create(
                    campagne=campagne, 
                    etudiant=etu, 
                    eligible=False, 
                    motif_refus="Redoublement", 
                    moyenne_a1_sans_pfa=0
                )
                count_traites += 1
                if etu.cne == "CNE001":
                    self.stdout.write("❌ Éliminé : Redoublement")
                continue

            if dossier.blame:
                dossier.eligible = False
                dossier.motif = "Recalé : Blâme"
                dossier.save()
                ResultatPasse1.objects.create(
                    campagne=campagne, 
                    etudiant=etu, 
                    eligible=False, 
                    motif_refus="Blâme", 
                    moyenne_a1_sans_pfa=0
                )
                count_traites += 1
                if etu.cne == "CNE001":
                    self.stdout.write("❌ Éliminé : Blâme")
                continue

            # 2. Calcul de la moyenne TC + SPEC (sans PFA)
            notes = NoteModule.objects.filter(
                campagne=campagne, 
                etudiant=etu, 
                module__is_pfa=False
            )
            
            if etu.cne == "CNE001":
                self.stdout.write(f"\n📋 Nombre de notes trouvées (sans PFA) : {notes.count()}")
                for n in notes:
                    self.stdout.write(
                        f"   - {n.module.nom:40} : {n.note:5.2f} "
                        f"(TC:{n.module.is_tc}, SPEC:{n.module.is_specialite}, PFA:{n.module.is_pfa})"
                    )
            
            if not notes.exists():
                self.stdout.write(self.style.WARNING(f"⚠️ {etu.cne} : Aucune note trouvée"))
                continue

            # CALCUL MANUEL POUR VÉRIFICATION
            notes_list = list(notes.values_list('note', flat=True))
            moyenne_manuelle = sum(notes_list) / len(notes_list) if notes_list else 0
            
            # CALCUL AVEC AGGREGATE
            moyenne_aggregate = notes.aggregate(Avg('note'))['note__avg'] or 0.0
            
            if etu.cne == "CNE001":
                self.stdout.write(f"\n📊 Notes utilisées : {notes_list}")
                self.stdout.write(f"📊 Somme : {sum(notes_list)}")
                self.stdout.write(f"📊 Nombre : {len(notes_list)}")
                self.stdout.write(f"📊 Moyenne manuelle : {moyenne_manuelle:.2f}")
                self.stdout.write(f"📊 Moyenne aggregate : {moyenne_aggregate:.2f}")
            
            moyenne = moyenne_aggregate
            dossier.moyenne_calculee_p1 = round(moyenne, 2)

            if moyenne >= SEUIL:
                dossier.eligible = True
                dossier.motif = "ADMIS"
                count_admis += 1
            else:
                dossier.eligible = False
                dossier.motif = f"Moyenne < {SEUIL}"
            
            dossier.save()

            if etu.cne == "CNE001":
                self.stdout.write(f"\n💾 Moyenne enregistrée : {dossier.moyenne_calculee_p1}")
                self.stdout.write(f"✓ Éligible : {dossier.eligible}")
                self.stdout.write(f"✓ Motif : {dossier.motif}")
                self.stdout.write(f"{'='*60}\n")

            # Création de l'entrée ResultatPasse1
            ResultatPasse1.objects.create(
                campagne=campagne,
                etudiant=etu,
                eligible=dossier.eligible,
                moyenne_a1_sans_pfa=round(moyenne, 2),
                motif_refus=dossier.motif if not dossier.eligible else ""
            )
            count_traites += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*80}\n"
            f"✅ Passe 1 Terminée avec Seuil {SEUIL}\n"
            f"   📋 {count_traites} dossiers traités\n"
            f"   ✓ {count_admis} admis\n"
            f"   ✗ {count_traites - count_admis} recalés\n"
            f"{'='*80}\n"
        ))