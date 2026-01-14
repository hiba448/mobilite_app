from rest_framework import serializers

class StudentMeSerializer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.CharField()
    cne = serializers.CharField(allow_null=True)
    filiere = serializers.CharField(allow_null=True)
    eligible_passe1 = serializers.BooleanField()
    statut = serializers.CharField(allow_null=True)
    rang = serializers.IntegerField(allow_null=True)
    campagne_active = serializers.CharField(allow_null=True)
    deadline_desiderata_open = serializers.BooleanField()

class DesiderataSerializer(serializers.Serializer):
    priorite = serializers.IntegerField()
    partenaire = serializers.CharField()
    filiere_accueil = serializers.CharField()
    type_mobilite = serializers.ChoiceField(choices=["EC", "DD"])