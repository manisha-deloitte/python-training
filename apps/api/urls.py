from django.urls import path

from . import views


urlpatterns = [
    path("register", views.RegisterView.as_view(), name="register"),
    path("login", views.LoginView.as_view(), name="login"),
    path(
        "documents",
        views.DocumentListCreateView.as_view(),
        name="documents",
    ),
    path("documents/<int:pk>", views.DocumentDetailView.as_view(), name="document-detail"),
    path(
        "query",
        views.QueryCreateView.as_view(),
        name="query",
    ),
    path(
        "queries",
        views.QueryListView.as_view(),
        name="queries",
    ),
]
