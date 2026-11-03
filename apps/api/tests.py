from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Document, QueryLog, UserSession


class ApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="password123")
        self.other_user = User.objects.create_user(username="bob", password="password123")
        self.session = UserSession.objects.create(
            user=self.user,
            token="a" * 64,
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.session.token}")

    def test_registration_login_and_token_authentication(self):
        registration = self.client.post(
            "/register",
            {"username": "charlie", "password": "password123"},
            format="json",
        )
        self.assertEqual(registration.status_code, 201)

        self.client.credentials()
        unauthenticated = self.client.get("/documents")
        self.assertEqual(unauthenticated.status_code, 401)

        login = self.client.post(
            "/login",
            {"username": "alice", "password": "password123"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(UserSession.objects.filter(token=login.data["token"]).exists())

    def test_api_requests_are_logged_without_logging_the_token(self):
        with self.assertLogs("api.requests", level="INFO") as captured:
            response = self.client.get("/documents")

        self.assertEqual(response.status_code, 200)
        log_output = " ".join(captured.output)
        self.assertIn("method=GET", log_output)
        self.assertIn("path=/documents", log_output)
        self.assertIn("status=200", log_output)
        self.assertNotIn(self.session.token, log_output)

    def test_document_crud_and_ownership(self):
        created = self.client.post(
            "/documents",
            {"title": "Notes", "content": "Training content"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        document_id = created.data["id"]

        self.assertEqual(self.client.get(f"/documents/{document_id}").status_code, 200)

        other_document = Document.objects.create(
            owner=self.other_user,
            title="Private",
            content="Not yours",
        )
        self.assertEqual(self.client.get(f"/documents/{other_document.id}").status_code, 404)
        self.assertEqual(self.client.delete(f"/documents/{other_document.id}").status_code, 403)
        self.assertEqual(self.client.delete(f"/documents/{document_id}").status_code, 204)

    def test_document_file_upload_and_size_limit(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        mixed_request = self.client.post(
            "/documents",
            {
                "file": SimpleUploadedFile("mixed.txt", b"Uploaded content"),
                "title": "Mixed request",
                "content": "JSON-style content",
            },
            format="multipart",
        )
        self.assertEqual(mixed_request.status_code, 400)

        upload = SimpleUploadedFile("notes.txt", b"Uploaded content")
        created = self.client.post(
            "/documents",
            {"file": upload},
            format="multipart",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["content"], "Uploaded content")

        unsupported_file = SimpleUploadedFile("notes.exe", b"not allowed")
        unsupported = self.client.post(
            "/documents",
            {"file": unsupported_file},
            format="multipart",
        )
        self.assertEqual(unsupported.status_code, 400)

        missing_file = self.client.post(
            "/documents",
            {"title": "Upload without a file"},
            format="multipart",
        )
        self.assertEqual(missing_file.status_code, 400)

        invalid_json = self.client.post(
            "/documents",
            {"title": "Missing content"},
            format="json",
        )
        self.assertEqual(invalid_json.status_code, 400)

        oversized_file = SimpleUploadedFile(
            "large.txt",
            b"x" * (5 * 1024 * 1024 + 1),
        )
        oversized = self.client.post(
            "/documents",
            {"file": oversized_file},
            format="multipart",
        )
        self.assertEqual(oversized.status_code, 413)

    def test_documents_and_queries_are_paginated_and_private(self):
        for index in range(2):
            Document.objects.create(
                owner=self.user,
                title=f"Document {index}",
                content="Content",
            )
            QueryLog.objects.create(user=self.user, query_text=f"query {index}")

        other_document = Document.objects.create(
            owner=self.other_user,
            title="Other user's document",
            content="Content",
        )
        QueryLog.objects.create(user=self.other_user, query_text="other user's query")

        documents = self.client.get("/documents?page_size=1")
        self.assertEqual(documents.status_code, 200)
        self.assertEqual(documents.data["count"], 2)
        self.assertEqual(len(documents.data["results"]), 1)
        self.assertIsNotNone(documents.data["next"])
        self.assertIsNone(documents.data["previous"])

        queries = self.client.get("/queries?page_size=1")
        self.assertEqual(queries.status_code, 200)
        self.assertEqual(queries.data["count"], 2)
        self.assertEqual(len(queries.data["results"]), 1)

        self.assertNotIn(
            other_document.id,
            [item["id"] for item in documents.data["results"]],
        )

    def test_query_endpoint_creates_query_log(self):
        response = self.client.post(
            "/query",
            {"query_text": "Find recent reports"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["query_text"], "Find recent reports")
        self.assertEqual(response.data["result_summary"], "")
        self.assertIn("created_at", response.data)
        self.assertEqual(response.data["user"], self.user.id)
        self.assertTrue(
            QueryLog.objects.filter(
                id=response.data["id"],
                user=self.user,
                query_text="Find recent reports",
            ).exists()
        )

        history = self.client.get("/queries")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data["count"], 1)
        self.assertEqual(history.data["results"][0]["id"], response.data["id"])

        self.assertEqual(self.client.get("/query").status_code, 405)

    def test_api_schema_and_swagger_ui_are_available(self):
        schema = self.client.get("/api/schema/")
        self.assertEqual(schema.status_code, 200)
        self.assertIn("/documents", schema.data["paths"])
        self.assertIn("/queries", schema.data["paths"])
        self.assertEqual(
            list(schema.data["paths"]["/query"]),
            ["post"],
        )
        document_request = schema.data["paths"]["/documents"]["post"]["requestBody"]
        self.assertIn("application/json", document_request["content"])
        self.assertIn("multipart/form-data", document_request["content"])

        swagger_ui = self.client.get("/api/docs/")
        self.assertEqual(swagger_ui.status_code, 200)
