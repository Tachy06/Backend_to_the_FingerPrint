from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import base64
import cv2
from .models import *
import os
from datetime import date, datetime
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from Marks.serializer import *
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt

class MarkAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        in_out = request.data.get('in_out')
        fingerprint_data = request.data.get('fingerprint_data')

        if not in_out or not fingerprint_data:
            return Response("Faltan datos en la solicitud", status=status.HTTP_400_BAD_REQUEST)

        fingerprint_data = fingerprint_data.encode("ascii")
        fingerprintData_base64 = base64.b64decode(fingerprint_data)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        new_image = os.path.join(current_dir, 'images', 'huella1.jpg')
        save_image_from_base64(fingerprintData_base64, new_image)

        for user_search in User_Worker.objects.all():
            image_decode = base64.b64decode(user_search.fingerPrint_template)
            old_image = os.path.join(current_dir, 'images', 'huella2.jpg')
            save_image_from_base64(image_decode, old_image)

            if user_search.photo is None:
                image_data = None
            else:
                image_data = base64.b64encode(user_search.photo).decode('utf-8')

            # Obtener los resultados de la comparación
            score_response = comparate_fingerprint(new_image, old_image, user_search, in_out, image_data)

            # Verificar el puntaje de la comparación
            if score_response['score'] >= 2.3:
                user = score_response['user']
                in_out = score_response['in_out']
                photo = score_response['photo']
                score = score_response['score']
                
                # Lógica de entrada/salida
                today = date.today()
                first_mark = CreateMark.objects.filter(user=user, date=today).order_by('-id').first()
                all_marks_today = CreateMark.objects.filter(user=user, date=today)

                if in_out == "Entrada":
                    if first_mark and first_mark.in_out == "Entrada":
                        data = {
                            'message': f"Ya tienes una marca de entrada registrada para hoy {user.user}",
                        }
                        print(score)
                        return Response(data, status=status.HTTP_404_NOT_FOUND)

                    hours_entry = datetime.now().time().strftime("%H:%M")
                    late = float(hours_entry.replace(":", ".")) > user.hourIn

                    # Solo calcular la llegada tardía si no se ha calculado aún para hoy
                    if CreateMark.objects.filter(user=user, date=today, late_calculated=True).exists():
                        CreateMark.objects.create(user=user, in_out=in_out, hours=hours_entry.replace(".", ":"), hours_extras=0, total_hours=0)
                    else:
                        CreateMark.objects.create(user=user, in_out=in_out, hours=hours_entry.replace(".", ":"), hours_extras=0, total_hours=0, in_late=late, late_calculated=True)

                    data = {
                        'message': f"Entrada registrada {user.user}",
                        'photo': photo,
                        'score': score
                    }
                    print(score)
                    return Response(data, status=status.HTTP_200_OK)

                elif in_out == "Salida":
                    if first_mark and first_mark.in_out == "Salida":
                        data = {
                            'message': f"Ya tienes una marca de salida registrada para hoy {user.user}",
                        }
                        print(score)
                        return Response(data, status=status.HTTP_404_NOT_FOUND)

                    marks_in = CreateMark.objects.filter(user=user, in_out="Entrada", date=today).last()
                    if not marks_in:
                        data = {
                            'message': f"No tienes una marca de entrada registrada para hoy {user.user}",
                        }
                        return Response(data, status=status.HTTP_404_NOT_FOUND)

                    hours = datetime.now().time().strftime("%H:%M")
                    final_hours = hours

                    entry_hours = marks_in.hours
                    exit_hours = final_hours
                    total_hours = calcular_diferencia_decimal(entry_hours, exit_hours)
                    total_hours_marks = 0
                    for mark in all_marks_today:
                        total_hours_marks += mark.total_hours
                    
                    if total_hours_marks >= 8:
                        extras = total_hours
                        late = float(hours.replace(":", ".")) > user.hourOut
                        CreateMark.objects.create(user=user, in_out=in_out, hours=hours, hours_extras=extras, total_hours=0, out_late=late)
                    else:
                        if total_hours == 0.01:
                            total_hours = 0.01
                            late = float(hours.replace(":", ".")) > user.hourOut
                            CreateMark.objects.create(user=user, in_out=in_out, hours=hours, hours_extras=0, total_hours=total_hours, out_late=late)
                        if total_hours > 8:
                            extras = total_hours - 8
                            if extras > 20:
                                extras = 20
                            total_hours = 8
                            late = float(hours.replace(":", ".")) > user.hourOut
                            CreateMark.objects.create(user=user, in_out=in_out, hours=hours, hours_extras=extras, total_hours=total_hours, out_late=late)
                        else:
                            extras = 0
                            late = float(hours.replace(":", ".")) > user.hourOut
                            CreateMark.objects.create(user=user, in_out=in_out, hours=hours, hours_extras=extras, total_hours=total_hours, out_late=late)
                    data = {
                        'message': f"Salida registrada {user.user}",
                        'photo': photo,
                        'score': score
                    }
                    print(score)
                    return Response(data, status=status.HTTP_200_OK)
        # Si no se encontró una coincidencia con un puntaje mayor a 1.9
        response = {
            'message': '',
            'score': score_response['score']
        }
        print(score_response['score'])
        return Response(response, status=status.HTTP_404_NOT_FOUND)

