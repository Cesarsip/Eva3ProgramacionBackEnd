"""Filtros de búsqueda para los endpoints de la API de PetCare."""
import django_filters

from .models import Cita, FichaClinica, Mascota, Profesional, Recordatorio, Tutor, Vacuna


class TutorFilter(django_filters.FilterSet):
    activo = django_filters.BooleanFilter(field_name='activo')
    comuna = django_filters.CharFilter(field_name='direccion', lookup_expr='icontains')

    class Meta:
        model = Tutor
        fields = ['activo']


class MascotaFilter(django_filters.FilterSet):
    tutor = django_filters.NumberFilter(field_name='tutor_id')
    especie = django_filters.CharFilter(field_name='especie')
    sexo = django_filters.CharFilter(field_name='sexo')
    activo = django_filters.BooleanFilter(field_name='activo')
    edad_minima = django_filters.NumberFilter(method='filtrar_edad_minima')

    class Meta:
        model = Mascota
        fields = ['tutor', 'especie', 'sexo', 'activo']

    def filtrar_edad_minima(self, queryset, name, value):
        """Filtra mascotas con al menos ``value`` años de edad."""
        from django.utils import timezone

        limite = timezone.localdate().replace(year=timezone.localdate().year - int(value))
        return queryset.filter(fecha_nacimiento__lte=limite)


class ProfesionalFilter(django_filters.FilterSet):
    activo = django_filters.BooleanFilter(field_name='activo')
    especialidad = django_filters.CharFilter(field_name='especialidad', lookup_expr='icontains')

    class Meta:
        model = Profesional
        fields = ['activo', 'especialidad']


class CitaFilter(django_filters.FilterSet):
    estado = django_filters.CharFilter(field_name='estado')
    profesional = django_filters.NumberFilter(field_name='profesional_id')
    mascota = django_filters.NumberFilter(field_name='mascota_id')
    tutor = django_filters.NumberFilter(field_name='mascota__tutor_id')
    fecha = django_filters.DateFilter(field_name='fecha')
    desde = django_filters.DateFilter(field_name='fecha', lookup_expr='gte')
    hasta = django_filters.DateFilter(field_name='fecha', lookup_expr='lte')

    class Meta:
        model = Cita
        fields = ['estado', 'profesional', 'mascota', 'tutor', 'fecha', 'desde', 'hasta']


class FichaClinicaFilter(django_filters.FilterSet):
    mascota = django_filters.NumberFilter(field_name='mascota_id')
    profesional = django_filters.NumberFilter(field_name='profesional_id')
    desde = django_filters.DateFilter(field_name='fecha', lookup_expr='date__gte')
    hasta = django_filters.DateFilter(field_name='fecha', lookup_expr='date__lte')

    class Meta:
        model = FichaClinica
        fields = ['mascota', 'profesional', 'desde', 'hasta']


class VacunaFilter(django_filters.FilterSet):
    mascota = django_filters.NumberFilter(field_name='mascota_id')
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    proxima_desde = django_filters.DateFilter(field_name='proxima_dosis', lookup_expr='gte')
    proxima_hasta = django_filters.DateFilter(field_name='proxima_dosis', lookup_expr='lte')

    class Meta:
        model = Vacuna
        fields = ['mascota', 'nombre', 'proxima_desde', 'proxima_hasta']


class RecordatorioFilter(django_filters.FilterSet):
    mascota = django_filters.NumberFilter(field_name='mascota_id')
    estado = django_filters.CharFilter(field_name='estado')
    tipo = django_filters.CharFilter(field_name='tipo')
    desde = django_filters.DateFilter(field_name='fecha_programada', lookup_expr='gte')
    hasta = django_filters.DateFilter(field_name='fecha_programada', lookup_expr='lte')

    class Meta:
        model = Recordatorio
        fields = ['mascota', 'estado', 'tipo', 'desde', 'hasta']
