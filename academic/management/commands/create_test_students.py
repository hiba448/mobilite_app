import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User  # <--- Import nécessaire
from academic.models import Etudiant, Filiere

class Command(BaseCommand):
    help = "Génère des étudiants de test avec leur compte User associé"

    def handle(self, *args, **options):
        # 1. Vérifier les filières
        filieres = list(Filiere.objects.all())
        if not filieres:
            self.stdout.write(self.style.ERROR("❌ Aucune filière trouvée ! Créez-les d'abord."))
            return

        # 2. Données aléatoires
        noms = ["Alami", "Bennani", "Idrissi", "Tazi", "Chraibi", "Ouazzani", "Kadiri", "Benjelloun", "Amrani", "Ziani"]
        prenoms = ["Ahmed", "Sara", "Karim", "Fatima", "Omar", "Yassine", "Hajar", "Salma", "Mehdi", "Kenza"]

        start_index = 8
        nombre_a_creer = 10

        self.stdout.write(f"--- Création de {nombre_a_creer} étudiants et utilisateurs ---")

        # 3. Boucle de création
        for i in range(nombre_a_creer):
            cne_str = f"CNE{str(start_index + i).zfill(3)}"
            
            # A. CRÉATION DU COMPTE UTILISATEUR (Login = CNE, Pass = 'pass123') 
            user, user_created = User.objects.get_or_create(username=cne_str)
            if user_created:
                user.set_password("pass123")
                user.save()

            # B. CRÉATION DE L'ÉTUDIANT LIÉ AU USER
            etu, created = Etudiant.objects.get_or_create(
                cne=cne_str,
                defaults={
                    'nom': random.choice(noms),
                    'prenom': random.choice(prenoms),
                    'filiere': random.choice(filieres),
                    'user': user  # <--- On attache le user qu'on vient de créer
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Créé : {etu.cne} (User: {user.username})"))
            else:
                self.stdout.write(self.style.WARNING(f"ℹ️ Existe déjà : {etu.cne}"))

        self.stdout.write(self.style.SUCCESS("--- Terminé avec succès ---"))