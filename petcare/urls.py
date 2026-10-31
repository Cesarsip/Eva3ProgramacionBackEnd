"""Rutas web y de la API del dominio PetCare."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api_views, views

router = DefaultRouter()
router.register('tutores', api_views.TutorViewSet, basename='api-tutores')
router.register('mascotas', api_views.MascotaViewSet, basename='api-mascotas')
router.register('profesionales', api_views.ProfesionalViewSet, basename='api-profesionales')
router.register('horarios', api_views.HorarioAtencionViewSet, basename='api-horarios')
router.register('citas', api_views.CitaViewSet, basename='api-citas')
router.register('fichas', api_views.FichaClinicaViewSet, basename='api-fichas')
router.register('vacunas', api_views.VacunaViewSet, basename='api-vacunas')
router.register('recordatorios', api_views.RecordatorioViewSet, basename='api-recordatorios')
router.register('usuarios', api_views.UsuarioViewSet, basename='api-usuarios')

urlpatterns = [
    # Páginas públicas
    path('', views.home, name='home'),
    path('login/', views.PetCareLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('health/', views.health_view, name='health'),

    # Panel
    path('dashboard/', views.dashboard, name='dashboard'),

    # Tutores
    path('tutores/', views.tutores_lista, name='tutores_lista'),
    path('tutores/nuevo/', views.tutor_crear, name='tutor_crear'),
    path('tutores/<int:pk>/editar/', views.tutor_editar, name='tutor_editar'),
    path('tutores/<int:pk>/eliminar/', views.tutor_eliminar, name='tutor_eliminar'),

    # Mascotas
    path('mascotas/', views.mascotas_lista, name='mascotas_lista'),
    path('mascotas/nueva/', views.mascota_crear, name='mascota_crear'),
    path('mascotas/<int:pk>/', views.mascota_detalle, name='mascota_detalle'),
    path('mascotas/<int:pk>/editar/', views.mascota_editar, name='mascota_editar'),
    path('mascotas/<int:pk>/eliminar/', views.mascota_eliminar, name='mascota_eliminar'),

    # Profesionales y horarios
    path('profesionales/', views.profesionales_lista, name='profesionales_lista'),
    path('profesionales/nuevo/', views.profesional_crear, name='profesional_crear'),
    path('profesionales/<int:pk>/', views.profesional_detalle, name='profesional_detalle'),
    path('profesionales/<int:pk>/editar/', views.profesional_editar, name='profesional_editar'),
    path('profesionales/<int:pk>/eliminar/', views.profesional_eliminar, name='profesional_eliminar'),
    path('profesionales/<int:profesional_pk>/horarios/nuevo/', views.horario_crear, name='horario_crear'),
    path('horarios/<int:pk>/editar/', views.horario_editar, name='horario_editar'),
    path('horarios/<int:pk>/eliminar/', views.horario_eliminar, name='horario_eliminar'),

    # Citas
    path('citas/', views.citas_lista, name='citas_lista'),
    path('citas/calendario/', views.citas_calendario, name='citas_calendario'),
    path('citas/nueva/', views.cita_crear, name='cita_crear'),
    path('citas/<int:pk>/editar/', views.cita_editar, name='cita_editar'),
    path('citas/<int:pk>/cancelar/', views.cita_cancelar, name='cita_cancelar'),
    path('citas/<int:pk>/confirmar/', views.cita_confirmar, name='cita_confirmar'),
    path('citas/<int:pk>/atender/', views.cita_atender, name='cita_atender'),
    path('citas/<int:pk>/no-asistio/', views.cita_no_asistio, name='cita_no_asistio'),
    path('citas/<int:pk>/eliminar/', views.cita_eliminar, name='cita_eliminar'),

    # Fichas clínicas
    path('fichas/', views.fichas_lista, name='fichas_lista'),
    path('fichas/nueva/', views.ficha_crear, name='ficha_crear'),
    path('fichas/<int:pk>/', views.ficha_detalle, name='ficha_detalle'),
    path('fichas/<int:pk>/editar/', views.ficha_editar, name='ficha_editar'),
    path('fichas/<int:pk>/eliminar/', views.ficha_eliminar, name='ficha_eliminar'),

    # Vacunas
    path('vacunas/', views.vacunas_lista, name='vacunas_lista'),
    path('vacunas/nueva/', views.vacuna_crear, name='vacuna_crear'),
    path('vacunas/<int:pk>/editar/', views.vacuna_editar, name='vacuna_editar'),
    path('vacunas/<int:pk>/eliminar/', views.vacuna_eliminar, name='vacuna_eliminar'),

    # Recordatorios
    path('recordatorios/', views.recordatorios_lista, name='recordatorios_lista'),
    path('recordatorios/nuevo/', views.recordatorio_crear, name='recordatorio_crear'),
    path('recordatorios/<int:pk>/editar/', views.recordatorio_editar, name='recordatorio_editar'),
    path('recordatorios/<int:pk>/enviar/', views.recordatorio_enviar, name='recordatorio_enviar'),
    path('recordatorios/<int:pk>/completar/', views.recordatorio_completar, name='recordatorio_completar'),
    path('recordatorios/<int:pk>/eliminar/', views.recordatorio_eliminar, name='recordatorio_eliminar'),

    # Autenticación JWT
    path('api/auth/token/', api_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', api_views.DocumentedTokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/registro/', api_views.RegistroAPIView.as_view(), name='api_registro'),
    path('api/auth/me/', api_views.PerfilAPIView.as_view(), name='api_perfil'),

    # API REST
    path('api/', include(router.urls)),
]
