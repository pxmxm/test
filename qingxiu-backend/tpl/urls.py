from django.urls import path

from . import views_download

urlpatterns = [
    path('download/<str:_id>/', views_download.DownloadView.as_view()),
]
