from rest_framework import serializers
from Authentication.models import User_Worker, CreateMark

class MonthlySummarySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    year_month = serializers.CharField()
    total_in_late = serializers.FloatField()

class UserWorkerSerializer(serializers.ModelSerializer):
    marks = MonthlySummarySerializer(many=True, read_only=True)

    class Meta:
        model = User_Worker
        fields = ['id', 'name', 'last_name', 'user', 'departament', 'total_hours', 'total_extra_hours', 'salary', 'extras', 'marks']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User_Worker
        fields = ['id', 'name', 'last_name', 'user', 'departament', 'salary', 'extras', 'marks']