from django.urls import path

from . import views


app_name = "change_management"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("requests/", views.request_list, name="request_list"),
    path("requests/new/", views.request_create, name="request_create"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/edit/", views.request_update, name="request_update"),
    path("requests/<int:pk>/submit/", views.submit_request, name="submit_request"),
    path("requests/<int:pk>/transition/", views.transition_request, name="transition_request"),
    path("requests/<int:pk>/comments/", views.add_comment, name="add_comment"),
    path("requests/<int:pk>/evidence/", views.add_evidence, name="add_evidence"),
    path("requests/<int:pk>/risk/", views.update_risk, name="update_risk"),
    path("queue/", views.approval_queue, name="approval_queue"),
    path("approvals/<int:pk>/decide/", views.decide_step, name="decide_step"),
]
