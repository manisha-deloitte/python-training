from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


OPENAPI_SCHEMA = {
    "openapi": "3.0.3",
    "info": {
        "title": "Document and Query API",
        "version": "1.0.0",
        "description": "Token-authenticated document management and query history API.",
    },
    "servers": [{"url": "/"}],
    "security": [{"TokenAuth": []}],
    "paths": {
        "/register": {
            "post": {
                "tags": ["Authentication"],
                "security": [],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Registration"}
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": "Account created.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Registration"}
                            }
                        },
                    },
                    "400": {"description": "Invalid registration data."},
                },
            }
        },
        "/login": {
            "post": {
                "tags": ["Authentication"],
                "security": [],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Login"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Login successful.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Token"}
                            }
                        },
                    },
                    "400": {"description": "Invalid username or password."},
                },
            }
        },
        "/documents": {
            "get": {
                "tags": ["Documents"],
                "parameters": [
                    {"$ref": "#/components/parameters/Page"},
                    {"$ref": "#/components/parameters/PageSize"},
                ],
                "responses": {
                    "200": {
                        "description": "Paginated documents belonging to the current user.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/PaginatedDocuments"
                                }
                            }
                        },
                    }
                },
            },
            "post": {
                "tags": ["Documents"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/DocumentCreate"}
                        },
                        "multipart/form-data": {
                            "schema": {"$ref": "#/components/schemas/DocumentUpload"}
                        },
                    },
                },
                "responses": {
                    "201": {
                        "description": "Document created.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Document"}
                            }
                        },
                    },
                    "400": {"description": "Invalid data, unsupported file, or invalid text encoding."},
                    "413": {"description": "Uploaded file exceeds 5 MB."},
                },
            },
        },
        "/documents/{id}": {
            "parameters": [
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            "get": {
                "tags": ["Documents"],
                "responses": {
                    "200": {
                        "description": "Document belonging to the current user.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Document"}
                            }
                        },
                    },
                    "404": {"description": "Document not found or not owned by the user."},
                },
            },
            "delete": {
                "tags": ["Documents"],
                "responses": {
                    "204": {"description": "Document deleted."},
                    "403": {"description": "Document belongs to another user."},
                    "404": {"description": "Document does not exist."},
                },
            },
        },
        "/query": {
            "post": {
                "tags": ["Queries"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/QueryCreate"}
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": "Query recorded.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/QueryLog"}
                            }
                        },
                    },
                    "400": {"description": "Invalid query data."},
                },
            },
        },
        "/queries": {
            "get": {
                "tags": ["Queries"],
                "parameters": [
                    {"$ref": "#/components/parameters/Page"},
                    {"$ref": "#/components/parameters/PageSize"},
                ],
                "responses": {
                    "200": {
                        "description": "Paginated query history for the current user.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/PaginatedQueries"}
                            }
                        },
                    }
                },
            }
        },
    },
    "components": {
        "securitySchemes": {
            "TokenAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Enter Token followed by a space and your token.",
            }
        },
        "parameters": {
            "Page": {
                "name": "page",
                "in": "query",
                "schema": {"type": "integer", "minimum": 1, "default": 1},
            },
            "PageSize": {
                "name": "page_size",
                "in": "query",
                "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
            },
        },
        "schemas": {
            "Registration": {
                "type": "object",
                "required": ["username", "password"],
                "properties": {
                    "id": {"type": "integer", "readOnly": True},
                    "username": {"type": "string", "maxLength": 150},
                    "password": {"type": "string", "writeOnly": True},
                },
            },
            "Login": {
                "type": "object",
                "required": ["username", "password"],
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string", "format": "password"},
                },
            },
            "Token": {
                "type": "object",
                "properties": {"token": {"type": "string"}},
            },
            "DocumentCreate": {
                "type": "object",
                "required": ["title", "content"],
                "properties": {
                    "title": {"type": "string", "maxLength": 255},
                    "content": {"type": "string"},
                },
            },
            "DocumentUpload": {
                "type": "object",
                "required": ["file"],
                "properties": {
                    "title": {"type": "string", "maxLength": 255},
                    "file": {
                        "type": "string",
                        "format": "binary",
                        "description": "UTF-8 .txt, .md, or .csv file up to 5 MB. Do not send a content field with a file.",
                    },
                },
            },
            "Document": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "readOnly": True},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "uploaded_at": {"type": "string", "format": "date-time"},
                    "owner": {"type": "integer"},
                },
            },
            "QueryCreate": {
                "type": "object",
                "required": ["query_text"],
                "properties": {"query_text": {"type": "string"}},
            },
            "QueryLog": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "readOnly": True},
                    "query_text": {"type": "string"},
                    "result_summary": {"type": "string", "readOnly": True},
                    "created_at": {"type": "string", "format": "date-time", "readOnly": True},
                    "user": {"type": "integer", "readOnly": True},
                },
            },
            "PaginatedDocuments": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "next": {"type": "string", "nullable": True},
                    "previous": {"type": "string", "nullable": True},
                    "results": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Document"},
                    },
                },
            },
            "PaginatedQueries": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "next": {"type": "string", "nullable": True},
                    "previous": {"type": "string", "nullable": True},
                    "results": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/QueryLog"},
                    },
                },
            },
        },
    },
}


class OpenApiSchemaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(OPENAPI_SCHEMA)


class SwaggerUIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return HttpResponse(
            """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Document and Query API - Swagger UI</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
  <script>
    window.onload = function () {
      SwaggerUIBundle({
        url: "/api/schema/",
        dom_id: "#swagger-ui",
        presets: [SwaggerUIBundle.presets.apis],
        layout: "BaseLayout"
      });
    };
  </script>
</body>
</html>"""
        )
