from django.core.management.base import BaseCommand
from mobility.models import Campagne
from selection.models import ConvocationEntretien, AffectationFinale


class Command(BaseCommand):
    help = "Passe 4: Générer les convocations (Affectés + Liste d'attente)"

    def handle(self, *args, **options):
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne:
            self.stdout.write(self.style.ERROR("Aucune campagne active."))
            return

        self.stdout.write("--- Génération des Convocations ---")

        # 1. On récupère les AFFECTE (ceux retenus par le FIFO)
        # Note: On inclut "NON_PUBLIE" au cas où tu aurais changé le script précédent
        candidats_retenus = AffectationFinale.objects.filter(
            campagne=campagne, 
            statut__in=["AFFECTE", "NON_PUBLIE"]
        ).select_related("etudiant")

        # 2. On convoque aussi la LISTE D'ATTENTE (Règle 4.1.1 : "plus le/les suivants") 
        # C'est utile pour gérer les désistements potentiels dès maintenant.
        candidats_attente = AffectationFinale.objects.filter(
            campagne=campagne, 
            statut="LISTE_ATTENTE"
        ).select_related("etudiant")

        total_convoques = 0

        # Fonction locale pour traiter une liste
        def convoquer_liste(liste_query, est_liste_attente=False):
            count = 0
            for aff in liste_query:
                # Créer la convocation
                msg = "Vous êtes sur liste d'attente." if est_liste_attente else "Vous êtes pré-sélectionné."
                
                convoc, created = ConvocationEntretien.objects.get_or_create(
                    campagne=campagne, 
                    etudiant=aff.etudiant,
                    defaults={"statut_convocation": "CONVOQUE", "message": msg}
                )

                # IMPORTANT : On met à jour le statut public pour le Dashboard Étudiant
                if aff.statut != "CONVOQUE":
                    aff.statut = "CONVOQUE"
                    aff.save()
                
                if created:
                    count += 1
            return count

        # Exécution
        nb_retenus = convoquer_liste(candidats_retenus, est_liste_attente=False)
        nb_attente = convoquer_liste(candidats_attente, est_liste_attente=True)

        self.stdout.write(self.style.SUCCESS(f"Terminé ✅"))
        self.stdout.write(f"Candidats retenus convoqués : {nb_retenus}")
        self.stdout.write(f"Liste d'attente convoquée   : {nb_attente}")