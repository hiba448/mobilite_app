from django.core.management.base import BaseCommand
from academic.models import Module

class Command(BaseCommand):
    help = "Crée les modules nécessaires pour le test de la Passe 1"

    def handle(self, *args, **options):
        # Liste (Nom du module, Type)
        # Type: 'TC' = Tronc Commun, 'SPEC' = Spécialité, 'PFA' = Projet Fin Année
        modules_to_create = [
            # --- Modules Génériques (CNE001-007) ---
            ("Langue & Com", "TC"),
            ("Bases de données", "TC"),
            ("Algorithmique", "TC"),
            ("Analyse Numérique", "TC"),
            ("Architecture", "TC"),
            ("PFA", "PFA"),

            # --- Modules BI&A (CNE008) ---
            ("Algorithmiques et Structures de données", "TC"),
            ("Architecture des ordinateurs", "TC"),
            ("Statistique et Probabilité Appliquée", "TC"),
            ("Modélisation et Programmation Mathématique", "TC"),
            ("Introduction au BI_A", "SPEC"),
            ("Langues et communication I", "TC"),
            ("Power Skills dans la culture", "TC"),
            # "Bases de données" existe déjà en haut, pas grave le script gère les doublons
            ("Réseaux et Systèmes", "TC"),
            ("Introduction à l’intelligence Artificielle", "SPEC"),
            ("Programmation Orientée Objet", "TC"),
            ("Projet fédérateur 1A", "PFA"),
            ("Langues et communication II", "TC"),
            ("ECONOMIE DIGITALE", "TC"),

            # --- Modules Sécurité (CNE009) ---
            ("Algorithmique Avancée", "TC"),
            ("Architecture et OS", "TC"),
            ("Mathématiques pour l'ingénieur", "TC"),
            ("Cryptographie de base", "SPEC"),
            ("Introduction au Cloud Computing", "SPEC"),
            ("Sécurité des Réseaux", "SPEC"),
            ("Langues et Soft Skills", "TC"),
            ("Projet Intégrateur Sécurité", "PFA"),

            # --- Modules IA (CNE010) ---
            ("Mathématiques pour la Data Science", "SPEC"),
            ("Machine Learning Fundamentals", "SPEC"),
            ("Programmation Python IA", "SPEC"),
            ("Projet IA Chatbot", "PFA"),

            # --- Modules Data Engineering (CNE011) ---
            ("Big Data Ecosystems", "SPEC"),
            ("NoSQL Databases", "SPEC"),
            ("Data Warehousing", "SPEC"),
            ("Bases de données Avancées", "TC"),
            ("Projet Pipeline de Données", "PFA"),
        ]

        self.stdout.write("--- Création des Modules ---")

        count = 0
        for nom, type_mod in modules_to_create:
            # Définition des drapeaux booléens
            is_pfa = (type_mod == 'PFA')
            is_tc = (type_mod == 'TC')
            is_spec = (type_mod == 'SPEC')

            # update_or_create permet de mettre à jour le type si le module existe déjà
            mod, created = Module.objects.update_or_create(
                nom=nom,
                defaults={
                    'is_pfa': is_pfa,
                    'is_tc': is_tc,
                    'is_specialite': is_spec
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Créé : {nom} ({type_mod})"))
            else:
                self.stdout.write(f"ℹ️ Mis à jour : {nom}")
            
            count += 1

        self.stdout.write(self.style.SUCCESS(f"--- Terminé : {count} modules traités ---"))