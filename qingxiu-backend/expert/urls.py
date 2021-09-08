from django.urls import path

from . import views, views_expert

urlpatterns = [
    path('expert/unit/', views.UnitView.as_view()),
    path('expert/date/', views.TimeView.as_view()),
    path('expert/title/', views.ExpertTitleView.as_view()),
    path('expert/type/', views.ExpertProjectTypeView.as_view()),
    path('expert/field/', views.ExpertFieldView.as_view()),
    path('expert/field/<int:field_id>/', views.ExpertFieldView.as_view()),
    path('expert/education/', views.ExpertEducationView.as_view()),
    path('expert/education/<int:education_id>/',
         views.ExpertEducationView.as_view()),
    path('expert/work/', views.ExpertWorkView.as_view()),
    path('expert/work/<int:work_id>/', views.ExpertWorkView.as_view()),
    path('expert/duty/', views.ExpertDutyView.as_view()),
    path('expert/duty/<int:duty_id>/', views.ExpertDutyView.as_view()),
    path('expert/agency/', views.ExpertAgencyView.as_view()),
    path('expert/agency/<int:agency_id>/', views.ExpertAgencyView.as_view()),
    path('expert/avoidance/', views.AvoidanceUnitView.as_view()),
    path('expert/avoidance/<int:avoidance_id>/',
         views.AvoidanceUnitView.as_view()),
    path('expert/enclosure/', views.EnclosureView.as_view()),
    path('expert/enclosure/<int:enclosure_id>/', views.EnclosureView.as_view()),
    path('expert/record/', views.ExpertRecordEditView.as_view()),
    path('expert/exit/', views.ExpertRecordExitView.as_view()),
    path('expert/', views_expert.ExpertView.as_view()),
    path('expert/<int:expert_id>/', views_expert.ExpertView.as_view()),
    path('expert/register/', views.ExpertRegisterView.as_view()),
]
