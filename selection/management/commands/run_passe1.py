from django.core.management.base import BaseCommand
from django.db.models import Avg
from selection.models import ParametresSelection, DossierEtudiant, ResultatPasse1
from mobility.models import Campagne
from academic.models import NoteModule


class Command(BaseCommand):
    help = "Passe 1: sélection des étudiants éligibles (C1.1-C1.3)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--campagne-id",
            type=int,
            help="ID de la campagne. Si absent, prend la campagne active.",
        )

    def handle(self, *args, **options):
        campagne_id = options.get("campagne_id")

        if campagne_id:
            campagne = Campagne.objects.get(id=campagne_id)
        else:
            campagne = Campagne.objects.filter(active=True).first()
            if not campagne:
                self.stdout.write(self.style.ERROR("Aucune campagne active trouvée."))
                return

        params, _ = ParametresSelection.objects.get_or_create(campagne=campagne)
        seuil1 = params.seuil1

        dossiers = DossierEtudiant.objects.filter(campagne=campagne).select_related("etudiant")

        if not dossiers.exists():
            self.stdout.write(self.style.WARNING("Aucun DossierEtudiant trouvé pour cette campagne."))
            return

        count_ok = 0
        count_ko = 0

        for d in dossiers:
            etu = d.etudiant

            # Moyenne A1 sans PFA (notes de la campagne, modules où is_pfa=False)
            moyenne = (
                NoteModule.objects.filter(campagne=campagne, etudiant=etu, module__is_pfa=False)
                .aggregate(m=Avg("note"))
                .get("m")
            )

            if moyenne is None:
                eligible = False
                motif = "Notes manquantes (moyenne A1 sans PFA indisponible)."
                moyenne_val = 0.0
            else:
                moyenne_val = float(moyenne)

                # C1.1 + C1.2 + C1.3
                if d.redoublement_a1:
                    eligible = False
                    motif = "Non éligible: redoublement A1 (C1.1)."
                elif d.blame:
                    eligible = False
                    motif = "Non éligible: blâme (C1.2)."
                elif moyenne_val <= seuil1:
                    eligible = False
                    motif = f"Non éligible: moyenne A1 sans PFA <= SEUIL1 ({seuil1}). (C1.3)"
                else:
                    eligible = True
                    motif = ""

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
            else:
                count_ko += 1

        self.stdout.write(self.style.SUCCESS(f"Passe 1 terminée pour {campagne}"))
        self.stdout.write(self.style.SUCCESS(f"Eligibles: {count_ok} | Non eligibles: {count_ko}"))