from django.urls import path
from .views import *

urlpatterns = [
    path('authentication/', MarkAPIView.as_view(), name="Authentication"),
    path('marks/', MarkWithIDAPIView.as_view(), name="Marks"),
    path('register/', RegisterAPIView.as_view(), name="Register"),
    path('login/', LoginApiView, name="Login"),
    path('logout/', LogoutApiView.as_view(), name='Logout'),
    path('register_admin/', RegisterAdminAPIView.as_view(), name="RegisterAdmin"),
    path('modify_user/', ModifyUserAPIView.as_view(), name="ModifyUser"),
    path('delete_user/', DeleteUserAPIView.as_view(), name="DeleteUser"),
    path('get_user/', GetUserAPIView.as_view(), name="GetUser"),
    path('delete_userAdmin/', DeleteUserAdminVIEW.as_view(), name="Delete_UserAdmin"),
]