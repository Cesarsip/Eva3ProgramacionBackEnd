"""Personalización del panel de administración de Django para PetCare."""
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django.utils.html import format_html

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

admin.site.site_header = 'PetCare · Administración Veterinaria'
admin.site.site_title = 'PetCare Admin'
admin.site.index_title = 'Panel de gestión de la clínica'


# =====================================================================
# USUARIOS
# =====================================================================
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = (
        'username', 'nombre_completo', 'email', 'rol', 'is_staff',
        'is_active', 'date_joined',
    )
    list_filter = ('rol', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'rut')
    ordering = ('username',)
    readonly_fields = ('date_joined', 'last_login')

    fieldsets = UserAdmin.fieldsets + (
        ('Datos PetCare', {'fields': ('rol', 'rut', 'telefono')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos PetCare', {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'rol', 'rut', 'telefono'),
        }),
    )

    @admin.display(description='Nombre completo')
    def nombre_completo(self, obj):
        return obj.nombre_completo


# =====================================================================
# TUTORES Y MASCOTAS
# =====================================================================
class MascotaInline(admin.TabularInline):
    model = Mascota
    extra = 0
    fields = ('nombre', 'especie', 'raza', 'sexo', 'activo')
    show_change_link = True


@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = (
        'nombre_completo', 'rut', 'email', 'telefono', 'total_mascotas',
        'activo', 'fecha_registro',
    )
    list_filter = ('activo',)
    search_fields = ('nombres', 'apellidos', 'rut', 'email', 'telefono')
    readonly_fields = ('fecha_registro',)
    inlines = [MascotaInline]
    list_per_page = 20

    @admin.display(description='Mascotas')
    def total_mascotas(self, obj):
        return obj.total_mascotas


class VacunaInline(admin.TabularInline):
    model = Vacuna
    extra = 0
    fields = ('nombre', 'fecha_aplicacion', 'proxima_dosis', 'profesional', 'lote')
    autocomplete_fields = ('profesional',)
    show_change_link = True


class RecordatorioInline(admin.TabularInline):
    model = Recordatorio
    extra = 0
    fields = ('titulo', 'tipo', 'fecha_programada', 'estado')
    show_change_link = True


@admin.register(Mascota)
class MascotaAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'especie', 'raza', 'tutor', 'sexo', 'edad', 'activo',
        'fecha_registro',
    )
    list_filter = ('especie', 'sexo', 'activo')
    search_fields = ('nombre', 'raza', 'microchip', 'tutor__nombres', 'tutor__apellidos')
    autocomplete_fields = ('tutor',)
    readonly_fields = ('fecha_registro',)
    inlines = [VacunaInline, RecordatorioInline]
    list_select_related = ('tutor',)

    @admin.display(description='Edad')
    def edad(self, obj):
        return obj.edad


# =====================================================================
# PROFESIONALES Y HORARIOS
# =====================================================================
class HorarioAtencionInline(admin.TabularInline):
    model = HorarioAtencion
    extra = 0
    fields = ('dia_semana', 'hora_inicio', 'hora_fin', 'activo')


@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    list_display = (
        'nombre_completo', 'especialidad', 'registro_profesional', 'email',
        'telefono', 'activo',
    )
    list_filter = ('especialidad', 'activo')
    search_fields = ('nombres', 'apellidos', 'especialidad', 'registro_profesional', 'email')
    readonly_fields = ('fecha_registro',)
    inlines = [HorarioAtencionInline]


@admin.register(HorarioAtencion)
class HorarioAtencionAdmin(admin.ModelAdmin):
    list_display = ('profesional', 'dia_semana', 'hora_inicio', 'hora_fin', 'activo')
    list_filter = ('dia_semana', 'activo', 'profesional')
    autocomplete_fields = ('profesional',)
    ordering = ('profesional', 'dia_semana', 'hora_inicio')


# =====================================================================
# CITAS
# =====================================================================
@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = (
        'mascota', 'tutor', 'profesional', 'fecha', 'hora',
        'estado_coloreado', 'fecha_creacion',
    )
    list_filter = ('estado', 'fecha', 'profesional')
    search_fields = (
        'mascota__nombre', 'mascota__tutor__nombres', 'mascota__tutor__apellidos',
        'profesional__nombres', 'profesional__apellidos', 'motivo',
    )
    autocomplete_fields = ('mascota', 'profesional')
    date_hierarchy = 'fecha'
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    list_select_related = ('mascota', 'mascota__tutor', 'profesional')
    actions = ('confirmar_citas', 'cancelar_citas', 'marcar_atendidas')
    fieldsets = (
        ('Paciente y profesional', {
            'fields': ('mascota', 'profesional'),
        }),
        ('Agenda', {
            'fields': ('fecha', 'hora', 'estado'),
        }),
        ('Detalle de la consulta', {
            'fields': ('motivo', 'notas'),
        }),
        ('Auditoría', {
            'classes': ('collapse',),
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
        }),
    )

    @admin.display(description='Tutor')
    def tutor(self, obj):
        return obj.mascota.tutor.nombre_completo

    @admin.display(description='Estado')
    def estado_coloreado(self, obj):
        colores = {
            'PROGRAMADA': '#6c757d',
            'CONFIRMADA': '#0d6efd',
            'ATENDIDA': '#198754',
            'CANCELADA': '#dc3545',
            'NO_ASISTIO': '#fd7e14',
        }
        return format_html(
            '<strong style="color:{}">{}</strong>',
            colores.get(obj.estado, '#6c757d'),
            obj.get_estado_display(),
        )

    def _accion_estado(self, request, queryset, metodo, etiqueta):
        exitos, errores = 0, []
        for cita in queryset:
            try:
                getattr(cita, metodo)()
                exitos += 1
            except ValidationError as exc:
                errores.append(f'{cita}: {"; ".join(exc.messages)}')
        if exitos:
            self.message_user(
                request,
                f'{exitos} cita(s) {etiqueta} correctamente.',
                messages.SUCCESS,
            )
        if errores:
            self.message_user(request, ' | '.join(errores), messages.ERROR)

    @admin.action(description='Confirmar citas seleccionadas')
    def confirmar_citas(self, request, queryset):
        self._accion_estado(request, queryset, 'confirmar', 'confirmada(s)')

    @admin.action(description='Cancelar citas seleccionadas')
    def cancelar_citas(self, request, queryset):
        self._accion_estado(request, queryset, 'cancelar', 'cancelada(s)')

    @admin.action(description='Marcar citas como atendidas')
    def marcar_atendidas(self, request, queryset):
        self._accion_estado(request, queryset, 'atender', 'atendida(s)')


