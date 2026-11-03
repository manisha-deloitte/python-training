from datetime import timedelta
from pathlib import Path
import secrets

from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, QueryLog, UserSession
from .serializers import (
    DocumentSerializer,
    DocumentUploadSerializer,
    QueryLogSerializer,
    RegistrationSerializer,
)


MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_FILE_TYPES = {".txt", ".md", ".csv"}


class RegisterView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = authenticate(
            username=request.data.get("username"),
            password=request.data.get("password"),
        )
        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = UserSession.objects.create(
            user=user,
            token=secrets.token_hex(32),
            expires_at=timezone.now() + timedelta(days=7),
        )
        return Response({"token": session.token})


class DocumentListCreateView(generics.ListAPIView):
    serializer_class = DocumentSerializer
    parser_classes = [JSONParser, MultiPartParser]

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user).order_by("-uploaded_at")

    def post(self, request):
        if request.content_type == "application/json":
            serializer = DocumentSerializer(data=request.data)
        else:
            if "content" in request.data:
                raise ValidationError(
                    {"detail": "Send either a file upload or JSON title and content, not both."}
                )

            upload_serializer = DocumentUploadSerializer(data=request.data)
            upload_serializer.is_valid(raise_exception=True)
            uploaded_file = upload_serializer.validated_data["file"]
            if uploaded_file.size > MAX_FILE_SIZE:
                return Response(
                    {"detail": "File exceeds the 5 MB size limit."},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )
            if Path(uploaded_file.name).suffix.lower() not in ALLOWED_FILE_TYPES:
                raise ValidationError(
                    {"file": "Only .txt, .md, and .csv files are allowed."}
                )
            try:
                content = uploaded_file.read().decode("utf-8")
            except UnicodeDecodeError as error:
                raise ValidationError(
                    {"file": "File must contain UTF-8 text."}
                ) from error

            serializer = DocumentSerializer(
                data={
                    "title": upload_serializer.validated_data.get("title")
                    or uploaded_file.name,
                    "content": content,
                }
            )

        serializer.is_valid(raise_exception=True)
        document = serializer.save(owner=request.user)
        return Response(
            DocumentSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)

    def destroy(self, request, *args, **kwargs):
        document = get_object_or_404(Document, pk=kwargs["pk"])
        if document.owner_id != request.user.id:
            raise PermissionDenied("You do not own this document.")
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class QueryCreateView(APIView):
    def post(self, request):
        serializer = QueryLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query_log = QueryLog.objects.create(
            query_text=serializer.validated_data["query_text"],
            user=request.user,
        )
        return Response(
            QueryLogSerializer(query_log).data,
            status=status.HTTP_201_CREATED,
        )


class QueryListView(generics.ListAPIView):
    serializer_class = QueryLogSerializer

    def get_queryset(self):
        return QueryLog.objects.filter(user=self.request.user).order_by("-created_at")
