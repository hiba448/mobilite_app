from rest_framework import serializers
from selection.models import ConvocationEntretien, ResultatEntretien


class ConvocationSerializer(serializers.ModelSerializer):
    cne = serializers.CharField(source="etudiant.cne", read_only=True)
    filiere = serializers.CharField(source="etudiant.filiere.nom", read_only=True)

    class Meta:
        model = ConvocationEntretien
        fields = "__all__"
        depth = 0


class ResultatEntretienSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultatEntretien
        fields = [
            "id",
            "campagne",
            "etudiant",
            "present",
            "engagement_financier_ok",
            "motivation_ok",
            "decision",
        ]