from rest_framework import serializers
from mobility.models import OffrePartenaire
from selection.models import AffectationFinale, ResultatEntretien


class OffrePartenaireSerializer(serializers.ModelSerializer):
    partenaire = serializers.CharField(source="partenaire.nom_ecole", read_only=True)
    filiere_origine = serializers.CharField(source="filiere_origine.nom", read_only=True)

    class Meta:
        model = OffrePartenaire
        fields = [
            "id",
            "partenaire",
            "filiere_origine",
            "filiere_accueil",
            "nb_places_ec",
            "nb_places_dd",
        ]


class CandidatPartenaireSerializer(serializers.ModelSerializer):
    cne = serializers.CharField(source="etudiant.cne", read_only=True)
    nom = serializers.CharField(source="etudiant.nom", read_only=True)
    prenom = serializers.CharField(source="etudiant.prenom", read_only=True)
    filiere = serializers.CharField(source="etudiant.filiere.nom", read_only=True)

    decision_comite = serializers.SerializerMethodField()

    class Meta:
        model = AffectationFinale
        fields = [
            "id",
            "cne",
            "nom",
            "prenom",
            "filiere",
            "type_mobilite",
            "choix_obtenu",
            "statut",
            "decision_comite",
        ]

    def get_decision_comite(self, obj):
        re = ResultatEntretien.objects.filter(campagne=obj.campagne, etudiant=obj.etudiant).first()
        return re.decision if re else None