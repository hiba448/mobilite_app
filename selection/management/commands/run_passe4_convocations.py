from django.core.management.base import BaseCommand
from mobility.models import Campagne
from selection.models import ConvocationEntretien, ResultatPasse3, AffectationFinale


class Command(BaseCommand):
    help = "Passe 4: générer les convocations (FIFO d'abord, puis attente si besoin)"

    def handle(self, *args, **options):
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne:
            self.stdout.write(self.style.ERROR("Aucune campagne active."))
            return

        # candidats pré-affectés (NON_PUBLIE) + liste d'attente
        fifo = AffectationFinale.objects.filter(campagne=campagne, statut="NON_PUBLIE").select_related("etudiant")
        attente = AffectationFinale.objects.filter(campagne=campagne, statut="LISTE_ATTENTE").select_related("etudiant")

        if not fifo.exists() and not attente.exists():
            self.stdout.write(self.style.ERROR("Aucune pré-affectation trouvée. Lance d'abord run_passe3_fifo."))
            return

        created = 0

        # convoquer tous les FIFO (version simple)
        for a in fifo:
            _, was_created = ConvocationEntretien.objects.get_or_create(campagne=campagne, etudiant=a.etudiant)
            if was_created:
                created += 1

        # option: convoquer aussi une partie de la liste d'attente (backup)
        # Ici on convoque tous les attente (simple), tu peux limiter après.
        for a in attente:
            _, was_created = ConvocationEntretien.objects.get_or_create(campagne=campagne, etudiant=a.etudiant)
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Convocations générées ✅ | nouvelles convocations: {created}"))