from django.urls import path

from core import views


urlpatterns = [
    path("mocks/", views.dev_mock_list_view, name="dev-mock-list"),
    path("mocks/telas/<slug:screen_slug>/", views.dev_mock_screen_view, name="dev-mock-screen"),
]
