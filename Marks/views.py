from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from Authentication.models import *
from django.db.models import Sum, Count, Case, When, IntegerField
from django.db.models.functions import TruncMonth
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
from django.contrib.auth.models import User
from collections import defaultdict
from .serializer import *
from datetime import datetime

# Create your views here.
class marks_by_month(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        month = request.GET.get('month')  # Obtener el mes de los parámetros de la solicitud
        if month:
            marks_by_month = CreateMark.objects.filter(date__month=month).annotate(month=TruncMonth('date')).values('month', 'user').annotate(total_marks=Count('id'))
            admins = User.objects.all()
            if marks_by_month or admins:
                marks_list = []
                marks_list_admin = []
                for admin in admins:
                    admin_user = User.objects.get(username=admin.username)
                    marks_list_admin.append({'nameAdmin': admin_user.first_name, 'last_nameAdmin': admin_user.last_name, 'userAdmin': admin_user.username})
                for mark in marks_by_month:
                    month = mark['month'].strftime('%B, %Y')
                    user = User_Worker.objects.get(id=mark['user'])
                    total_marks = mark['total_marks']
                    marks_list.append({'month': month, 'name': user.name, 'last_name': user.last_name, 'user': user.user, 'total_marks': total_marks})
                return JsonResponse({'marks_list': marks_list, 'marks_list_admin': marks_list_admin})
            else:
                return JsonResponse({'error': 'No se encontraron marcas para este mes'})
        else:
            return JsonResponse({'error': 'No se proporcionó un mes válido'})

class Get_All_Information(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request, user, month):
        try:
            userSearch = User_Worker.objects.get(user=user)
            marks = CreateMark.objects.filter(user=userSearch, date__month=month, date__year=now().year).order_by('date')

            marks_by_date = defaultdict(list)
            for mark in marks:
                date_key = mark.date
                marks_by_date[date_key].append(mark)

            marks_list = []
            salary_hour = userSearch.salary / 8
            salary_extra = userSearch.extras
            hours = 0.0
            minutes = 0.0
            hours_extra = 0.0
            minutes_extra = 0.0

            for date, daily_marks in marks_by_date.items():
                yes = 0
                entries = [m for m in daily_marks if m.in_out == 'Entrada']
                exits = [m for m in daily_marks if m.in_out == 'Salida']

                while entries and exits:
                    entry = entries.pop(0)  # Obtén la primera entrada
                    if entry.in_late:
                        if yes == 0:
                            yes = yes + 1
                            in_late = 'Sí'
                        else:
                            in_late = ''
                    else:
                        if yes == 0:
                            yes = yes + 1
                            in_late = 'No'
                        else:
                            in_late = ''

                    corresponding_exit = None
                    for i, exit in enumerate(exits):
                        if exit.date == date:
                            corresponding_exit = exit
                            exits.pop(i)
                            break

                    if corresponding_exit:
                        hours_worked = corresponding_exit.total_hours
                        extra_hours = corresponding_exit.hours_extras

                        total_extra_hours = 0
                        total_extra_salary = 0
                        total_normal_salary = 0

                        # Si las horas trabajadas exceden 8, el resto va a horas extras
                        if hours_worked > 8:
                            extra_hours += hours_worked - 8
                            total_normal_salary = 8
                            total_hours_worked = f'{8}:00'  # Las horas normales se fijan en 8
                        elif hours_worked == 0:
                            total_hours_worked = '00:00'
                        elif hours_worked <= 0.59:
                            hours = int(hours_worked)
                            minutes = (hours_worked - hours)
                            minutes_formatted = minutes * 100
                            total_normal_salary = float(minutes_formatted) / 60
                            minutes_str = str(minutes).replace('0.', '')
                            total_hours_worked = f'{hours}:{minutes_str}'
                        else:
                            hours = int(hours_worked)
                            minutes = (hours_worked - hours)
                            minutes_formatted = str(minutes).replace('0.', '')
                            total_hours_worked = f'{hours}:{minutes_formatted}'
                            minutes_salary = float(minutes) * 100 / 60
                            total_normal_salary = hours + minutes_salary

                        total_extra_hours += extra_hours
                        if extra_hours <= 0.59:
                            if extra_hours <= 0.09:
                                hours = int(extra_hours)
                                minutes = (extra_hours - hours)
                                minutes_formatted = minutes * 100
                                total_extra_salary = float(minutes_formatted) / 60
                                total_extra_hours = f'{hours}:{minutes}'
                            else:
                                hours = int(extra_hours)
                                minutes = (extra_hours - hours)
                                total_extra_salary = float(extra_hours) * 100 / 60
                                total_extra_hours = f'{hours}:{minutes}'
                        if extra_hours == 0:
                            total_extra_hours = '00:00'
                        else:
                            hours = int(extra_hours)
                            minutes = (extra_hours - hours)
                            minutes_formatted = minutes * 100
                            total_extra_salary = hours + (float(minutes_formatted) / 60)
                            if minutes < 0.10:
                                minutes_str = str(minutes).replace('.0', '')
                                total_extra_hours = f'{hours}:{minutes_str}'
                            elif minutes >= 0.10:
                                minutes_str = str(minutes).replace('0.', '')
                                total_extra_hours = f'{hours}:{minutes_str}'


                        # Convertir horas y minutos para el formato correcto

                        # Cálculo del salario: horas normales y extras
                        total_salary = (salary_hour * float(total_normal_salary)) + (salary_extra * float(total_extra_salary))

                        # Añade la información al resultado
                        marks_list.append({
                            'date': date.strftime('%Y-%m-%d'),
                            'name': userSearch.name,
                            'last_name': userSearch.last_name,
                            'user': userSearch.user,
                            'entry_hours': entry.hours if entry else None,
                            'exit_hours': corresponding_exit.hours if corresponding_exit else None,
                            'total_hours': total_hours_worked,
                            'extra_hours': total_extra_hours,
                            'total_salary': total_salary,
                            'in_late': in_late,
                            'out_late': corresponding_exit.out_late if corresponding_exit else None
                        })

            return JsonResponse({'marks': marks_list}, status=200)

        except User_Worker.DoesNotExist:
            return JsonResponse({'error': 'El usuario no existe'}, status=404)

        
class Get_All_InformationByUserFilter(APIView):
    authentication_classes = [TokenAuthentication]
    
    def get(self, request, user, reportType, selectedMonth):
        try:
            userSearch = User_Worker.objects.get(user=user)
            
            # Filtrar las marcas según el tipo de reporte
            if reportType == "15":
                marks = CreateMark.objects.filter(user=userSearch, date__month=selectedMonth, date__day__lte=15)
            elif reportType == "30":
                marks = CreateMark.objects.filter(user=userSearch, date__month=selectedMonth, date__day__gte=16, date__day__lte=30)
            else:
                marks = CreateMark.objects.filter(user=userSearch, date__month=selectedMonth)
            
            marks_by_date = defaultdict(list)
            for mark in marks:
                date_key = mark.date
                marks_by_date[date_key].append(mark)

            marks_list = []
            salary_hour = userSearch.salary / 8  # Cálculo del salario por hora
            salary_extra = userSearch.extras  # Pago por horas extras

            for date, daily_marks in marks_by_date.items():
                yes = 0
                entries = [m for m in daily_marks if m.in_out == 'Entrada']
                exits = [m for m in daily_marks if m.in_out == 'Salida']

                # Reiniciar los valores para cada día
                total_hours_worked = 0
                total_salary = 0

                while entries and exits:
                    entry = entries.pop(0)
                    if entry.in_late:
                        if yes == 0:
                            yes = yes + 1
                            in_late = 'Sí'
                        else:
                            in_late = ''
                    else:
                        if yes == 0:
                            yes = yes + 1
                            in_late = 'No'
                        else:
                            in_late = ''
                    corresponding_exit = None
                    for i, exit in enumerate(exits):
                        if exit.date == date:
                            corresponding_exit = exit
                            exits.pop(i)
                            break

                    if corresponding_exit:
                        hours_worked = corresponding_exit.total_hours
                        extra_hours = corresponding_exit.hours_extras

                        total_extra_hours = 0
                        total_extra_salary = 0
                        total_normal_salary = 0

                        # Si las horas trabajadas exceden 8, el resto va a horas extras
                        if hours_worked > 8:
                            extra_hours += hours_worked - 8
                            total_normal_salary = 8
                            total_hours_worked = f'{8}:00'  # Las horas normales se fijan en 8
                        elif hours_worked == 0:
                            total_hours_worked = '00:00'
                        elif hours_worked <= 0.59:
                            hours = int(hours_worked)
                            minutes = (hours_worked - hours)
                            minutes_formatted = minutes * 100
                            total_normal_salary = float(minutes_formatted) / 60
                            minutes_str = str(minutes).replace('0.', '')
                            total_hours_worked = f'{hours}:{minutes_str}'
                        else:
                            hours = int(hours_worked)
                            minutes = (hours_worked - hours)
                            minutes_formatted = str(minutes).replace('0.', '')
                            total_hours_worked = f'{hours}:{minutes_formatted}'
                            minutes_salary = float(minutes) * 100 / 60
                            total_normal_salary = hours + minutes_salary

                        total_extra_hours += extra_hours
                        if extra_hours <= 0.59:
                            if extra_hours <= 0.09:
                                hours = int(extra_hours)
                                minutes = (extra_hours - hours)
                                minutes_formatted = minutes * 100
                                total_extra_salary = float(minutes_formatted) / 60
                                total_extra_hours = f'{hours}:{minutes}'
                            else:
                                hours = int(extra_hours)
                                minutes = (extra_hours - hours)
                                total_extra_salary = float(extra_hours) * 100 / 60
                                total_extra_hours = f'{hours}:{minutes}'
                        if extra_hours == 0:
                            total_extra_hours = '00:00'
                        else:
                            hours = int(extra_hours)
                            minutes = (extra_hours - hours)
                            minutes_formatted = minutes * 100
                            total_extra_salary = hours + (float(minutes_formatted) / 60)
                            if minutes < 0.10:
                                minutes_str = str(minutes).replace('.0', '')
                                total_extra_hours = f'{hours}:{minutes_str}'
                            elif minutes >= 0.10:
                                minutes_str = str(minutes).replace('0.', '')
                                total_extra_hours = f'{hours}:{minutes_str}'


                        # Convertir horas y minutos para el formato correcto

                        # Cálculo del salario: horas normales y extras
                        total_salary = (salary_hour * float(total_normal_salary)) + (salary_extra * float(total_extra_salary))
                        total_salary = round(total_salary)

                    marks_list.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'name': userSearch.name,
                        'last_name': userSearch.last_name,
                        'user': userSearch.user,
                        'entry_hours': entry.hours if entry else None,
                        'exit_hours': corresponding_exit.hours if corresponding_exit else None,
                        'total_hours': total_hours_worked,
                        'extra_hours': total_extra_hours,
                        'in_late': in_late,
                        'total_salary': total_salary,
                    })

            return JsonResponse({'marks': marks_list}, status=200)

        except User_Worker.DoesNotExist:
            return JsonResponse({'error': 'El usuario no existe'}, status=404)
            
