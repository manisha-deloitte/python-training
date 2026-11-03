from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Document, QueryLog


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "title", "content", "uploaded_at", "owner"]
        read_only_fields = ["id", "uploaded_at", "owner"]


class DocumentUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    file = serializers.FileField()


class QueryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryLog
        fields = ["id", "query_text", "result_summary", "created_at", "user"]
        read_only_fields = ["id", "result_summary", "created_at", "user"]
