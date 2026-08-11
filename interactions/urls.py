from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    path('project/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
    path('project/<int:pk>/rate/', views.rate_project, name='rate_project'),
    path('project/<int:pk>/report/', views.report_project, name='report_project'),
    path('comment/<int:pk>/report/', views.report_comment, name='report_comment'),
]