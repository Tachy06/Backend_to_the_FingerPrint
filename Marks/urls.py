from django.urls import path
from .views import *

urlpatterns = [
    path('get_marks/', marks_by_month.as_view(), name="GetMarks"),
    path('get_all_information/<str:user>/<int:month>/', Get_All_Information.as_view(), name="Get_All_Information"),
    path('get_all_informationFilter/<str:user>/<str:reportType>/<str:selectedMonth>/', Get_All_InformationByUserFilter.as_view(), name="Get_All_Information"),
    path('all-marks/', AllMarksByWorkerView.as_view(), name="AllMarks"),
    path('get_marks_user/', MarksByMonthUser.as_view(), name="Get_Marks_User"),
]