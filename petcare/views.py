"""Vistas HTML de PetCare (Django templates + Bootstrap)."""
import calendar
from datetime import date, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.forms import inlineformset_factory
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import Resolver404, resolve
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CitaForm,
    ExamenForm,
    FichaClinicaForm,
    HorarioAtencionForm,
    LoginForm,
    MascotaForm,
    ProfesionalForm,
    RecetaForm,
    RecordatorioForm,
    RegistroTutorForm,
    TutorForm,
    VacunaForm,
)
from .models import (
    Cita,
    Examen,
    FichaClinica,
    HorarioAtencion,
    Mascota,
    Profesional,
    Receta,
    Recordatorio,
    Tutor,
    Usuario,
    Vacuna,
)

ROLES_PERSONAL = (
    Usuario.RolChoices.ADMINISTRADOR,
    Usuario.RolChoices.VETERINARIO,
    Usuario.RolChoices.RECEPCIONISTA,
)
ROLES_VET_ADMIN = (
    Usuario.RolChoices.ADMINISTRADOR,
    Usuario.RolChoices.VETERINARIO,
)
ROLES_ADMIN = (Usuario.RolChoices.ADMINISTRADOR,)

MESES_ES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]


# =====================================================================
# UTILIDADES DE ACCESO Y CONSULTA
# =====================================================================
def rol_requerido(*roles):
    """Restringe una vista HTML a los roles indicados y devuelve 403 si no aplica."""

    def decorador(vista):
        @login_required
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if request.user.is_superuser or request.user.rol in roles:
                return vista(request, *args, **kwargs)
            return render(request, '403.html', status=403)

        return envoltura

    return decorador


def paginar(request, queryset, por_pagina=10):
    from django.core.paginator import Paginator

    pagina = Paginator(queryset, por_pagina).get_page(request.GET.get('page'))
    parametros = request.GET.copy()
    parametros.pop('page', None)
    # Permite conservar los filtros activos en los enlaces de paginación.
    pagina.querystring = parametros.urlencode()
    return pagina


def mascotas_visibles(usuario):
    queryset = Mascota.objects.select_related('tutor')
    if usuario.puede_gestionar_clinica:
        return queryset
    return queryset.filter(tutor__usuario=usuario)


def citas_visibles(usuario):
    queryset = Cita.objects.select_related('mascota', 'mascota__tutor', 'profesional')
    if usuario.puede_gestionar_clinica:
        return queryset
    return queryset.filter(mascota__tutor__usuario=usuario)


def fichas_visibles(usuario):
    queryset = FichaClinica.objects.select_related(
        'mascota', 'mascota__tutor', 'profesional'
    ).prefetch_related('recetas', 'examenes')
    if usuario.puede_gestionar_clinica:
        return queryset
    return queryset.filter(mascota__tutor__usuario=usuario)


def vacunas_visibles(usuario):
    queryset = Vacuna.objects.select_related('mascota', 'mascota__tutor', 'profesional')
    if usuario.puede_gestionar_clinica:
        return queryset
    return queryset.filter(mascota__tutor__usuario=usuario)


def recordatorios_visibles(usuario):
    queryset = Recordatorio.objects.select_related('mascota', 'mascota__tutor')
    if usuario.puede_gestionar_clinica:
        return queryset
    return queryset.filter(mascota__tutor__usuario=usuario)


# =====================================================================
# PÁGINAS PÚBLICAS Y AUTENTICACIÓN
# =====================================================================
def _contexto_portada():
    """Datos de la portada pública (totales visibles en el hero)."""
    return {
        'total_profesionales': Profesional.objects.filter(activo=True).count(),
        'total_mascotas': Mascota.objects.filter(activo=True).count(),
        'total_tutores': Tutor.objects.filter(activo=True).count(),
    }


def home(request):
    """
    Portada pública de PetCare.

    Se muestra igual para un visitante y para una sesión iniciada (mismo
    comportamiento que ``index_view`` de CarritoShop / EVA 2): nunca monta el
    panel de gestión. Quien tiene sesión entra al dashboard desde el botón
    “Ir al panel” o después de iniciar sesión.
    """
    contexto = _contexto_portada()
    contexto['portada_publica'] = True
    return render(request, 'home.html', contexto)


