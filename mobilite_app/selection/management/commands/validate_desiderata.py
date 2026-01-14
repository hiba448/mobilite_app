from django.core.management.base import BaseCommand
from mobility.models import Campagne, Alignement, Desiderata
from selection.models import ResultatPasse1


class Command(BaseCommand):
    help = "Valider les desiderata selon l'alignement (Règle 2.1.1) + éligibilité Passe 1"

    def handle(self, *args, **options):
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne:
            self.stdout.write(self.style.ERROR("Aucune campagne active."))
            return

        eligibles = set(
            ResultatPasse1.objects.filter(campagne=campagne, eligible=True).values_list("etudiant_id", flat=True)
        )

        desids = Desiderata.objects.filter(campagne=campagne).select_related("etudiant", "partenaire", "etudiant__filiere")

        ok = 0
        ko = 0

        for d in desids:
            # 1) doit être éligible Passe 1
            if d.etudiant_id not in eligibles:
                d.statut = "REFUSE"
                d.save()
                ko += 1
                continue

            # 2) doit respecter l'alignement
            allowed = Alignement.objects.filter(
                campagne=campagne,
                filiere_origine=d.etudiant.filiere,
                partenaire=d.partenaire,
                filiere_accueil=d.filiere_accueil,
                type_mobilite=d.type_mobilite,
            ).exists()

            if allowed:
                d.statut = "VALIDE"
                d.save()
                ok += 1
            else:
                d.statut = "REFUSE"
                d.save()
                ko += 1

        self.stdout.write(self.style.SUCCESS(f"Validation Passe 2 terminée ✅ | VALIDE={ok} | REFUSE={ko}"))