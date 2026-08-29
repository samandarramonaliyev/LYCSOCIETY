from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification
from .serializers import NotificationSerializer
from .models import NotificationPreference
from .preferences import PreferenceSerializer

class NotificationListAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")
        if request.query_params.get("unread") == "true": qs = qs.filter(is_read=False)
        return Response(NotificationSerializer(qs, many=True).data)

class NotificationReadAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request, notification_id):
        obj = Notification.objects.filter(pk=notification_id, recipient=request.user).first()
        if obj is None: return Response({"detail": "Not found."}, status=404)
        if not obj.is_read:
            obj.is_read = True; obj.save(update_fields=("is_read", "updated_at"))
        return Response(NotificationSerializer(obj).data)

class PreferenceAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def get(self, request):
        obj, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(PreferenceSerializer(obj).data)
    def patch(self, request):
        obj, _ = NotificationPreference.objects.get_or_create(user=request.user)
        s=PreferenceSerializer(obj,data=request.data,partial=True); s.is_valid(raise_exception=True); s.save(); return Response(s.data)
