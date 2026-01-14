from rest_framework import serializers

class MeSerializer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.CharField()
    