class AllMarksByWorkerView(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        current_year = now().year
        month = request.GET.get('month')
        reportType = request.GET.get('reportType')

        if not month or month == '0':
            return Response({"message": "Elija un mes", "messagetype": "error"})

        # Filtrar las marcas de acuerdo al tipo de reporte
        if reportType == '15':
            date_filter = CreateMark.objects.filter(
                date__year=current_year,
                date__month=month,
                date__day__lte=15
            )
        elif reportType == '30':
            date_filter = CreateMark.objects.filter(
                date__year=current_year,
                date__month=month,
                date__day__gte=16,
                date__day__lte=30
            )
        else:
            date_filter = CreateMark.objects.filter(
                date__year=current_year,
                date__month=month
            )

        # Agrupar por usuario y por mes, acumulando las horas trabajadas y extras
        monthly_summaries = date_filter.values(
            'user_id',
            year_month=TruncMonth('date'),
        ).annotate(
            total_hours=Sum('total_hours'),
            total_extra_hours=Sum('hours_extras'),
            total_in_late=Sum(Case(When(in_late=True, then=1), default=0, output_field=IntegerField()))
        ).order_by('user_id', 'year_month')

        # Obtener todos los trabajadores
        workers = User_Worker.objects.all()
        worker_data = []

        for worker in workers:
            # Filtrar las resúmenes mensuales por usuario
            summaries = [summary for summary in monthly_summaries if summary['user_id'] == worker.id]

            # Inicializar totales
            total_regular_hours = 0.0
            total_extra_hours = 0.0
            total_salary = 0.0
            salary_hour = worker.salary / 8
            salary_extra = worker.extras
            total_hours = 0

            for summary in summaries:
                total_hours_float = float(summary['total_hours'])  # Convertir Decimal a float

                # Calcular horas normales y extras sin limitación de 8 horas diarias
                total_regular_hours += total_hours_float
                total_extra_hours += float(summary['total_extra_hours'])  # Convertir Decimal a float si es necesario

                # Aplicar redondeo y cálculo de salario
                hours = int(total_regular_hours)
                minutes = (total_regular_hours - hours)
                if minutes <= 0.59:
                    if minutes < 0.10:
                        minutes_formatted = float(minutes) * 100
                        minutes_formatted = str(minutes_formatted).replace('0.', '')
                        total_hours = f'{hours}h:{minutes_formatted}m'
                    else:
                        minutes_formatted = float(minutes) * 100
                        minutes_formatted = round(minutes_formatted)
                        minutes_formatted = str(minutes_formatted).replace('0.', '')
                        total_hours = f'{hours}h:{minutes_formatted}m'
                else:
                    hours += 1
                    minutes = 1 - float(minutes)
                    minutes_formatted = minutes * 100
                    minutes_formatted = round(minutes_formatted)
                    minutes_formatted = str(minutes_formatted).replace('.0', '')
                    total_hours = f'{hours}h:{minutes_formatted}m'
                total_salary += salary_hour * (float(hours) + (float(minutes) * 100 / 60))
                total_salary = round(total_salary)

            # Calcular el salario total incluyendo las horas extras
            extra_hours_number = total_extra_hours
            minutes_extra_number = 0.0
            if extra_hours_number > 20:
                extra_hours_number = 20
                total_salary += salary_extra * extra_hours_number
            else:
                hours_extra = int(extra_hours_number)
                minutes_extra = (extra_hours_number - hours_extra)
                if minutes_extra <= 0.59:
                    if minutes_extra < 0.10:
                        minutes_extra_formatted = float(minutes_extra) * 100
                        minutes_extra_number = round(minutes_extra_formatted)
                        minutes_extra_formatted = str(minutes_extra_formatted).replace('0.', '')
                        extra_hours = f'{hours_extra}h:0{round(float(minutes_extra_formatted))}m'
                    else:
                        minutes_extra_formatted = float(minutes_extra) * 100
                        minutes_extra_number = round(minutes_extra_formatted)
                        minutes_extra_formatted = str(minutes_extra_formatted).replace('.0', '')
                        extra_hours = f'{hours_extra}h:{round(float(minutes_extra_formatted))}m'
                else:
                    hours_extra += 1
                    minutes_extra_number = (float(minutes_extra) * 100) - 60
                    minutes_extra_number = round(minutes_extra_number)
                    if minutes_extra_number < 10:
                        extra_hours = f'{hours_extra}h:0{minutes_extra_number}m'
                    else:
                        extra_hours = f'{hours_extra}:{minutes_extra_number}'
                total_salary += salary_extra * (float(hours_extra) + (minutes_extra_number / 60))
                total_salary = round(total_salary)

            # Almacenar la información en la lista final
            worker_data.append({
                'id': worker.id,
                'name': worker.name,
                'last_name': worker.last_name,
                'user': worker.user,
                'total_hours': total_hours,
                'total_extra_hours': extra_hours,
                'departament': worker.departament,
                'salary': total_salary,
                'extras': worker.extras,
                'marks': summaries,  # Agregamos las marcas individuales para referencia
            })

        # Serializamos los datos
        serializer = UserWorkerSerializer(worker_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

def calculate_time_diff(start_time, end_time):
    formato_hora = "%H:%M"
    t1 = datetime.strptime(str(start_time), formato_hora)
    t2 = datetime.strptime(str(end_time), formato_hora)
    
    # Calcula la diferencia en horas y minutos
    diferencia = t2 - t1
    arreglado = str(diferencia).replace(':', '.')
    
    # Divide la cadena por el segundo punto y toma las dos primeras partes
    partes = arreglado.split('.')
    if len(partes) > 2:
        arreglado = f"{partes[0]}.{partes[1]}"
    
    return float(arreglado)

class MarksByMonthUser(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        month_str = request.GET.get('month')
        user_request = request.GET.get('user')
        report_type = request.GET.get('reportType')
        
        try:
            month = int(month_str)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'El mes debe ser un número entero válido'}, status=404)
        
        if user_request:
            try:
                user_instance = User_Worker.objects.get(user=user_request)

                if report_type == '15':
                    marks_by_month = CreateMark.objects.filter(
                        user=user_instance, 
                        date__month=month, 
                        date__day__lte=15
                    ).values('date', 'in_out', 'hours', 'hours_extras', 'in_late').order_by('date', 'in_out')
                    total_worked = CreateMark.objects.filter(
                        user=user_instance, 
                        date__month=month, 
                        date__day__lte=15
                    ).values('date').annotate(
                        suma_total=Sum('total_hours'), 
                        suma_extras=Sum('hours_extras')
                    ).order_by('date')

                    if not marks_by_month:
                        return JsonResponse({'error': 'No se encontraron marcas para el rango del 1 al 15'}, status=404)

                elif report_type == '30':
                    marks_by_month = CreateMark.objects.filter(
                        user=user_instance, 
                        date__month=month, 
                        date__day__gte=16, 
                        date__day__lte=30
                    ).values('date', 'in_out', 'hours', 'hours_extras', 'in_late').order_by('date', 'in_out')
                    total_worked = CreateMark.objects.filter(
                        user=user_instance, 
                        date__month=month, 
                        date__day__gte=16, 
                        date__day__lte=30
                    ).values('date').annotate(
                        suma_total=Sum('total_hours'), 
                        suma_extras=Sum('hours_extras')
                    ).order_by('date')

                    if not marks_by_month:
                        return JsonResponse({'error': 'No se encontraron marcas para el rango del 16 al 30'}, status=404)

                else:
                    marks_by_month = CreateMark.objects.filter(
                        user=user_instance, 
                        date__month=month
                    ).values('date', 'in_out', 'hours', 'hours_extras', 'in_late').order_by('date', 'in_out')
                    total_worked = CreateMark.objects.filter(
                        user=user_instance, 
                        date__month=month
                    ).values('date').annotate(
                        suma_total=Sum('total_hours'), 
                        suma_extras=Sum('hours_extras')
                    ).order_by('date')

                    if not marks_by_month:
                        return JsonResponse({'error': 'No se encontraron marcas para el mes completo'}, status=404)

                # Procesar marcas si se encuentran
                marks_dict = {}
                for mark in marks_by_month:
                    date = mark['date']
                    if date not in marks_dict:
                        marks_dict[date] = {'entries': [], 'exits': [], 'in_late': False}
                    
                    if mark['in_out'] == 'Entrada':
                        marks_dict[date]['entries'].append(mark)
                        if mark['in_late']:
                            marks_dict[date]['in_late'] = True
                    elif mark['in_out'] == 'Salida':
                        marks_dict[date]['exits'].append(mark)

                marks_list = []
                for date, records in marks_dict.items():
                    entries = sorted(records['entries'], key=lambda x: x['hours'])
                    exits = sorted(records['exits'], key=lambda x: x['hours'], reverse=True)

                    if entries and exits:
                        first_entry = entries[0]
                        last_exit = exits[0]

                        in_late = first_entry['in_late']

                        extra_hours_diff = 0

                        total_hours = calculate_time_diff(first_entry['hours'], last_exit['hours'])
                        if total_hours > 8:
                            extra_hours_diff = total_hours - 8
                            total_hours = 8.00
                            extra_hours_diff = round(extra_hours_diff, 2)
                            extra_hours_diff = str(extra_hours_diff).replace('.', ':')
                        total_hours = str(total_hours).replace('.', ':')

                        # Calcular el salario y horas extras para cada día
                        total_salary = 0
                        hours = 0
                        total_extra_hours = 0
                        salary_hour = user_instance.salary / 8
                        extra_salary = user_instance.extras
                        total_regular_hours = 0
                        total_extra_salary = 0
                        for day in total_worked:
                            if day['date'] == date:
                                total_hours_float = day['suma_total']
                                if total_hours_float < 1:
                                    if total_hours_float <= 0.09:
                                        hours = int(total_hours_float)
                                        minutes = float(total_hours_float - hours)
                                        total_salary = salary_hour * (float(hours) + (float(minutes) * 100 / 60))
                                    else:
                                        total_regular_hours = total_hours_float
                                        hours = int(total_hours_float)
                                        minutes = (total_hours_float - hours)
                                        total_salary = salary_hour * (hours + (float(minutes) * 100 / 60))
                                else:
                                    if total_hours_float > 8:
                                        total_regular_hours = 8  # Máximo 8 horas normales por día
                                        total_extra_hours += float(total_hours_float) - 8.0  # Lo que sobre pasa son horas extras
                                        hours = int(total_regular_hours)
                                        minutes = (total_regular_hours - hours)
                                        total_salary = salary_hour * (float(hours) + (float(minutes) * 100 / 60))
                                    elif total_hours_float == 8:
                                        total_regular_hours = 8  # Máximo 8 horas normales por día
                                        total_salary = salary_hour * float(total_regular_hours)
                                    else:
                                        total_regular_hours = total_hours_float
                                        hours = int(total_regular_hours)
                                        minutes = (total_regular_hours - hours)
                                        total_salary = salary_hour * (float(hours) + (float(minutes) * 100 / 60))

                                total_extra_hours += float(day['suma_extras'])
                                if total_extra_hours < 1:
                                    hours = int(total_extra_hours)
                                    minutes = (total_extra_hours - hours)
                                    total_extra_salary = (hours + (float(minutes) * 100 / 60))
                                else:
                                    hours = int(total_extra_hours)
                                    minutes = (total_extra_hours - hours)
                                    total_extra_salary = (hours + (float(minutes) * 100 / 60))

                                total_salary += extra_salary * total_extra_salary

                                    

                        marks_list.append({
                            'date': date,
                            'entry_hours': first_entry['hours'],
                            'exit_hours': last_exit['hours'],
                            'total_salary': round(total_salary),
                            'total_hours': total_hours,
                            'extra_hours': extra_hours_diff,
                            'in_late': 'Sí' if in_late else 'No',
                        })

                return JsonResponse({'marks_list': marks_list})

            except User_Worker.DoesNotExist:
                return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

        else:
            return JsonResponse({'error': 'No se proporcionó un usuario válido'}, status=404)