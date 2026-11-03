from django.contrib import admin
from django.urls import include, path

from apps.api.schema import OpenApiSchemaView, SwaggerUIView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", OpenApiSchemaView.as_view(), name="schema"),
    path("api/docs/", SwaggerUIView.as_view(), name="swagger-ui"),
    path("", include("apps.api.urls")),
]
