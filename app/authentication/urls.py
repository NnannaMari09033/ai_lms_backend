from django.urls import path
from .views import register_view, login_view, user_detail_view, user_list_view, change_password_view,reset_password_request_view,set_new_password_view, student_profile_view, instructor_profile_view
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView



urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('users/<int:pk>/', user_detail_view, name='user-detail'),
    path('users/', user_list_view, name='user-list'),         
    path('change-password/', change_password_view, name='change-password'),
    path('reset-password/', reset_password_request_view, name='reset-password'),
    path('set-new-password/', set_new_password_view, name='set-new-password'),
    path('student-profile/', student_profile_view, name='student-profile'),
    path('instructor-profile/', instructor_profile_view, name='instructor-profile'),      
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),   
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


]