def redirect_to_home(request):
    """
    Fallback de rutas web no reconocidas.

    Replica el comportamiento de EVA 2 (CarritoShop): en lugar de mostrar la
    pantalla 404 por defecto, cualquier URL web desconocida redirige con 302
    a la portada (``redirect('home')``, igual que ``redirect('index')`` allá).
    Así una URL inventada como ``/poto`` termina siempre en la portada pública
    y nunca sirve el panel de gestión.

    Las rutas /admin/, /api/, /static/ y /media/ quedan excluidas desde
    ``petcare_project/urls.py`` para no interferir con Django Admin, la API
    ni los archivos estáticos.

    Antes de redirigir se comprueba si la ruta existe al agregarle la barra
    final (por ejemplo ``/login`` -> ``/login/``), para conservar el
    comportamiento normal de Django (APPEND_SLASH) en las rutas válidas.
    """
    destino = f'{request.path}/'
    try:
        coincidencia = resolve(destino)
    except Resolver404:
        return redirect('home')
    if coincidencia.url_name == 'catch_all':
        return redirect('home')
    return redirect(destino)


class PetCareLoginView(LoginView):
    template_name = 'auth/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, 'Bienvenido(a) de vuelta a PetCare.')
        return super().form_valid(form)


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'Tu sesión se cerró correctamente.')
    return redirect('home')


def registro_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegistroTutorForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(
            request,
            'Tu cuenta fue creada. Ya puedes solicitar horas para tus mascotas.',
        )
        return redirect('dashboard')
    return render(request, 'auth/registro.html', {'form': form})


# =====================================================================
# DASHBOARD
# =====================================================================
@login_required
def dashboard(request):
    usuario = request.user
    hoy = timezone.localdate()
    es_personal = usuario.puede_gestionar_clinica

    if es_personal:
        contexto = {
            'total_tutores': Tutor.objects.filter(activo=True).count(),
            'total_mascotas': Mascota.objects.filter(activo=True).count(),
            'citas_hoy': Cita.objects.filter(fecha=hoy).exclude(
                estado=Cita.EstadoChoices.CANCELADA
            ).count(),
            'citas_pendientes': Cita.objects.filter(
                estado__in=[Cita.EstadoChoices.PROGRAMADA, Cita.EstadoChoices.CONFIRMADA]
            ).count(),
            'recordatorios_pendientes': Recordatorio.objects.filter(
                estado=Recordatorio.EstadoChoices.PENDIENTE
            ).count(),
            'proximas_citas': Cita.objects.filter(
                fecha__gte=hoy,
                estado__in=[Cita.EstadoChoices.PROGRAMADA, Cita.EstadoChoices.CONFIRMADA],
            ).select_related('mascota', 'mascota__tutor', 'profesional')[:8],
            'recordatorios': Recordatorio.objects.filter(
                estado=Recordatorio.EstadoChoices.PENDIENTE,
                fecha_programada__lte=hoy + timedelta(days=14),
            ).select_related('mascota')[:8],
            'fichas_recientes': FichaClinica.objects.select_related(
                'mascota', 'profesional'
            )[:5],
        }
    else:
        contexto = {
            'total_mascotas': mascotas_visibles(usuario).filter(activo=True).count(),
            'citas_hoy': citas_visibles(usuario).filter(fecha=hoy).exclude(
                estado=Cita.EstadoChoices.CANCELADA
            ).count(),
            'citas_pendientes': citas_visibles(usuario).filter(
                estado__in=[Cita.EstadoChoices.PROGRAMADA, Cita.EstadoChoices.CONFIRMADA]
            ).count(),
            'recordatorios_pendientes': recordatorios_visibles(usuario).filter(
                estado=Recordatorio.EstadoChoices.PENDIENTE
            ).count(),
            'proximas_citas': citas_visibles(usuario).filter(
                fecha__gte=hoy,
                estado__in=[Cita.EstadoChoices.PROGRAMADA, Cita.EstadoChoices.CONFIRMADA],
            )[:8],
            'recordatorios': recordatorios_visibles(usuario).filter(
                estado=Recordatorio.EstadoChoices.PENDIENTE,
                fecha_programada__lte=hoy + timedelta(days=30),
            )[:8],
        }

    contexto['es_personal'] = es_personal
    return render(request, 'dashboard.html', contexto)


