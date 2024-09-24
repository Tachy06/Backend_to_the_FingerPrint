from django.db import models

# Create your models here.

class User_Worker(models.Model):
    name = models.CharField(max_length=255, null=False)
    last_name = models.CharField(max_length=255, null=False)
    user = models.CharField(max_length=255, null=False, unique=True)
    departament = models.CharField(max_length=255, null=False)
    total_hours = models.CharField(max_length=10000,null=False, default=0)
    total_extra_hours = models.CharField(max_length=10000, null=False, default=0)
    salary = models.FloatField(null=False)
    extras = models.FloatField(null=False)
    hourIn = models.FloatField(null=False)
    hourOut = models.FloatField(null=False)
    photo = models.BinaryField(null=True, blank=True)
    fingerPrint_template = models.BinaryField(null=False)

    class Meta:
        verbose_name = 'User_Worker'
        verbose_name_plural = "Users_Workers"


class CreateMark(models.Model):
    user = models.ForeignKey(User_Worker, related_name='marks', on_delete=models.CASCADE)
    in_out = models.CharField(max_length=255, null=False)
    hours = models.CharField(max_length=255, null=True)
    hours_extras = models.DecimalField(max_digits=5, decimal_places=2, null=True, default=0.00)
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, default=0.00)
    in_late = models.BooleanField(default=False)
    out_late = models.BooleanField(default=False)
    date = models.DateField(auto_now_add=True)
    late_calculated = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'CreateMark'
        verbose_name_plural = "CreateMarks"