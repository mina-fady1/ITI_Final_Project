from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('activate/<uuid:token>/', views.activate, name='activate'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('password/forgot/', views.forgot_password, name='forgot_password'),
    path('password/reset/<uuid:token>/', views.reset_password, name='reset_password'),
]