# =====================================================================
# TUTORES
# =====================================================================
@rol_requerido(*ROLES_PERSONAL)
def tutores_lista(request):
    q = request.GET.get('q', '').strip()
    activo = request.GET.get('activo', '')
    queryset = Tutor.objects.annotate(
        num_mascotas=Count('mascotas', filter=Q(mascotas__activo=True))
    ).order_by('apellidos', 'nombres')
    if q:
        queryset = queryset.filter(
            Q(nombres__icontains=q)
            | Q(apellidos__icontains=q)
            | Q(rut__icontains=q)
            | Q(email__icontains=q)
            | Q(telefono__icontains=q)
        )
    if activo in ('1', '0'):
        queryset = queryset.filter(activo=(activo == '1'))
    return render(request, 'tutores/lista.html', {
        'page_obj': paginar(request, queryset, 10),
        'q': q,
        'activo': activo,
    })


@rol_requerido(*ROLES_PERSONAL)
def tutor_crear(request):
    form = TutorForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        tutor = form.save()
        messages.success(request, f'Tutor {tutor.nombre_completo} registrado correctamente.')
        return redirect('tutores_lista')
    return render(request, 'tutores/form.html', {'form': form, 'titulo': 'Nuevo tutor'})


@rol_requerido(*ROLES_PERSONAL)
def tutor_editar(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)
    form = TutorForm(request.POST or None, instance=tutor)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Los datos del tutor fueron actualizados.')
        return redirect('tutores_lista')
    return render(request, 'tutores/form.html', {
        'form': form,
        'titulo': f'Editar tutor: {tutor.nombre_completo}',
        'objeto': tutor,
    })


@rol_requerido(*ROLES_ADMIN)
@require_POST
def tutor_eliminar(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)
    nombre = tutor.nombre_completo
    tutor.delete()
    messages.success(request, f'El tutor {nombre} fue eliminado.')
    return redirect('tutores_lista')


# =====================================================================
# MASCOTAS
# =====================================================================
@login_required
def mascotas_lista(request):
    q = request.GET.get('q', '').strip()
    especie = request.GET.get('especie', '')
    queryset = mascotas_visibles(request.user)
    if q:
        queryset = queryset.filter(
            Q(nombre__icontains=q)
            | Q(raza__icontains=q)
            | Q(microchip__icontains=q)
            | Q(tutor__nombres__icontains=q)
            | Q(tutor__apellidos__icontains=q)
        )
    if especie:
        queryset = queryset.filter(especie=especie)
    return render(request, 'mascotas/lista.html', {
        'page_obj': paginar(request, queryset, 10),
        'q': q,
        'especie': especie,
        'especies': Mascota.EspecieChoices.choices,
    })


@login_required
def mascota_detalle(request, pk):
    mascota = get_object_or_404(mascotas_visibles(request.user), pk=pk)
    return render(request, 'mascotas/detalle.html', {
        'mascota': mascota,
        'citas': mascota.citas.select_related('profesional').order_by('-fecha', '-hora')[:10],
        'fichas': mascota.fichas.select_related('profesional').prefetch_related('recetas', 'examenes')[:10],
        'vacunas': mascota.vacunas.select_related('profesional')[:10],
        'recordatorios': mascota.recordatorios.all()[:10],
    })


@rol_requerido(*ROLES_PERSONAL)
def mascota_crear(request):
    form = MascotaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        mascota = form.save()
        messages.success(request, f'La mascota {mascota.nombre} fue registrada.')
        return redirect('mascota_detalle', pk=mascota.pk)
    return render(request, 'mascotas/form.html', {'form': form, 'titulo': 'Nueva mascota'})


@rol_requerido(*ROLES_PERSONAL)
def mascota_editar(request, pk):
    mascota = get_object_or_404(Mascota, pk=pk)
    form = MascotaForm(request.POST or None, instance=mascota)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'La ficha de la mascota fue actualizada.')
        return redirect('mascota_detalle', pk=mascota.pk)
    return render(request, 'mascotas/form.html', {
        'form': form,
        'titulo': f'Editar mascota: {mascota.nombre}',
        'objeto': mascota,
    })


@rol_requerido(*ROLES_ADMIN)
@require_POST
def mascota_eliminar(request, pk):
    mascota = get_object_or_404(Mascota, pk=pk)
    nombre = mascota.nombre
    mascota.delete()
    messages.success(request, f'La mascota {nombre} fue eliminada.')
    return redirect('mascotas_lista')


