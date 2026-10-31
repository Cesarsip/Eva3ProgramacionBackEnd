from django.conf import settings


def student_footer_context(request):
    """Expone los datos del estudiante en todas las plantillas."""
    data = getattr(settings, 'STUDENT_DATA', {})
    return {
        'student_data': data,
        'ALUMNO_NOMBRE': data.get('NOMBRE_COMPLETO', ''),
        'ALUMNO_SECCION': data.get('SECCION', ''),
        'ALUMNO_ANIO': data.get('ANIO', ''),
    }
