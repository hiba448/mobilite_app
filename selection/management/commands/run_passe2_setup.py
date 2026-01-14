from django.core.management.base import BaseCommand
from mobility.models import Campagne, Partenaire, OffrePartenaire, Alignement, Desiderata
from selection.models import ResultatPasse1
from academic.models import Filiere


class Command(BaseCommand):
    help = "Passe 2: setup de test (partenaire + offre + alignement + un desiderata valide)"

    def handle(self, *args, **options):
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne:
            self.stdout.write(self.style.ERROR("Aucune campagne active."))
            return

        # prendre un étudiant éligible
        r = ResultatPasse1.objects.filter(campagne=campagne, eligible=True).select_related("etudiant").first()
        if not r:
            self.stdout.write(self.style.ERROR("Aucun étudiant éligible en Passe 1."))
            return
        etu = r.etudiant

        filiere = etu.filiere

        # Partenaire
        p, _ = Partenaire.objects.get_or_create(nom_ecole="ISIMA", defaults={"pays": "France"})

        # Offre partenaire (capacités)
        OffrePartenaire.objects.get_or_create(
            campagne=campagne,
            partenaire=p,
            filiere_origine=filiere,
            filiere_accueil="F5 – Réseaux et sécurité informatique",
            defaults={"nb_places_ec": 2, "nb_places_dd": 1},
        )

        # Alignement autorisé
        Alignement.objects.get_or_create(
            campagne=campagne,
            filiere_origine=filiere,
            partenaire=p,
            filiere_accueil="F5 – Réseaux et sécurité informatique",
            type_mobilite="EC",
        )

        # Desiderata (choix #1)
        d, created = Desiderata.objects.get_or_create(
            campagne=campagne,
            etudiant=etu,
            priorite=1,
            defaults={
                "partenaire": p,
                "filiere_accueil": "F5 – Réseaux et sécurité informatique",
                "type_mobilite": "EC",
                "statut": "EN_ATTENTE",
            },
        )

        self.stdout.write(self.style.SUCCESS("Passe 2 setup OK ✅"))
        self.stdout.write(self.style.SUCCESS(f"Desiderata créé/présent pour {etu.cne}: {d.partenaire} - {d.filiere_accueil}"))