# =====================================================================
# PROFESIONALES Y HORARIOS
# =====================================================================
@login_required
def profesionales_lista(request):
    q = request.GET.get('q', '').strip()
    queryset = Profesional.objects.annotate(cantidad_horarios=Count('horarios')).order_by(
        'apellidos', 'nombres'
    )
    if q:
        queryset = queryset.filter(
            Q(nombres__icontains=q)
            | Q(apellidos__icontains=q)
            | Q(especialidad__icontains=q)
            | Q(registro_profesional__icontains=q)
        )
    return render(request, 'profesionales/lista.html', {
        'page_obj': paginar(request, queryset, 10),
        'q': q,
    })


@login_required
def profesional_detalle(request, pk):
    profesional = get_object_or_404(Profesional, pk=pk)
    return render(request, 'profesionales/detalle.html', {
        'profesional': profesional,
        'horarios': profesional.horarios.order_by('dia_semana', 'hora_inicio'),
        'citas': profesional.citas.select_related('mascota', 'mascota__tutor').order_by('-fecha')[:10],
    })


@rol_requerido(*ROLES_ADMIN)
def profesional_crear(request):
    form = ProfesionalForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        profesional = form.save()
        messages.success(request, f'Profesional {profesional.nombre_completo} registrado.')
        return redirect('profesional_detalle', pk=profesional.pk)
    return render(request, 'profesionales/form.html', {
        'form': form,
        'titulo': 'Nuevo profesional',
    })


@rol_requerido(*ROLES_ADMIN)
def profesional_editar(request, pk):
    profesional = get_object_or_404(Profesional, pk=pk)
    form = ProfesionalForm(request.POST or None, instance=profesional)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Los datos del profesional fueron actualizados.')
        return redirect('profesional_detalle', pk=profesional.pk)
    return render(request, 'profesionales/form.html', {
        'form': form,
        'titulo': f'Editar profesional: {profesional.nombre_completo}',
        'objeto': profesional,
    })


@rol_requerido(*ROLES_ADMIN)
@require_POST
def profesional_eliminar(request, pk):
    profesional = get_object_or_404(Profesional, pk=pk)
    nombre = profesional.nombre_completo
    profesional.delete()
    messages.success(request, f'El profesional {nombre} fue eliminado.')
    return redirect('profesionales_lista')


@rol_requerido(*ROLES_ADMIN)
def horario_crear(request, profesional_pk):
    profesional = get_object_or_404(Profesional, pk=profesional_pk)
    form = HorarioAtencionForm(request.POST or None, initial={'profesional': profesional})
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Bloque de atención agregado.')
        return redirect('profesional_detalle', pk=profesional.pk)
    return render(request, 'profesionales/horario_form.html', {
        'form': form,
        'profesional': profesional,
        'titulo': 'Nuevo bloque de atención',
    })


@rol_requerido(*ROLES_ADMIN)
def horario_editar(request, pk):
    horario = get_object_or_404(HorarioAtencion, pk=pk)
    form = HorarioAtencionForm(request.POST or None, instance=horario)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Bloque de atención actualizado.')
        return redirect('profesional_detalle', pk=horario.profesional_id)
    return render(request, 'profesionales/horario_form.html', {
        'form': form,
        'profesional': horario.profesional,
        'titulo': 'Editar bloque de atención',
        'objeto': horario,
    })


@rol_requerido(*ROLES_ADMIN)
@require_POST
def horario_eliminar(request, pk):
    horario = get_object_or_404(HorarioAtencion, pk=pk)
    profesional_id = horario.profesional_id
    horario.delete()
    messages.success(request, 'Bloque de atención eliminado.')
    return redirect('profesional_detalle', pk=profesional_id)


