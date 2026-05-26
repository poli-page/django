from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Render endpoints
    path("render/pdf", views.render_pdf, name="render_pdf"),
    path("render/stream", views.render_stream, name="render_stream"),
    path("render/file", views.render_to_file, name="render_to_file"),
    path("render/preview", views.render_preview, name="render_preview"),
    # Document endpoints
    path("documents", views.document_create, name="document_create"),
    path("documents/<str:doc_id>", views.document_handle, name="document_handle"),
    path(
        "documents/<str:doc_id>/thumbnails",
        views.document_thumbnails,
        name="document_thumbnails",
    ),
    path("documents/<str:doc_id>/preview", views.document_preview, name="document_preview"),
    # Error handling
    path("errors/bad-version", views.error_bad_version, name="error_bad_version"),
]
