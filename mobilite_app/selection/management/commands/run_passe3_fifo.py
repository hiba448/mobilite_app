import math
from django.core.management.base import BaseCommand
from mobility.models import Campagne, Desiderata, OffrePartenaire
from selection.models import ParametresSelection, ResultatPasse3, AffectationFinale
from academic.models import MoyenneS3
from selection.utils import mediane_s3_filiere

class Command(BaseCommand):
    help = "Passe 3 (étape 2): Affectation FIFO selon desiderata VALIDES + capacités + quotas 10/30 (version 1)"

    def handle(self, *args, **options):
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne:
            self.stdout.write(self.style.ERROR("Aucune campagne active."))
            return

        params, _ = ParametresSelection.objects.get_or_create(campagne=campagne)
        seuil1 = params.seuil1
        seuil2 = params.seuil2
        min_pct = params.min_pct
        max_pct = params.max_pct

        # Capacités restantes: clé = (partenaire_id, filiere_origine_id, filiere_accueil, type_mobilite)
        capacities = {}
        offers = OffrePartenaire.objects.filter(campagne=campagne).select_related("partenaire", "filiere_origine")
        for off in offers:
            capacities[(off.partenaire_id, off.filiere_origine_id, off.filiere_accueil, "EC")] = off.nb_places_ec
            capacities[(off.partenaire_id, off.filiere_origine_id, off.filiere_accueil, "DD")] = off.nb_places_dd

        # Étudiants classés (Passe 3 étape 1) triés par filière puis rang
        ranked = ResultatPasse3.objects.filter(campagne=campagne).select_related("etudiant", "filiere").order_by("filiere__nom", "rang")

        if not ranked.exists():
            self.stdout.write(self.style.ERROR("Aucun ResultatPasse3. Lance d'abord run_passe3_rank."))
            return

        # Nettoyage: reset pré-affectations
        AffectationFinale.objects.filter(campagne=campagne).delete()

        total_affectes = 0
        total_attente = 0
        total_non = 0

        # Traitement par filière
        current_filiere_id = None
        buffer = []

        def process_filiere(items):
            nonlocal total_affectes, total_attente, total_non

            if not items:
                return

            filiere = items[0].filiere
            effectif = len(items)

            # quotas (arrondi à entier +1 comme ton texte)
            min_quota = math.floor(effectif * (min_pct / 100.0)) + 1
            max_quota = math.floor(effectif * (max_pct / 100.0)) + 1

            affectes_dans_filiere = 0

            for r in items:
                etu = r.etudiant
                # 0) Critère S3 : moy_s3 >= max(mediane_filiere_s3, SEUIL1)
                m_s3 = MoyenneS3.objects.filter(etudiant=etu, campagne=campagne).first()
                med = mediane_s3_filiere(campagne, filiere)

                # Mode dev/test : si pas de données S3, on laisse passer
                if m_s3 and med is not None:
                    seuil_s3 = max(med, seuil1)
                    if m_s3.moy_s3_avant_rattrapage < seuil_s3:
                        r.statut = "NON_RETENU"
                        r.save()
                        AffectationFinale.objects.update_or_create(
                            campagne=campagne, etudiant=etu,
                            defaults={"statut": "NON_RETENU"}
                        )
                        total_non += 1
                        continue

                # 1) jamais en dessous de SEUIL1
                if r.note_selection < seuil1:
                    r.statut = "NON_RETENU"
                    r.save()
                    AffectationFinale.objects.update_or_create(
                        campagne=campagne, etudiant=etu,
                        defaults={"statut": "NON_RETENU"}
                    )
                    total_non += 1
                    continue

                # 2) règle seuil2 + min 10% (version 1)
                if r.note_selection < seuil2 and affectes_dans_filiere >= min_quota:
                    r.statut = "NON_RETENU"
                    r.save()
                    AffectationFinale.objects.update_or_create(
                        campagne=campagne, etudiant=etu,
                        defaults={"statut": "NON_RETENU"}
                    )
                    total_non += 1
                    continue

                # 3) max 30%
                if affectes_dans_filiere >= max_quota:
                    r.statut = "ATTENTE"
                    r.save()
                    AffectationFinale.objects.update_or_create(
                        campagne=campagne, etudiant=etu,
                        defaults={"statut": "LISTE_ATTENTE"}
                    )
                    total_attente += 1
                    continue

                # 4) chercher le premier desiderata VALIDE qui a encore une capacité
                choices = Desiderata.objects.filter(
                    campagne=campagne, etudiant=etu, statut="VALIDE"
                ).select_related("partenaire").order_by("priorite")

                assigned = False

                for d in choices:
                    key = (d.partenaire_id, filiere.id, d.filiere_accueil, d.type_mobilite)
                    remaining = capacities.get(key, 0)

                    if remaining > 0:
                        # consommer une place
                        capacities[key] = remaining - 1

                        # enregistrer pré-affectation
                        AffectationFinale.objects.update_or_create(
                            campagne=campagne,
                            etudiant=etu,
                            defaults={
                                "partenaire": d.partenaire,
                                "type_mobilite": d.type_mobilite,
                                "choix_obtenu": d.priorite,
                                "statut": "NON_PUBLIE",
                            }
                        )

                        r.statut = "FIFO"
                        r.save()

                        affectes_dans_filiere += 1
                        total_affectes += 1
                        assigned = True
                        break

                if not assigned:
                    # aucun choix possible (places épuisées ou pas de desiderata)
                    r.statut = "ATTENTE"
                    r.save()
                    AffectationFinale.objects.update_or_create(
                        campagne=campagne, etudiant=etu,
                        defaults={"statut": "LISTE_ATTENTE"}
                    )
                    total_attente += 1

        # Boucle par filière
        for r in ranked:
            if current_filiere_id is None:
                current_filiere_id = r.filiere_id

            if r.filiere_id != current_filiere_id:
                process_filiere(buffer)
                buffer = []
                current_filiere_id = r.filiere_id

            buffer.append(r)

        # dernière filière
        process_filiere(buffer)

        self.stdout.write(self.style.SUCCESS("Passe 3 étape 2 (FIFO) terminée ✅"))
        self.stdout.write(self.style.SUCCESS(f"Affectés (pré-oral): {total_affectes} | Liste attente: {total_attente} | Non retenus: {total_non}"))