"""Vistas de la API REST de PetCare (DRF + JWT)."""
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters as drf_filters
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .filters import (
    CitaFilter,
    FichaClinicaFilter,
    MascotaFilter,
    ProfesionalFilter,
    RecordatorioFilter,
    TutorFilter,
    VacunaFilter,
)
from .models import (
    Cita,
    FichaClinica,
    HorarioAtencion,
    Mascota,
    Profesional,
    Recordatorio,
    Tutor,
    Usuario,
    Vacuna,
)
from .permissions import (
    EsAdministrador,
    EsPersonalClinica,
    EsTutorPropietarioOStaff,
    LecturaAutenticadaEscrituraAdministrador,
    LecturaAutenticadaEscrituraPersonal,
    LecturaAutenticadaEscrituraVeterinario,
    PermisoCitas,
)
from .serializers import (
    CitaSerializer,
    CustomTokenObtainPairSerializer,
    FichaClinicaSerializer,
    HorarioAtencionSerializer,
    MascotaSerializer,
    ProfesionalSerializer,
    RecordatorioSerializer,
    RegistroTutorSerializer,
    TutorSerializer,
    UsuarioSerializer,
    VacunaSerializer,
)


# =====================================================================
# DOCUMENTACIÓN OPENAPI
# =====================================================================
class PetCareSpectacularAPIView(SpectacularAPIView):
    """
    Esquema OpenAPI con un nombre de archivo seguro para el navegador.

    drf-spectacular usa el título del esquema (``PetCare | Gestión
    Veterinaria``) como ``Content-Disposition``. El acento produce un byte
    no ASCII en la cabecera HTTP y algunos navegadores/proxies dejan la
    petición pendiente. Se fuerza un nombre ASCII para que Swagger UI cargue
    el esquema sin problemas.
    """

    def _get_filename(self, request, version):
        formato = self.perform_content_negotiation(request, force=True)[0].format
        return f'petcare-schema.{formato}'


# =====================================================================
# AUTENTICACIÓN
# =====================================================================
@extend_schema(tags=['Autenticación'])
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(tags=['Autenticación'])
class DocumentedTokenRefreshView(TokenRefreshView):
    pass


class RegistroAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Autenticación'],
        request=RegistroTutorSerializer,
        responses={201: UsuarioSerializer},
        description='Registra un tutor y devuelve sus tokens JWT.',
    )
    def post(self, request):
        serializer = RegistroTutorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tutor = serializer.save()
        refresh = RefreshToken.for_user(tutor.usuario)
        return Response(
            {
                'usuario': UsuarioSerializer(tutor.usuario).data,
                'tutor': TutorSerializer(tutor).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class PerfilAPIView(APIView):
    @extend_schema(tags=['Autenticación'], responses=UsuarioSerializer)
    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


# =====================================================================
# TUTORES
# =====================================================================
class TutorViewSet(viewsets.ModelViewSet):
    serializer_class = TutorSerializer
    permission_classes = [permissions.IsAuthenticated, LecturaAutenticadaEscrituraPersonal]
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = TutorFilter
    search_fields = ['nombres', 'apellidos', 'rut', 'email', 'telefono']
    ordering_fields = ['apellidos', 'nombres', 'fecha_registro']

    def get_queryset(self):
        queryset = Tutor.objects.select_related('usuario')
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if getattr(user, 'puede_gestionar_clinica', False):
            return queryset
        return queryset.filter(usuario=user)


# =====================================================================
# MASCOTAS
# =====================================================================
class MascotaViewSet(viewsets.ModelViewSet):
    serializer_class = MascotaSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        LecturaAutenticadaEscrituraPersonal,
        EsTutorPropietarioOStaff,
    ]
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = MascotaFilter
    search_fields = ['nombre', 'raza', 'microchip', 'tutor__nombres', 'tutor__apellidos']
    ordering_fields = ['nombre', 'fecha_registro', 'especie']

    def get_queryset(self):
        queryset = Mascota.objects.select_related('tutor')
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if getattr(user, 'puede_gestionar_clinica', False):
            return queryset
        return queryset.filter(tutor__usuario=user)

    @extend_schema(
        tags=['Mascotas'],
        description='Devuelve la ficha completa: citas, fichas clínicas, vacunas y recordatorios.',
    )
    @action(detail=True, methods=['get'])
    def historial(self, request, pk=None):
        mascota = self.get_object()
        return Response({
            'mascota': MascotaSerializer(mascota).data,
            'citas': CitaSerializer(mascota.citas.select_related('profesional'), many=True).data,
            'fichas': FichaClinicaSerializer(
                mascota.fichas.select_related('profesional').prefetch_related('recetas', 'examenes'),
                many=True,
            ).data,
            'vacunas': VacunaSerializer(
                mascota.vacunas.select_related('profesional'), many=True
            ).data,
            'recordatorios': RecordatorioSerializer(mascota.recordatorios.all(), many=True).data,
        })


# =====================================================================
# PROFESIONALES Y HORARIOS
# =====================================================================
class ProfesionalViewSet(viewsets.ModelViewSet):
    queryset = Profesional.objects.select_related('usuario')
    serializer_class = ProfesionalSerializer
    permission_classes = [permissions.IsAuthenticated, LecturaAutenticadaEscrituraAdministrador]
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = ProfesionalFilter
    search_fields = ['nombres', 'apellidos', 'especialidad', 'registro_profesional', 'email']
    ordering_fields = ['apellidos', 'nombres', 'especialidad']


class HorarioAtencionViewSet(viewsets.ModelViewSet):
    queryset = HorarioAtencion.objects.select_related('profesional')
    serializer_class = HorarioAtencionSerializer
    permission_classes = [permissions.IsAuthenticated, LecturaAutenticadaEscrituraAdministrador]
    filterset_fields = ['profesional', 'dia_semana', 'activo']
    ordering_fields = ['profesional', 'dia_semana', 'hora_inicio']


# =====================================================================
# CITAS
# =====================================================================
class CitaViewSet(viewsets.ModelViewSet):
    serializer_class = CitaSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        PermisoCitas,
        EsTutorPropietarioOStaff,
    ]
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = CitaFilter
    search_fields = ['mascota__nombre', 'mascota__tutor__nombres', 'mascota__tutor__apellidos', 'motivo']
    ordering_fields = ['fecha', 'hora', 'estado']

    def get_queryset(self):
        queryset = Cita.objects.select_related('mascota', 'mascota__tutor', 'profesional')
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if getattr(user, 'puede_gestionar_clinica', False):
            return queryset
        return queryset.filter(mascota__tutor__usuario=user)

    @extend_schema(tags=['Citas'], request=None, responses=CitaSerializer)
    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        if not request.user.puede_gestionar_clinica:
            return Response(
                {'detail': 'Solo el personal de la clínica puede confirmar citas.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        cita = self.get_object()
        try:
            cita.confirmar()
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CitaSerializer(cita).data)

    @extend_schema(tags=['Citas'], request=None, responses=CitaSerializer)
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        cita = self.get_object()
        try:
            cita.cancelar()
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CitaSerializer(cita).data)

    @extend_schema(tags=['Citas'], request=None, responses=CitaSerializer)
    @action(detail=True, methods=['post'])
    def atender(self, request, pk=None):
        if not (request.user.is_veterinario or request.user.is_administrador):
            return Response(
                {'detail': 'Solo un veterinario o administrador puede atender citas.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        cita = self.get_object()
        try:
            cita.atender()
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CitaSerializer(cita).data)

    @extend_schema(
        tags=['Citas'],
        parameters=[
            OpenApiParameter('profesional', int, required=True, description='ID del profesional'),
            OpenApiParameter('fecha', str, required=True, description='Fecha AAAA-MM-DD'),
        ],
        description='Calcula los bloques de 30 minutos disponibles para un profesional.',
    )
    @action(detail=False, methods=['get'])
    def disponibilidad(self, request):
        profesional_id = request.query_params.get('profesional')
        fecha_texto = request.query_params.get('fecha')
        if not profesional_id or not fecha_texto:
            return Response(
                {'detail': 'Debes indicar los parámetros profesional y fecha.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            fecha = date.fromisoformat(fecha_texto)
        except ValueError:
            return Response(
                {'detail': 'La fecha debe tener el formato AAAA-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            profesional = Profesional.objects.get(pk=profesional_id, activo=True)
        except (Profesional.DoesNotExist, ValueError):
            return Response(
                {'detail': 'Profesional no encontrado o inactivo.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        bloques = profesional.horarios.filter(
            dia_semana=fecha.weekday(), activo=True
        ).order_by('hora_inicio')
        if not bloques.exists():
            return Response({
                'profesional': profesional.id,
                'fecha': fecha,
                'horarios': [],
                'mensaje': 'El profesional no tiene horario configurado para ese día.',
            })

        citas = list(Cita.objects.filter(
            profesional=profesional,
            fecha=fecha,
            estado__in=[Cita.EstadoChoices.PROGRAMADA, Cita.EstadoChoices.CONFIRMADA],
        ))
        ahora = timezone.localtime()
        resultado = []

        for bloque in bloques:
            inicio = datetime.combine(fecha, bloque.hora_inicio)
            fin = datetime.combine(fecha, bloque.hora_fin)
            while inicio < fin:
                hora = inicio.time()
                fin_bloque = inicio + timedelta(minutes=30)
                ocupado = False
                for cita in citas:
                    inicio_cita = datetime.combine(fecha, cita.hora)
                    fin_cita = inicio_cita + timedelta(minutes=30)
                    if inicio_cita < fin_bloque and fin_cita > inicio:
                        ocupado = True
                        break
                pasado = fecha < ahora.date() or (
                    fecha == ahora.date() and hora <= ahora.time()
                )
                resultado.append({
                    'hora': hora.strftime('%H:%M'),
                    'disponible': not ocupado and not pasado,
                })
                inicio = fin_bloque

        return Response({
            'profesional': profesional.id,
            'profesional_nombre': profesional.nombre_completo,
            'fecha': fecha,
            'horarios': resultado,
        })


# =====================================================================
# FICHAS CLÍNICAS
# =====================================================================
class FichaClinicaViewSet(viewsets.ModelViewSet):
    serializer_class = FichaClinicaSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        LecturaAutenticadaEscrituraVeterinario,
        EsTutorPropietarioOStaff,
    ]
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = FichaClinicaFilter
    search_fields = ['mascota__nombre', 'diagnostico', 'tratamiento', 'motivo_consulta']
    ordering_fields = ['fecha', 'proxima_revision']

    def get_queryset(self):
        queryset = FichaClinica.objects.select_related(
            'mascota', 'mascota__tutor', 'profesional'
        ).prefetch_related('recetas', 'examenes')
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if getattr(user, 'puede_gestionar_clinica', False):
            return queryset
        return queryset.filter(mascota__tutor__usuario=user)


# =====================================================================
# VACUNAS
# =====================================================================
class VacunaViewSet(viewsets.ModelViewSet):
    serializer_class = VacunaSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        LecturaAutenticadaEscrituraVeterinario,
        EsTutorPropietarioOStaff,
    ]
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = VacunaFilter
    search_fields = ['nombre', 'mascota__nombre', 'lote']
    ordering_fields = ['fecha_aplicacion', 'proxima_dosis', 'nombre']

    def get_queryset(self):
        queryset = Vacuna.objects.select_related('mascota', 'mascota__tutor', 'profesional')
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if getattr(user, 'puede_gestionar_clinica', False):
            return queryset
        return queryset.filter(mascota__tutor__usuario=user)


# =====================================================================
# RECORDATORIOS
# =====================================================================
class RecordatorioViewSet(viewsets.ModelViewSet):
    serializer_class = RecordatorioSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        LecturaAutenticadaEscrituraPersonal,
        EsTutorPropietarioOStaff,
    ]
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = RecordatorioFilter
    search_fields = ['titulo', 'descripcion', 'mascota__nombre']
    ordering_fields = ['fecha_programada', 'estado', 'tipo']

    def get_queryset(self):
        queryset = Recordatorio.objects.select_related('mascota', 'mascota__tutor')
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if getattr(user, 'puede_gestionar_clinica', False):
            return queryset
        return queryset.filter(mascota__tutor__usuario=user)

    @extend_schema(tags=['Recordatorios'], request=None, responses=RecordatorioSerializer)
    @action(detail=True, methods=['post'])
    def enviar(self, request, pk=None):
        if not request.user.puede_gestionar_clinica:
            return Response(
                {'detail': 'Solo el personal de la clínica puede marcar envíos.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        recordatorio = self.get_object()
        recordatorio.marcar_enviado()
        return Response(RecordatorioSerializer(recordatorio).data)

    @extend_schema(tags=['Recordatorios'], request=None, responses=RecordatorioSerializer)
    @action(detail=True, methods=['post'])
    def completar(self, request, pk=None):
        if not request.user.puede_gestionar_clinica:
            return Response(
                {'detail': 'Solo el personal de la clínica puede completar recordatorios.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        recordatorio = self.get_object()
        recordatorio.marcar_completado()
        return Response(RecordatorioSerializer(recordatorio).data)


# =====================================================================
# USUARIOS (SOLO ADMINISTRADOR)
# =====================================================================
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all().order_by('username')
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated, EsAdministrador]
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    search_fields = ['username', 'first_name', 'last_name', 'email', 'rut']
    ordering_fields = ['username', 'date_joined', 'rol']
