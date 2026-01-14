from django.core.management.base import BaseCommand
from django.db.models import Avg
from mobility.models import Campagne
from selection.models import ParametresSelection, DossierEtudiant, ResultatPasse1, ResultatPasse3
from academic.models import NoteModule, Module


class Command(BaseCommand):
    help = "Passe 3 (étape 1): calcul note sélection + classement par filière"

    def handle(self, *args, **options):
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne:
            self.stdout.write(self.style.ERROR("Aucune campagne active."))
            return

        params, _ = ParametresSelection.objects.get_or_create(campagne=campagne)
        seuil1 = params.seuil1

        # Etudiants éligibles Passe 1
        eligibles_ids = set(ResultatPasse1.objects.filter(campagne=campagne, eligible=True)
                            .values_list("etudiant_id", flat=True))

        dossiers = DossierEtudiant.objects.filter(campagne=campagne, etudiant_id__in=eligibles_ids)\
                                          .select_related("etudiant", "etudiant__filiere")

        if not dossiers.exists():
            self.stdout.write(self.style.WARNING("Aucun dossier éligible pour Passe 3."))
            return

        # Liste des modules TC et Spécialité
        tc_modules = Module.objects.filter(is_tc=True, is_pfa=False)
        spe_modules = Module.objects.filter(is_specialite=True, is_pfa=False)

        if not tc_modules.exists():
            self.stdout.write(self.style.ERROR("Aucun module TC (is_tc=True). Coche les 9 modules TC dans l'admin."))
            return

        # Calcul note par étudiant
        results_by_filiere = {}

        for d in dossiers:
            etu = d.etudiant
            filiere = etu.filiere

            # Critère S3 avant rattrapage
            if d.moyenne_s3_avant_rattrapage is not None:
                # médiane filière pas encore implémentée => on applique max(12.5, médiane) plus tard
                if d.moyenne_s3_avant_rattrapage < seuil1:
                    continue

            # moyenne TC
            tc_avg = NoteModule.objects.filter(
                campagne=campagne, etudiant=etu, module__in=tc_modules
            ).aggregate(m=Avg("note"))["m"]

            if tc_avg is None:
                continue

            # moyenne spécialité (si aucun module spé, on prend 0)
            spe_avg = NoteModule.objects.filter(
                campagne=campagne, etudiant=etu, module__in=spe_modules
            ).aggregate(m=Avg("note"))["m"] or 0.0

            note_sel = 0.8 * float(tc_avg) + 0.2 * float(spe_avg)

            results_by_filiere.setdefault(filiere.id, []).append((etu, filiere, note_sel))

        # Tri + enregistrement ResultatPasse3 (rang)
        total = 0
        for filiere_id, items in results_by_filiere.items():
            items.sort(key=lambda x: x[2], reverse=True)  # note_sel décroissante

            for i, (etu, filiere, note_sel) in enumerate(items, start=1):
                ResultatPasse3.objects.update_or_create(
                    campagne=campagne,
                    etudiant=etu,
                    defaults={
                        "filiere": filiere,
                        "note_selection": note_sel,
                        "rang": i,
                        "statut": "FIFO",  # provisoire, étape 2 gérera attente/non retenu
                    }
                )
                total += 1

        self.stdout.write(self.style.SUCCESS(f"Passe 3 étape 1 OK ✅ | Classements créés: {total}"))