# =====================================================================
# CITAS
# =====================================================================
@login_required
def citas_lista(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    fecha = request.GET.get('fecha', '')
    profesional_id = request.GET.get('profesional', '')

    queryset = citas_visibles(request.user)
    if q:
        queryset = queryset.filter(
            Q(mascota__nombre__icontains=q)
            | Q(mascota__tutor__nombres__icontains=q)
            | Q(mascota__tutor__apellidos__icontains=q)
            | Q(motivo__icontains=q)
        )
    if estado:
        queryset = queryset.filter(estado=estado)
    if fecha:
        queryset = queryset.filter(fecha=fecha)
    if profesional_id:
        queryset = queryset.filter(profesional_id=profesional_id)

    queryset = queryset.order_by('-fecha', '-hora')
    return render(request, 'citas/lista.html', {
        'page_obj': paginar(request, queryset, 12),
        'q': q,
        'estado': estado,
        'fecha': fecha,
        'profesional_id': profesional_id,
        'estados': Cita.EstadoChoices.choices,
        'profesionales': Profesional.objects.filter(activo=True),
    })


@login_required
def citas_calendario(request):
    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get('anio', hoy.year))
        mes = int(request.GET.get('mes', hoy.month))
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month
    if mes < 1 or mes > 12:
        mes = hoy.month
    if anio < 2000 or anio > 2100:
        anio = hoy.year

    citas = citas_visibles(request.user).filter(fecha__year=anio, fecha__month=mes)
    por_dia = {}
    for cita in citas:
        por_dia.setdefault(cita.fecha, []).append(cita)

    calendario = calendar.Calendar(firstweekday=0)
    semanas = []
    for semana in calendario.monthdatescalendar(anio, mes):
        dias = []
        for dia in semana:
            dias.append({
                'fecha': dia,
                'en_mes': dia.month == mes,
                'es_hoy': dia == hoy,
                'citas': por_dia.get(dia, []),
            })
        semanas.append(dias)

    primer_dia = date(anio, mes, 1)
    anterior = primer_dia - timedelta(days=1)
    siguiente = (primer_dia.replace(day=28) + timedelta(days=4)).replace(day=1)

    return render(request, 'citas/calendario.html', {
        'semanas': semanas,
        'nombre_mes': MESES_ES[mes - 1],
        'anio': anio,
        'mes': mes,
        'anio_anterior': anterior.year,
        'mes_anterior': anterior.month,
        'anio_siguiente': siguiente.year,
        'mes_siguiente': siguiente.month,
        'dias_semana': ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'],
    })


@login_required
def cita_crear(request):
    fecha_inicial = request.GET.get('fecha') or timezone.localdate()
    form = CitaForm(
        request.POST or None,
        usuario=request.user,
        initial={'fecha': fecha_inicial},
    )
    if request.method == 'POST' and form.is_valid():
        cita = form.save()
        messages.success(request, 'La cita fue agendada correctamente.')
        return redirect('citas_lista')
    return render(request, 'citas/form.html', {
        'form': form,
        'titulo': 'Nueva cita',
    })


