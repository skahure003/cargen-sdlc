from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("policy/", views.policy, name="policy"),
    path("policy/download/", views.policy_download, name="policy_download"),
    path("assets/<str:filename>", views.asset, name="asset"),
    path("templates/", views.templates_index, name="templates_index"),
    path("templates/download/<slug:slug>/", views.template_download, name="template_download"),
    path("background/", views.background_index, name="background_index"),
    path("background/<slug:slug>/", views.background_detail, name="background_detail"),
    path("areas/", views.area_index, name="area_index"),
    path("areas/<slug:slug>/", views.area_detail, name="area_detail"),
    path("controls/", views.controls_index, name="controls_index"),
    path("controls/<slug:section>/", views.control_section, name="control_section"),
    path(
        "controls/<slug:section>/<slug:slug>/",
        views.control_detail,
        name="control_detail",
    ),
    path("risks/", views.risk_index, name="risk_index"),
    path("risks/<slug:slug>/", views.risk_detail, name="risk_detail"),
]
