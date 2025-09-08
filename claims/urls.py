from django.urls import path
from . import views

urlpatterns = [
    path("", views.claim_list, name="claim-list"),
    path("claim/<int:pk>/", views.claim_detail, name="claim-detail"),

    # CRUD
    path("claims/create/", views.claim_create, name="claim-create"),
    path("claims/<int:pk>/update/", views.claim_update, name="claim-update"),
    path("claims/<int:pk>/delete/", views.claim_delete, name="claim-delete"),

    # Flags & Notes (HTMX)
    path("claims/<int:pk>/flag-toggle/", views.claim_flag_toggle, name="claim-flag"),
    path("claims/<int:pk>/notes/list/", views.notes_list, name="note-list"),
    path("claims/<int:pk>/notes/add/", views.note_add, name="note-add"),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    path("claims/form/close/", views.claim_form_close, name="claim-form-close"),
]
