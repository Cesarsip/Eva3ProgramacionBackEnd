"""
Permisos basados en roles para la API REST de PetCare.

Roles del sistema:
- ADMINISTRADOR: acceso total, incluye configuración y eliminaciones.
- VETERINARIO: gestión clínica (fichas, vacunas, citas).
- RECEPCIONISTA: gestión de tutores, mascotas y agenda.
- TUTOR: consulta de sus propias mascotas, citas y recordatorios.
"""
from rest_framework import permissions

from .models import Mascota, Usuario


class EsAdministrador(permissions.BasePermission):
    """Solo el rol Administrador (o un superusuario) puede acceder."""

    message = 'Acceso denegado: se requiere rol Administrador.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_administrador
        )


class EsVeterinarioOAdministrador(permissions.BasePermission):
    """Permite el acceso a veterinarios y administradores."""

    message = 'Acceso denegado: se requiere rol Veterinario o Administrador.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_veterinario or request.user.is_administrador)
        )


class EsPersonalClinica(permissions.BasePermission):
    """Permite el acceso a administradores, veterinarios y recepcionistas."""

    message = 'Acceso denegado: se requiere ser parte del personal de la clínica.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.puede_gestionar_clinica
        )


class PuedeVerDocumentacionAPI(permissions.BasePermission):
    """
    La documentación OpenAPI solo está disponible para personal de la clínica
    con sesión iniciada. Los tutores y visitantes anónimos reciben 403.
    """

    message = 'Acceso denegado: la documentación de la API es solo para personal de la clínica.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, 'puede_gestionar_clinica', False)
        )


class LecturaAutenticadaEscrituraPersonal(permissions.BasePermission):
    """Cualquier usuario autenticado puede leer; solo el personal puede escribir."""

    message = 'Acceso denegado: solo el personal de la clínica puede modificar este recurso.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.puede_gestionar_clinica


class LecturaAutenticadaEscrituraVeterinario(permissions.BasePermission):
    """Lectura para autenticados; escritura solo veterinarios/administradores."""

    message = 'Acceso denegado: solo un veterinario o administrador puede modificar este recurso.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_veterinario or request.user.is_administrador


class LecturaAutenticadaEscrituraAdministrador(permissions.BasePermission):
    """Lectura para autenticados; escritura solo administradores."""

    message = 'Acceso denegado: solo un administrador puede modificar este recurso.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_administrador


class PermisoCitas(permissions.BasePermission):
    """
    Permiso para el recurso de citas.

    Todo usuario autenticado puede leer. El personal de la clínica gestiona
    cualquier cita; un tutor solo puede solicitar una cita nueva o cancelar
    una cita existente (el permiso de objeto limita ambas acciones a sus
    propias mascotas).
    """

    message = 'Acceso denegado: no puedes modificar esta cita.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if user.puede_gestionar_clinica:
            return True
        return getattr(view, 'action', None) in ('create', 'cancelar')


class EsTutorPropietarioOStaff(permissions.BasePermission):
    """
    Permiso a nivel de objeto.

    El personal de la clínica puede acceder a cualquier registro; un tutor
    solo puede acceder a las mascotas, citas, fichas y recordatorios que le
    pertenecen.
    """

    message = 'Acceso denegado: este registro pertenece a otro tutor.'

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.puede_gestionar_clinica:
            return True

        if isinstance(obj, Mascota):
            return obj.tutor.usuario_id == user.id
        if isinstance(obj, Usuario):
            return obj.id == user.id

        mascota = getattr(obj, 'mascota', None)
        if mascota is None and hasattr(obj, 'cita'):
            mascota = getattr(obj.cita, 'mascota', None)
        if mascota is not None:
            return mascota.tutor.usuario_id == user.id
        return False