@rol_requerido(*ROLES_PERSONAL)
def cita_editar(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    form = CitaForm(request.POST or None, instance=cita, usuario=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'La cita fue actualizada.')
        return redirect('citas_lista')
    return render(request, 'citas/form.html', {
        'form': form,
        'titulo': 'Editar cita',
        'objeto': cita,
    })


@login_required
@require_POST
def cita_cancelar(request, pk):
    cita = get_object_or_404(citas_visibles(request.user), pk=pk)
    try:
        cita.cancelar()
    except ValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
    else:
        messages.success(request, 'La cita fue cancelada.')
    return redirect('citas_lista')


@rol_requerido(*ROLES_PERSONAL)
@require_POST
def cita_confirmar(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    try:
        cita.confirmar()
    except ValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
    else:
        messages.success(request, 'La cita fue confirmada.')
    return redirect('citas_lista')


@rol_requerido(*ROLES_VET_ADMIN)
@require_POST
def cita_atender(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    try:
        cita.atender()
    except ValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
    else:
        messages.success(request, 'La cita fue marcada como atendida.')
    return redirect('citas_lista')


@rol_requerido(*ROLES_PERSONAL)
@require_POST
def cita_no_asistio(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    if cita.estado in (Cita.EstadoChoices.PROGRAMADA, Cita.EstadoChoices.CONFIRMADA):
        cita.estado = Cita.EstadoChoices.NO_ASISTIO
        cita.save(update_fields=['estado', 'fecha_actualizacion'])
        messages.warning(request, 'La cita fue marcada como no asistida.')
    else:
        messages.error(request, 'Solo se pueden marcar citas activas como no asistidas.')
    return redirect('citas_lista')


@rol_requerido(*ROLES_ADMIN)
@require_POST
def cita_eliminar(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    cita.delete()
    messages.success(request, 'La cita fue eliminada.')
    return redirect('citas_lista')


# =====================================================================
# FICHAS CLÍNICAS
# =====================================================================
RecetaFormSet = inlineformset_factory(
    FichaClinica, Receta, form=RecetaForm, extra=2, can_delete=True
)
ExamenFormSet = inlineformset_factory(
    FichaClinica, Examen, form=ExamenForm, extra=2, can_delete=True
)


@login_required
def fichas_lista(request):
    q = request.GET.get('q', '').strip()
    queryset = fichas_visibles(request.user)
    if q:
        queryset = queryset.filter(
            Q(mascota__nombre__icontains=q)
            | Q(diagnostico__icontains=q)
            | Q(tratamiento__icontains=q)
            | Q(motivo_consulta__icontains=q)
        )
    return render(request, 'fichas/lista.html', {
        'page_obj': paginar(request, queryset, 10),
        'q': q,
    })


@login_required
def ficha_detalle(request, pk):
    ficha = get_object_or_404(fichas_visibles(request.user), pk=pk)
    return render(request, 'fichas/detalle.html', {'ficha': ficha})


@rol_requerido(*ROLES_VET_ADMIN)
def ficha_crear(request):
    cita = None
    initial = {}
    cita_id = request.GET.get('cita')
    if cita_id:
        cita = get_object_or_404(Cita, pk=cita_id)
        initial = {
            'cita': cita,
            'mascota': cita.mascota,
            'profesional': cita.profesional,
            'fecha': timezone.localtime(),
            'motivo_consulta': cita.motivo,
        }

    if request.method == 'POST':
        form = FichaClinicaForm(request.POST)
        if form.is_valid():
            ficha = form.save(commit=False)
            receta_formset = RecetaFormSet(request.POST, instance=ficha, prefix='recetas')
            examen_formset = ExamenFormSet(request.POST, instance=ficha, prefix='examenes')
            if receta_formset.is_valid() and examen_formset.is_valid():
                ficha.save()
                form.save_m2m()
                receta_formset.save()
                examen_formset.save()
                if ficha.cita_id and ficha.cita.estado in (
                    Cita.EstadoChoices.PROGRAMADA,
                    Cita.EstadoChoices.CONFIRMADA,
                ):
                    try:
                        ficha.cita.atender()
                    except ValidationError:
                        pass
                messages.success(request, 'La ficha clínica fue registrada.')
                return redirect('ficha_detalle', pk=ficha.pk)
        else:
            receta_formset = RecetaFormSet(request.POST, prefix='recetas')
            examen_formset = ExamenFormSet(request.POST, prefix='examenes')
    else:
        form = FichaClinicaForm(initial=initial)
        receta_formset = RecetaFormSet(prefix='recetas')
        examen_formset = ExamenFormSet(prefix='examenes')

    return render(request, 'fichas/form.html', {
        'form': form,
        'receta_formset': receta_formset,
        'examen_formset': examen_formset,
        'titulo': 'Nueva ficha clínica',
        'cita': cita,
    })


@rol_requerido(*ROLES_VET_ADMIN)
def ficha_editar(request, pk):
    ficha = get_object_or_404(FichaClinica, pk=pk)
    form = FichaClinicaForm(request.POST or None, instance=ficha)
    receta_formset = RecetaFormSet(
        request.POST or None, instance=ficha, prefix='recetas'
    )
    examen_formset = ExamenFormSet(
        request.POST or None, instance=ficha, prefix='examenes'
    )
    if (
        request.method == 'POST'
        and form.is_valid()
        and receta_formset.is_valid()
        and examen_formset.is_valid()
    ):
        form.save()
        receta_formset.save()
        examen_formset.save()
        messages.success(request, 'La ficha clínica fue actualizada.')
        return redirect('ficha_detalle', pk=ficha.pk)

    return render(request, 'fichas/form.html', {
        'form': form,
        'receta_formset': receta_formset,
        'examen_formset': examen_formset,
        'titulo': f'Editar ficha de {ficha.mascota.nombre}',
        'objeto': ficha,
    })


@rol_requerido(*ROLES_ADMIN)
@require_POST
def ficha_eliminar(request, pk):
    ficha = get_object_or_404(FichaClinica, pk=pk)
    ficha.delete()
    messages.success(request, 'La ficha clínica fue eliminada.')
    return redirect('fichas_lista')


# =====================================================================
# VACUNAS
# =====================================================================
@login_required
def vacunas_lista(request):
    q = request.GET.get('q', '').strip()
    queryset = vacunas_visibles(request.user)
    if q:
        queryset = queryset.filter(
            Q(nombre__icontains=q)
            | Q(mascota__nombre__icontains=q)
            | Q(lote__icontains=q)
        )
    return render(request, 'vacunas/lista.html', {
        'page_obj': paginar(request, queryset, 12),
        'q': q,
    })


@rol_requerido(*ROLES_VET_ADMIN)
def vacuna_crear(request):
    form = VacunaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        vacuna = form.save()
        messages.success(
            request,
            'Vacuna registrada. Si indicaste próxima dosis, se creó el recordatorio automático.',
        )
        return redirect('vacunas_lista')
    return render(request, 'vacunas/form.html', {'form': form, 'titulo': 'Nueva vacuna'})


@rol_requerido(*ROLES_VET_ADMIN)
def vacuna_editar(request, pk):
    vacuna = get_object_or_404(Vacuna, pk=pk)
    form = VacunaForm(request.POST or None, instance=vacuna)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'La vacuna fue actualizada.')
        return redirect('vacunas_lista')
    return render(request, 'vacunas/form.html', {
        'form': form,
        'titulo': 'Editar vacuna',
        'objeto': vacuna,
    })


@rol_requerido(*ROLES_ADMIN)
@require_POST
def vacuna_eliminar(request, pk):
    vacuna = get_object_or_404(Vacuna, pk=pk)
    vacuna.delete()
    messages.success(request, 'La vacuna fue eliminada.')
    return redirect('vacunas_lista')


# =====================================================================
# RECORDATORIOS
# =====================================================================
@login_required
def recordatorios_lista(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')
    queryset = recordatorios_visibles(request.user)
    if q:
        queryset = queryset.filter(
            Q(titulo__icontains=q)
            | Q(descripcion__icontains=q)
            | Q(mascota__nombre__icontains=q)
        )
    if estado:
        queryset = queryset.filter(estado=estado)
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    return render(request, 'recordatorios/lista.html', {
        'page_obj': paginar(request, queryset, 12),
        'q': q,
        'estado': estado,
        'tipo': tipo,
        'estados': Recordatorio.EstadoChoices.choices,
        'tipos': Recordatorio.TipoChoices.choices,
    })


@rol_requerido(*ROLES_PERSONAL)
def recordatorio_crear(request):
    form = RecordatorioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Recordatorio creado.')
        return redirect('recordatorios_lista')
    return render(request, 'recordatorios/form.html', {
        'form': form,
        'titulo': 'Nuevo recordatorio',
    })


@rol_requerido(*ROLES_PERSONAL)
def recordatorio_editar(request, pk):
    recordatorio = get_object_or_404(Recordatorio, pk=pk)
    form = RecordatorioForm(request.POST or None, instance=recordatorio)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Recordatorio actualizado.')
        return redirect('recordatorios_lista')
    return render(request, 'recordatorios/form.html', {
        'form': form,
        'titulo': 'Editar recordatorio',
        'objeto': recordatorio,
    })


@rol_requerido(*ROLES_PERSONAL)
@require_POST
def recordatorio_enviar(request, pk):
    recordatorio = get_object_or_404(Recordatorio, pk=pk)
    recordatorio.marcar_enviado()
    messages.success(request, 'Recordatorio marcado como enviado.')
    return redirect('recordatorios_lista')


@rol_requerido(*ROLES_PERSONAL)
@require_POST
def recordatorio_completar(request, pk):
    recordatorio = get_object_or_404(Recordatorio, pk=pk)
    recordatorio.marcar_completado()
    messages.success(request, 'Recordatorio marcado como completado.')
    return redirect('recordatorios_lista')


@rol_requerido(*ROLES_ADMIN)
@require_POST
def recordatorio_eliminar(request, pk):
    recordatorio = get_object_or_404(Recordatorio, pk=pk)
    recordatorio.delete()
    messages.success(request, 'Recordatorio eliminado.')
    return redirect('recordatorios_lista')


# =====================================================================
# SALUD Y ERRORES
# =====================================================================
def health_view(request):
    return JsonResponse({
        'status': 'ok',
        'service': 'PetCare',
        'timestamp': timezone.now().isoformat(),
    })


def error_404(request, exception):
    return render(request, '404.html', status=404)


def error_500(request):
    return render(request, '500.html', status=500)