def save_image_from_base64(image_data, filename):
    # Guardar los datos binarios en un archivo de imagen
    with open(filename, "wb") as file:
        file.write(image_data)

def comparate_fingerprint(new, old, user, in_out, photo):
    img1 = cv2.imread(new, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(old, cv2.IMREAD_GRAYSCALE)

    sift = cv2.SIFT_create()
    
    keypoints_1, descriptors_1 = sift.detectAndCompute(img1, None)
    keypoints_2, descriptors_2 = sift.detectAndCompute(img2, None)
    
    matches = cv2.FlannBasedMatcher({'algorithm': 1, 'trees': 10}, {}).knnMatch(descriptors_1, descriptors_2, k=2)
    
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)
    
    keypoints = 0
    if len(keypoints_1) >= len(keypoints_2):
        keypoints = len(keypoints_1)
    else:
        keypoints = len(keypoints_2)

    score = len(good_matches) / keypoints * 100

    # Empaquetar los datos en un diccionario
    result = {
        'score': score,
        'user': user,
        'in_out': in_out,
        'photo': photo
    }
    
    return result

class MarkWithIDAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        user = request.data.get('user')
        in_out = request.data.get('in_out')

        try:
            user = User_Worker.objects.get(user=user)
        except User_Worker.DoesNotExist:
            data = {
                'message': 'Usuario no encontrado',
            }
            return Response(data, status=status.HTTP_404_NOT_FOUND)

        try:
            today = date.today()
            last_mark = CreateMark.objects.filter(user=user, date=today).order_by('-id').first()
            all_marks_today = CreateMark.objects.filter(user=user, date=today)

            if in_out == "Entrada":
                if last_mark and last_mark.in_out == "Entrada":
                    data = {
                        'message': f"Ya tienes una marca de entrada registrada para hoy {user.user}",
                    }
                    return Response(data, status=status.HTTP_404_NOT_FOUND)

                hours_entry = datetime.now().time().strftime("%H:%M")
                late = float(hours_entry.replace(":", ".")) > user.hourIn

                CreateMark.objects.create(user=user, in_out=in_out, hours=hours_entry.replace(".", ":"), hours_extras=0, total_hours=0, in_late=late)
                photo = base64.b64encode(user.photo).decode('utf-8')
                data = {
                    'message': f"Marca de entrada registrada {user.user}",
                    'photo': photo,
                }
                return Response(data, status=status.HTTP_200_OK)

            elif in_out == "Salida":
                if last_mark and last_mark.in_out == "Salida":
                    data = {
                        'message': f"Ya tienes una marca de salida registrada para hoy {user.user}",
                    }
                    return Response(data, status=status.HTTP_404_NOT_FOUND)

                marks_in = CreateMark.objects.filter(user=user, in_out="Entrada", date=today).last()
                if not marks_in:
                    return Response(f"No tienes una marca de entrada registrada para hoy {user.user}", status=status.HTTP_404_NOT_FOUND)

                hours = datetime.now().time().strftime("%H:%M")
                final_hours = hours

                entry_hours = marks_in.hours
                exit_hours = final_hours
                total_hours = calcular_diferencia_decimal(entry_hours, exit_hours)
                total_hours_marks = 0
                for mark in all_marks_today:
                    total_hours_marks += mark.total_hours

                if total_hours_marks >= 7.60:
                    extras = total_hours
                    late = float(hours.replace(":", ".")) > user.hourOut
                    CreateMark.objects.create(user=user, in_out=in_out, hours=hours, hours_extras=extras, total_hours=0, out_late=late)
                else:
                    if total_hours == 0.01:
                        total_hours = 0.01
                            
                    if total_hours > 8:
                        extras = total_hours - 8
                        total_hours = 8
                    else:
                        extras = 0
                        late = float(hours.replace(":", ".")) > user.hourOut
                        CreateMark.objects.create(user=user, in_out=in_out, hours=hours, hours_extras=extras, total_hours=total_hours, out_late=late)
                photo = base64.b64encode(user.photo).decode('utf-8')
                data = {
                    'message': f"Marca de salida registrada {user.user}",
                    'photo': photo,
                }
                return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            response = {
                'message': 'Error al registrar la marca',
                'error': str(e)
            }
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        return Response("Solicitud no procesada", status=status.HTTP_400_BAD_REQUEST)
    
class RegisterAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    parser_classes = [MultiPartParser, FormParser]
    def post(self, request):

        name = request.data.get('name')
        last_name = request.data.get('last_name')
        user = request.data.get('user')
        departament = request.data.get('departament')
        salary = request.data.get('salary')
        extras = request.data.get('extras')
        hourIn = request.data.get('hourIn')
        hourIn = hourIn.replace(":", ".")
        hourOut = request.data.get('hourOut')
        hourOut = hourOut.replace(":", ".")
        fingerprint_data = request.data.get('fingerprint_data')
        print(fingerprint_data)
        if fingerprint_data == 'undefined':
            data = {
                'message': 'No se registró la huella dactilar',
            }
            return Response(data, status=status.HTTP_404_NOT_FOUND)
        fingerprint_data = fingerprint_data.encode("ascii")
        photo = request.FILES.get('photo')
        if photo:
            photo_binary = photo.read()
        else:
            photo_binary = None

        try:
            user = User_Worker.objects.get(user=user)
            data = {
                'message': 'El usuario ya existe',
            }
            return Response(data, status=status.HTTP_404_NOT_FOUND)
        except User_Worker.DoesNotExist:
            User_Worker.objects.create(name=name, last_name=last_name, departament=departament, user=user, salary=salary, extras=extras, hourIn=float(hourIn), hourOut=float(hourOut), photo=photo_binary, fingerPrint_template=fingerprint_data)
            data = {
                'message': 'Usuario registrado con exito',
            }
            return Response(data, status=status.HTTP_200_OK)
        


@csrf_exempt
@api_view(['POST'])
def LoginApiView(request):
    user = request.data.get('user')
    password = request.data.get('password')

    user_search = get_object_or_404(User, username=user)
    
    if not user or not password:
        return Response("Faltan datos en la solicitud", status=status.HTTP_404_NOT_FOUND)
    
    if not user_search.check_password(password):
        return Response("Contraseña o usuario incorrectos", status=status.HTTP_404_NOT_FOUND)
    
    token, created = Token.objects.get_or_create(user=user_search)

    return Response({'token': token.key, 'created': created}, status=status.HTTP_200_OK)
        
class LogoutApiView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_200_OK)
    
class RegisterAdminAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    def post(self, request, *args, **kwargs):
        name = request.data.get('name')
        last_name = request.data.get('last_name')
        user = request.data.get('user')
        password = request.data.get('password')

        if name == '' or last_name == '' or user == '' or password == '':
            return Response("Faltan datos en la solicitud", status=status.HTTP_404_NOT_FOUND)
        elif name.isspace() or last_name.isspace() or user.isspace() or password.isspace():
            return Response("Faltan datos en la solicitud", status=status.HTTP_404_NOT_FOUND)
        try:
            user_search = User.objects.get(username=user)
            if user_search:
                return Response("Usuario ya existente", status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            User.objects.create_user(first_name=name, last_name=last_name, username=user, password=password, is_superuser=True)
            return Response("Usuario registrado con exito", status=status.HTTP_200_OK)
        
class ModifyUserAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.GET.get('user')
        user_search = User_Worker.objects.get(user=user)
        hourIn = str(user_search.hourIn)
        hourOut = str(user_search.hourOut)
        hourIn = hourIn.replace(".", ":")
        hourOut = hourOut.replace(".", ":")
        if user_search.photo:
            photo_base64 = base64.b64encode(user_search.photo).decode('utf-8')
        else:
            photo_base64 = None
        data = {'name': user_search.name, 'last_name': user_search.last_name, 'user': user_search.user, 'departament': user_search.departament, 'salary': user_search.salary, 'extras': user_search.extras, 'hourIn': hourIn, 'hourOut': hourOut, 'photo': photo_base64}
        return JsonResponse(data)
    
    def post(self, request):
        name = request.data.get('name')
        last_name = request.data.get('last_name')
        user = request.data.get('user')
        departament = request.data.get('departament')
        salary = request.data.get('salary')
        extras = request.data.get('extras')
        hourIn = request.data.get('hourIn')
        hourIn = hourIn.replace(":", ".")
        hourOut = request.data.get('hourOut')
        hourOut = hourOut.replace(":", ".")
        fingerprint_data = request.data.get('fingerprint_data')
        photo = request.FILES.get('photo')

        try:
            user_search = User_Worker.objects.get(user=user)
            user_search.name = name
            user_search.last_name = last_name
            user_search.departament = departament
            user_search.salary = salary
            user_search.extras = extras
            user_search.hourIn = float(hourIn)
            user_search.hourOut = float(hourOut)

            print(fingerprint_data)
            
            # Solo actualizar la foto si se proporciona una nueva
            if photo:
                user_search.photo = photo.read()

            # Solo actualizar la huella dactilar si se proporciona una nueva
            if fingerprint_data != 'undefined':
                fingerprint_data = fingerprint_data.encode("ascii")
                user_search.fingerPrint_template = fingerprint_data


            user_search.save()
            if fingerprint_data == 'undefined':
                data = {'message': 'Usuario modificado con exito sin huella dactilar'}
            else:
                data = {'message': 'Usuario modificado con exito'}
            return Response(data, status=status.HTTP_200_OK)
        except User_Worker.DoesNotExist:
            data = {'message': 'El usuario no existe'}
            return Response(data, status=status.HTTP_404_NOT_FOUND)

class DeleteUserAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.data.get('user')
        user_instance = get_object_or_404(User_Worker, user=user)
        user_instance.delete()
        return Response("Usuario eliminado con exito", status=status.HTTP_200_OK)
    
class GetUserAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user_request = request.GET.get('user')
        if user_request:
            try:
                user_instance = User_Worker.objects.get(user=user_request)
                serializer = UserSerializer(user_instance)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except User_Worker.DoesNotExist:
                return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"error": "Falta el parámetro 'user'"}, status=status.HTTP_404_NOT_FOUND)
    

def calcular_diferencia_decimal(tiempo_inicio, tiempo_fin):
    formato_hora = "%H:%M"
    t1 = datetime.strptime(str(tiempo_inicio), formato_hora)
    t2 = datetime.strptime(str(tiempo_fin), formato_hora)
    
    # Calcula la diferencia en horas y minutos
    diferencia = t2 - t1
    arreglado = str(diferencia).replace(':', '.')
    
    # Divide la cadena por el segundo punto y toma las dos primeras partes
    partes = arreglado.split('.')
    if len(partes) > 2:
        arreglado = f"{partes[0]}.{partes[1]}"
    
    return float(arreglado)
    
        
class DeleteUserAdminVIEW(APIView):
    authentication_classes = [TokenAuthentication]
    def post(self, request, *args, **kwargs):
        user_request = request.data.get('user')
        if user_request:
            try:
                user_instance = User.objects.get(username=user_request)
                user_instance.delete()
                return Response("Usuario eliminado con exito", status=status.HTTP_200_OK)
            except User_Worker.DoesNotExist:
                return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"error": "Falta el parámetro 'user'"}, status=status.HTTP_404_NOT_FOUND)