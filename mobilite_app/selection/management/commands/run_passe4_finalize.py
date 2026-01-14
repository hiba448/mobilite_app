from django.core.management.base import BaseCommand
from mobility.models import Campagne, Desiderata, OffrePartenaire
from selection.models import ResultatEntretien, AffectationFinale, ResultatPasse3


class Command(BaseCommand):
    help = "Passe 4: appliquer décisions oral + libérer places + proposer à l'attente"

    def handle(self, *args, **options):
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne:
            self.stdout.write(self.style.ERROR("Aucune campagne active."))
            return

        # construire capacités restantes à partir des offres
        capacities = {}
        offers = OffrePartenaire.objects.filter(campagne=campagne).select_related("partenaire", "filiere_origine")
        for off in offers:
            capacities[(off.partenaire_id, off.filiere_origine_id, off.filiere_accueil, "EC")] = off.nb_places_ec
            capacities[(off.partenaire_id, off.filiere_origine_id, off.filiere_accueil, "DD")] = off.nb_places_dd

        # consommer les places des pré-affectations actuelles (NON_PUBLIE)
        pre = AffectationFinale.objects.filter(campagne=campagne, statut="NON_PUBLIE").select_related("etudiant", "partenaire", "etudiant__filiere")
        for a in pre:
            if a.partenaire and a.type_mobilite and a.choix_obtenu:
                key = (a.partenaire_id, a.etudiant.filiere_id, a.partenaire.nom_ecole if False else a.partenaire_id, )  # (ignore)
        # NOTE: on ne peut pas reconstruire filiere_accueil depuis AffectationFinale (pas stockée),
        # donc on va recalculer via le desiderata correspondant.
        for a in pre:
            if not a.partenaire or not a.type_mobilite or not a.choix_obtenu:
                continue
            d = Desiderata.objects.filter(
                campagne=campagne, etudiant=a.etudiant, priorite=a.choix_obtenu, statut="VALIDE"
            ).first()
            if not d:
                continue
            key = (d.partenaire_id, a.etudiant.filiere_id, d.filiere_accueil, d.type_mobilite)
            if key in capacities and capacities[key] > 0:
                capacities[key] -= 1

        # appliquer décisions d'entretien
        entretiens = ResultatEntretien.objects.filter(campagne=campagne).select_related("etudiant")
        decisions = {e.etudiant_id: e for e in entretiens}

        freed_slots = []  # liste de (filiere_id, partenaire_id, filiere_accueil, type_mobilite)

        for a in pre:
            e = decisions.get(a.etudiant_id)

            # si pas de résultat saisi => on laisse en NON_PUBLIE
            if not e:
                continue

            # règles élimination
            elimine = False
            if not e.present:
                elimine = True
            elif not e.engagement_financier_ok:
                elimine = True
            elif not e.motivation_ok:
                elimine = True
            elif e.decision == "ELIMINE":
                elimine = True

            if elimine:
                # libérer place si elle existait
                d = Desiderata.objects.filter(
                    campagne=campagne, etudiant=a.etudiant, priorite=a.choix_obtenu, statut="VALIDE"
                ).first()
                if d:
                    freed_slots.append((a.etudiant.filiere_id, d.partenaire_id, d.filiere_accueil, d.type_mobilite))

                a.statut = "NON_RETENU"
                a.partenaire = None
                a.type_mobilite = None
                a.choix_obtenu = None
                a.save()
            else:
                a.statut = "AFFECTE"
                a.save()

        # repêchage: pour chaque place libérée, proposer au plus méritant en attente ayant le voeu correspondant
        for (filiere_id, partenaire_id, filiere_accueil, type_mobilite) in freed_slots:
            # trouver candidats attente classés (rang le plus petit) qui ont ce vœu
            candidats = (
                AffectationFinale.objects.filter(campagne=campagne, statut="LISTE_ATTENTE", etudiant__filiere_id=filiere_id)
                .select_related("etudiant")
            )

            best = None
            best_rank = None

            for c in candidats:
                # a-t-il exprimé le vœu correspondant ?
                has_wish = Desiderata.objects.filter(
                    campagne=campagne,
                    etudiant=c.etudiant,
                    statut="VALIDE",
                    partenaire_id=partenaire_id,
                    filiere_accueil=filiere_accueil,
                    type_mobilite=type_mobilite,
                ).exists()

                if not has_wish:
                    continue

                r = ResultatPasse3.objects.filter(campagne=campagne, etudiant=c.etudiant).first()
                if not r or r.rang is None:
                    continue

                if best is None or r.rang < best_rank:
                    best = c
                    best_rank = r.rang

            if best:
                # affecter la place libérée
                d_best = Desiderata.objects.filter(
                    campagne=campagne,
                    etudiant=best.etudiant,
                    statut="VALIDE",
                    partenaire_id=partenaire_id,
                    filiere_accueil=filiere_accueil,
                    type_mobilite=type_mobilite,
                ).order_by("priorite").first()

                best.partenaire_id = partenaire_id
                best.type_mobilite = type_mobilite
                best.choix_obtenu = d_best.priorite if d_best else None
                best.statut = "AFFECTE"
                best.save()

        self.stdout.write(self.style.SUCCESS("Passe 4 finalisation terminée ✅"))