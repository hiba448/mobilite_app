from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import MeSerializer

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    data = {"username": request.user.username, "role": request.user.profile.role}
    return Response(MeSerializer(data).data)