# =====================================================================
# FICHA CLÍNICA, RECETAS Y EXÁMENES
# =====================================================================
class RecetaInline(admin.TabularInline):
    model = Receta
    extra = 1
    fields = ('medicamento', 'dosis', 'frecuencia', 'duracion', 'indicaciones')


class ExamenInline(admin.TabularInline):
    model = Examen
    extra = 1
    fields = ('tipo', 'fecha', 'resultado', 'archivo_url', 'observaciones')


@admin.register(FichaClinica)
class FichaClinicaAdmin(admin.ModelAdmin):
    list_display = (
        'mascota', 'profesional', 'fecha', 'diagnostico_corto',
        'proxima_revision', 'fecha_creacion',
    )
    list_filter = ('profesional', 'fecha', 'proxima_revision')
    search_fields = (
        'mascota__nombre', 'mascota__tutor__nombres', 'mascota__tutor__apellidos',
        'diagnostico', 'tratamiento',
    )
    autocomplete_fields = ('mascota', 'profesional', 'cita')
    date_hierarchy = 'fecha'
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    inlines = [RecetaInline, ExamenInline]
    list_select_related = ('mascota', 'profesional')
    fieldsets = (
        ('Paciente y atención', {
            'fields': ('mascota', 'cita', 'profesional', 'fecha'),
        }),
        ('Registro clínico', {
            'fields': ('motivo_consulta', 'diagnostico', 'tratamiento', 'observaciones'),
        }),
        ('Signos vitales', {
            'fields': ('peso_kg', 'temperatura', 'frecuencia_cardiaca', 'proxima_revision'),
        }),
        ('Auditoría', {
            'classes': ('collapse',),
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
        }),
    )

    @admin.display(description='Diagnóstico')
    def diagnostico_corto(self, obj):
        texto = obj.diagnostico.strip()
        return texto if len(texto) <= 70 else f'{texto[:70]}…'


@admin.register(Receta)
class RecetaAdmin(admin.ModelAdmin):
    list_display = ('medicamento', 'ficha', 'dosis', 'frecuencia', 'duracion')
    search_fields = ('medicamento', 'ficha__mascota__nombre')
    autocomplete_fields = ('ficha',)


@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'ficha', 'fecha', 'archivo_url')
    list_filter = ('fecha',)
    search_fields = ('tipo', 'ficha__mascota__nombre', 'resultado')
    autocomplete_fields = ('ficha',)
    date_hierarchy = 'fecha'


# =====================================================================
# VACUNAS Y RECORDATORIOS
# =====================================================================
@admin.register(Vacuna)
class VacunaAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'mascota', 'fecha_aplicacion', 'proxima_dosis',
        'profesional', 'lote',
    )
    list_filter = ('nombre', 'fecha_aplicacion', 'proxima_dosis')
    search_fields = ('nombre', 'mascota__nombre', 'lote')
    autocomplete_fields = ('mascota', 'profesional')
    date_hierarchy = 'fecha_aplicacion'
    list_select_related = ('mascota', 'profesional')


@admin.register(Recordatorio)
class RecordatorioAdmin(admin.ModelAdmin):
    list_display = (
        'titulo', 'mascota', 'tipo', 'fecha_programada', 'estado',
        'fecha_envio',
    )
    list_filter = ('tipo', 'estado', 'fecha_programada')
    search_fields = ('titulo', 'descripcion', 'mascota__nombre')
    autocomplete_fields = ('mascota', 'vacuna', 'ficha')
    date_hierarchy = 'fecha_programada'
    list_editable = ('estado',)
    list_select_related = ('mascota',)
    actions = ('marcar_enviados', 'marcar_completados')

    @admin.action(description='Marcar recordatorios como enviados')
    def marcar_enviados(self, request, queryset):
        enviados = 0
        for recordatorio in queryset.exclude(
            estado=Recordatorio.EstadoChoices.COMPLETADO
        ):
            recordatorio.marcar_enviado()
            enviados += 1
        self.message_user(
            request,
            f'{enviados} recordatorio(s) marcado(s) como enviado(s).',
            messages.SUCCESS,
        )

    @admin.action(description='Marcar recordatorios como completados')
    def marcar_completados(self, request, queryset):
        completados = 0
        for recordatorio in queryset:
            recordatorio.marcar_completado()
            completados += 1
        self.message_user(
            request,
            f'{completados} recordatorio(s) marcado(s) como completado(s).',
            messages.SUCCESS,
        )
