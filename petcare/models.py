import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# =====================================================================
# USUARIO Y ROLES
# =====================================================================
class Usuario(AbstractUser):
    """Usuario del sistema con roles de la clínica veterinaria."""

    class RolChoices(models.TextChoices):
        ADMINISTRADOR = 'ADMINISTRADOR', 'Administrador'
        VETERINARIO = 'VETERINARIO', 'Veterinario'
        RECEPCIONISTA = 'RECEPCIONISTA', 'Recepcionista'
        TUTOR = 'TUTOR', 'Tutor / Dueño'

    rol = models.CharField(
        max_length=20,
        choices=RolChoices.choices,
        default=RolChoices.TUTOR,
        verbose_name='Rol',
    )
    rut = models.CharField(max_length=20, blank=True, null=True, verbose_name='RUT')
    telefono = models.CharField(max_length=25, blank=True, null=True, verbose_name='Teléfono')

    class Meta:
        db_table = 'petcare_usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def save(self, *args, **kwargs):
        # Un superusuario siempre debe tener el rol administrativo.
        if self.is_superuser:
            self.rol = self.RolChoices.ADMINISTRADOR
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def nombre_completo(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.username

    @property
    def is_administrador(self):
        return self.rol == self.RolChoices.ADMINISTRADOR or self.is_superuser

    @property
    def is_veterinario(self):
        return self.rol == self.RolChoices.VETERINARIO or self.is_administrador

    @property
    def is_recepcionista(self):
        return self.rol == self.RolChoices.RECEPCIONISTA or self.is_administrador

    @property
    def is_tutor(self):
        return self.rol == self.RolChoices.TUTOR

    @property
    def puede_gestionar_clinica(self):
        return self.is_administrador or self.is_veterinario or self.is_recepcionista

    def __str__(self):
        return f'{self.username} [{self.get_rol_display()}]'


# =====================================================================
# TUTORES Y MASCOTAS
# =====================================================================
class Tutor(models.Model):
    """Persona responsable de una o más mascotas."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tutor_profile',
        verbose_name='Usuario del portal',
    )
    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    rut = models.CharField(max_length=20, unique=True, verbose_name='RUT')
    email = models.EmailField(unique=True, verbose_name='Correo electrónico')
    telefono = models.CharField(max_length=25, verbose_name='Teléfono')
    direccion = models.CharField(max_length=200, blank=True, default='', verbose_name='Dirección')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')

    class Meta:
        db_table = 'petcare_tutor'
        verbose_name = 'Tutor'
        verbose_name_plural = 'Tutores'
        ordering = ['apellidos', 'nombres']

    def clean(self):
        if self.usuario and self.usuario.rol not in (
            Usuario.RolChoices.TUTOR,
            Usuario.RolChoices.ADMINISTRADOR,
        ):
            raise ValidationError({'usuario': 'El usuario asociado debe tener rol Tutor o Administrador.'})

    def save(self, *args, **kwargs):
        # Completa los datos desde el usuario del portal cuando falten.
        if self.usuario:
            self.nombres = self.nombres or self.usuario.first_name
            self.apellidos = self.apellidos or self.usuario.last_name
            self.email = self.email or self.usuario.email
            self.rut = self.rut or (self.usuario.rut or '')
            self.telefono = self.telefono or (self.usuario.telefono or '')
        super().save(*args, **kwargs)

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'.strip()

    @property
    def total_mascotas(self):
        return self.mascotas.filter(activo=True).count()

    def __str__(self):
        return f'{self.nombre_completo} ({self.rut})'


class Mascota(models.Model):
    """Paciente veterinario."""

    class EspecieChoices(models.TextChoices):
        PERRO = 'PERRO', 'Perro'
        GATO = 'GATO', 'Gato'
        CONEJO = 'CONEJO', 'Conejo'
        AVE = 'AVE', 'Ave'
        REPTIL = 'REPTIL', 'Reptil'
        OTRO = 'OTRO', 'Otro'

    class SexoChoices(models.TextChoices):
        MACHO = 'M', 'Macho'
        HEMBRA = 'H', 'Hembra'
        DESCONOCIDO = 'X', 'No especificado'

    tutor = models.ForeignKey(
        Tutor,
        on_delete=models.CASCADE,
        related_name='mascotas',
        verbose_name='Tutor responsable',
    )
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    especie = models.CharField(
        max_length=20,
        choices=EspecieChoices.choices,
        default=EspecieChoices.PERRO,
        verbose_name='Especie',
    )
    raza = models.CharField(max_length=100, blank=True, default='', verbose_name='Raza')
    sexo = models.CharField(
        max_length=1,
        choices=SexoChoices.choices,
        default=SexoChoices.DESCONOCIDO,
        verbose_name='Sexo',
    )
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name='Fecha de nacimiento')
    peso_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Peso (kg)',
    )
    microchip = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Número de microchip',
    )
    color = models.CharField(max_length=80, blank=True, default='', verbose_name='Color / señas')
    observaciones = models.TextField(blank=True, default='', verbose_name='Observaciones')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')

    class Meta:
        db_table = 'petcare_mascota'
        verbose_name = 'Mascota'
        verbose_name_plural = 'Mascotas'
        ordering = ['nombre']

    def clean(self):
        if not self.microchip:
            # Evita que varios pacientes sin microchip choquen con el índice único.
            self.microchip = None
        if self.fecha_nacimiento and self.fecha_nacimiento > timezone.localdate():
            raise ValidationError({'fecha_nacimiento': 'La fecha de nacimiento no puede ser futura.'})
        if self.peso_kg is not None and self.peso_kg <= 0:
            raise ValidationError({'peso_kg': 'El peso debe ser mayor que cero.'})

    def save(self, *args, **kwargs):
        if not self.microchip:
            self.microchip = None
        super().save(*args, **kwargs)

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return 'Sin dato'
        hoy = timezone.localdate()
        anios = hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )
        if anios >= 1:
            return f'{anios} año{"s" if anios != 1 else ""}'
        meses = (hoy.year - self.fecha_nacimiento.year) * 12 + hoy.month - self.fecha_nacimiento.month
        if hoy.day < self.fecha_nacimiento.day:
            meses -= 1
        meses = max(meses, 0)
        return f'{meses} mes{"es" if meses != 1 else ""}'

    @property
    def especie_icono(self):
        return {
            self.EspecieChoices.PERRO: 'bi-github',
            self.EspecieChoices.GATO: 'bi-heart',
            self.EspecieChoices.CONEJO: 'bi-flower1',
            self.EspecieChoices.AVE: 'bi-twitter',
            self.EspecieChoices.REPTIL: 'bi-bug',
        }.get(self.especie, 'bi-paw')

    def __str__(self):
        return f'{self.nombre} ({self.get_especie_display()})'


# =====================================================================
# PROFESIONALES Y HORARIOS
# =====================================================================
class Profesional(models.Model):
    """Veterinario que atiende en la clínica."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='perfil_profesional',
        verbose_name='Usuario del sistema',
    )
    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    especialidad = models.CharField(max_length=120, verbose_name='Especialidad')
    registro_profesional = models.CharField(
        max_length=60,
        unique=True,
        verbose_name='Registro profesional',
    )
    email = models.EmailField(verbose_name='Correo electrónico')
    telefono = models.CharField(max_length=25, blank=True, default='', verbose_name='Teléfono')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')

    class Meta:
        db_table = 'petcare_profesional'
        verbose_name = 'Profesional'
        verbose_name_plural = 'Profesionales'
        ordering = ['apellidos', 'nombres']

    def save(self, *args, **kwargs):
        if self.usuario:
            self.nombres = self.nombres or self.usuario.first_name
            self.apellidos = self.apellidos or self.usuario.last_name
            self.email = self.email or self.usuario.email
        super().save(*args, **kwargs)

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'.strip()

    def __str__(self):
        return f'Dr(a). {self.nombre_completo} - {self.especialidad}'


class HorarioAtencion(models.Model):
    """Bloque de disponibilidad semanal de un profesional."""

    class DiaChoices(models.IntegerChoices):
        LUNES = 0, 'Lunes'
        MARTES = 1, 'Martes'
        MIERCOLES = 2, 'Miércoles'
        JUEVES = 3, 'Jueves'
        VIERNES = 4, 'Viernes'
        SABADO = 5, 'Sábado'
        DOMINGO = 6, 'Domingo'

    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.CASCADE,
        related_name='horarios',
        verbose_name='Profesional',
    )
    dia_semana = models.IntegerField(choices=DiaChoices.choices, verbose_name='Día de la semana')
    hora_inicio = models.TimeField(verbose_name='Hora de inicio')
    hora_fin = models.TimeField(verbose_name='Hora de término')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        db_table = 'petcare_horario_atencion'
        verbose_name = 'Horario de atención'
        verbose_name_plural = 'Horarios de atención'
        ordering = ['profesional', 'dia_semana', 'hora_inicio']
        unique_together = ('profesional', 'dia_semana', 'hora_inicio')

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError({'hora_fin': 'La hora de término debe ser posterior a la de inicio.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f'{self.profesional.nombre_completo} - '
            f'{self.get_dia_semana_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}'
        )


# =====================================================================
# CITAS
# =====================================================================
class Cita(models.Model):
    """Cita médica de una mascota con un profesional."""

    class EstadoChoices(models.TextChoices):
        PROGRAMADA = 'PROGRAMADA', 'Programada'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        ATENDIDA = 'ATENDIDA', 'Atendida'
        CANCELADA = 'CANCELADA', 'Cancelada'
        NO_ASISTIO = 'NO_ASISTIO', 'No asistió'

    mascota = models.ForeignKey(
        Mascota,
        on_delete=models.CASCADE,
        related_name='citas',
        verbose_name='Mascota',
    )
    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.PROTECT,
        related_name='citas',
        verbose_name='Profesional',
    )
    fecha = models.DateField(verbose_name='Fecha')
    hora = models.TimeField(verbose_name='Hora')
    motivo = models.TextField(verbose_name='Motivo de la consulta')
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.PROGRAMADA,
        verbose_name='Estado',
    )
    notas = models.TextField(blank=True, default='', verbose_name='Notas internas')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        db_table = 'petcare_cita'
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['fecha', 'hora']
        constraints = [
            models.UniqueConstraint(
                fields=['profesional', 'fecha', 'hora'],
                condition=models.Q(estado__in=['PROGRAMADA', 'CONFIRMADA']),
                name='uniq_cita_activa_profesional',
            ),
            models.UniqueConstraint(
                fields=['mascota', 'fecha', 'hora'],
                condition=models.Q(estado__in=['PROGRAMADA', 'CONFIRMADA']),
                name='uniq_cita_activa_mascota',
            ),
        ]

    def clean(self):
        if not self.fecha or not self.hora or not self.profesional_id or not self.mascota_id:
            return

        if self._state.adding and self.fecha < timezone.localdate():
            raise ValidationError({'fecha': 'No se pueden agendar citas en fechas pasadas.'})

        if self.estado not in (self.EstadoChoices.PROGRAMADA, self.EstadoChoices.CONFIRMADA):
            return

        if not self.profesional.activo:
            raise ValidationError({'profesional': 'El profesional no está activo.'})
        if not self.mascota.activo:
            raise ValidationError({'mascota': 'La mascota no está activa.'})

        dia = self.fecha.weekday()
        horarios = HorarioAtencion.objects.filter(
            profesional=self.profesional,
            dia_semana=dia,
            activo=True,
        )
        if not horarios.exists():
            raise ValidationError({'fecha': 'El profesional no tiene horario configurado para ese día.'})
        if not any(h.hora_inicio <= self.hora < h.hora_fin for h in horarios):
            raise ValidationError({'hora': 'La hora elegida está fuera del horario de atención del profesional.'})

        conflictos_profesional = Cita.objects.filter(
            profesional=self.profesional,
            fecha=self.fecha,
            hora=self.hora,
            estado__in=[self.EstadoChoices.PROGRAMADA, self.EstadoChoices.CONFIRMADA],
        ).exclude(pk=self.pk)
        if conflictos_profesional.exists():
            raise ValidationError({'hora': 'El profesional ya tiene una cita activa en ese horario.'})

        conflictos_mascota = Cita.objects.filter(
            mascota=self.mascota,
            fecha=self.fecha,
            hora=self.hora,
            estado__in=[self.EstadoChoices.PROGRAMADA, self.EstadoChoices.CONFIRMADA],
        ).exclude(pk=self.pk)
        if conflictos_mascota.exists():
            raise ValidationError({'hora': 'La mascota ya tiene otra cita activa en ese horario.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def puede_cancelar(self):
        return self.estado in (self.EstadoChoices.PROGRAMADA, self.EstadoChoices.CONFIRMADA)

    @property
    def badge_class(self):
        return {
            self.EstadoChoices.PROGRAMADA: 'text-bg-secondary',
            self.EstadoChoices.CONFIRMADA: 'text-bg-primary',
            self.EstadoChoices.ATENDIDA: 'text-bg-success',
            self.EstadoChoices.CANCELADA: 'text-bg-danger',
            self.EstadoChoices.NO_ASISTIO: 'text-bg-warning',
        }.get(self.estado, 'text-bg-secondary')

    def confirmar(self):
        if self.estado != self.EstadoChoices.PROGRAMADA:
            raise ValidationError('Solo se pueden confirmar citas programadas.')
        self.estado = self.EstadoChoices.CONFIRMADA
        self.save(update_fields=['estado', 'fecha_actualizacion'])

    def atender(self):
        if self.estado not in (self.EstadoChoices.PROGRAMADA, self.EstadoChoices.CONFIRMADA):
            raise ValidationError('Solo se pueden atender citas programadas o confirmadas.')
        self.estado = self.EstadoChoices.ATENDIDA
        self.save(update_fields=['estado', 'fecha_actualizacion'])

    def cancelar(self):
        if not self.puede_cancelar:
            raise ValidationError('Esta cita ya no se puede cancelar.')
        self.estado = self.EstadoChoices.CANCELADA
        self.save(update_fields=['estado', 'fecha_actualizacion'])

    def __str__(self):
        return f'{self.fecha} {self.hora:%H:%M} - {self.mascota.nombre} con {self.profesional.nombre_completo}'


# =====================================================================
# FICHA CLÍNICA, RECETAS Y EXÁMENES
# =====================================================================
class FichaClinica(models.Model):
    """Registro clínico de una atención veterinaria."""

    mascota = models.ForeignKey(
        Mascota,
        on_delete=models.CASCADE,
        related_name='fichas',
        verbose_name='Mascota',
    )
    cita = models.OneToOneField(
        Cita,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ficha_clinica',
        verbose_name='Cita asociada',
    )
    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.PROTECT,
        related_name='fichas',
        verbose_name='Profesional',
    )
    fecha = models.DateTimeField(default=timezone.now, verbose_name='Fecha de atención')
    motivo_consulta = models.TextField(verbose_name='Motivo de consulta')
    diagnostico = models.TextField(verbose_name='Diagnóstico')
    tratamiento = models.TextField(verbose_name='Tratamiento')
    observaciones = models.TextField(blank=True, default='', verbose_name='Observaciones')
    peso_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Peso (kg)',
    )
    temperatura = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Temperatura (°C)',
    )
    frecuencia_cardiaca = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Frecuencia cardíaca (lpm)',
    )
    proxima_revision = models.DateField(
        null=True,
        blank=True,
        verbose_name='Próxima revisión',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        db_table = 'petcare_ficha_clinica'
        verbose_name = 'Ficha clínica'
        verbose_name_plural = 'Fichas clínicas'
        ordering = ['-fecha']

    def clean(self):
        if self.cita_id:
            if not self.mascota_id:
                self.mascota = self.cita.mascota
            elif self.mascota_id != self.cita.mascota_id:
                raise ValidationError({'mascota': 'La mascota no coincide con la cita seleccionada.'})
            if not self.profesional_id:
                self.profesional = self.cita.profesional
        if self.proxima_revision and self.proxima_revision < self.fecha.date():
            raise ValidationError({'proxima_revision': 'La próxima revisión no puede ser anterior a la atención.'})

    def save(self, *args, **kwargs):
        # Completa mascota y profesional desde la cita antes de validar.
        if self.cita_id:
            if not self.mascota_id:
                self.mascota_id = self.cita.mascota_id
            if not self.profesional_id:
                self.profesional_id = self.cita.profesional_id
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Ficha de {self.mascota.nombre} - {self.fecha:%d/%m/%Y}'


class Receta(models.Model):
    """Medicamento recetado dentro de una ficha clínica."""

    ficha = models.ForeignKey(
        FichaClinica,
        on_delete=models.CASCADE,
        related_name='recetas',
        verbose_name='Ficha clínica',
    )
    medicamento = models.CharField(max_length=150, verbose_name='Medicamento')
    dosis = models.CharField(max_length=100, verbose_name='Dosis')
    frecuencia = models.CharField(max_length=100, verbose_name='Frecuencia')
    duracion = models.CharField(max_length=100, verbose_name='Duración')
    indicaciones = models.TextField(blank=True, default='', verbose_name='Indicaciones')

    class Meta:
        db_table = 'petcare_receta'
        verbose_name = 'Receta'
        verbose_name_plural = 'Recetas'
        ordering = ['medicamento']

    def __str__(self):
        return f'{self.medicamento} - {self.dosis}'


class Examen(models.Model):
    """Examen o procedimiento realizado durante la atención."""

    ficha = models.ForeignKey(
        FichaClinica,
        on_delete=models.CASCADE,
        related_name='examenes',
        verbose_name='Ficha clínica',
    )
    tipo = models.CharField(max_length=120, verbose_name='Tipo de examen')
    resultado = models.TextField(verbose_name='Resultado')
    fecha = models.DateField(default=timezone.localdate, verbose_name='Fecha del examen')
    archivo_url = models.CharField(
        max_length=300,
        blank=True,
        default='',
        verbose_name='URL del archivo (opcional)',
    )
    observaciones = models.TextField(blank=True, default='', verbose_name='Observaciones')

    class Meta:
        db_table = 'petcare_examen'
        verbose_name = 'Examen'
        verbose_name_plural = 'Exámenes'
        ordering = ['-fecha', 'tipo']

    def __str__(self):
        return f'{self.tipo} - {self.fecha}'


# =====================================================================
# VACUNAS Y RECORDATORIOS
# =====================================================================
class Vacuna(models.Model):
    """Vacuna aplicada a una mascota y su próxima dosis."""

    mascota = models.ForeignKey(
        Mascota,
        on_delete=models.CASCADE,
        related_name='vacunas',
        verbose_name='Mascota',
    )
    nombre = models.CharField(max_length=120, verbose_name='Vacuna')
    fecha_aplicacion = models.DateField(default=timezone.localdate, verbose_name='Fecha de aplicación')
    proxima_dosis = models.DateField(null=True, blank=True, verbose_name='Próxima dosis')
    profesional = models.ForeignKey(
        Profesional,
        on_delete=models.PROTECT,
        related_name='vacunas',
        verbose_name='Profesional',
    )
    lote = models.CharField(max_length=80, blank=True, default='', verbose_name='Lote')
    observaciones = models.TextField(blank=True, default='', verbose_name='Observaciones')

    class Meta:
        db_table = 'petcare_vacuna'
        verbose_name = 'Vacuna'
        verbose_name_plural = 'Vacunas'
        ordering = ['-fecha_aplicacion']

    def clean(self):
        if self.proxima_dosis and self.fecha_aplicacion and self.proxima_dosis < self.fecha_aplicacion:
            raise ValidationError({'proxima_dosis': 'La próxima dosis no puede ser anterior a la aplicación.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nombre} - {self.mascota.nombre}'


class Recordatorio(models.Model):
    """Aviso de vacunación, control periódico u otra tarea pendiente."""

    class TipoChoices(models.TextChoices):
        VACUNA = 'VACUNA', 'Vacunación'
        CONTROL = 'CONTROL', 'Control periódico'
        OTRO = 'OTRO', 'Otro'

    class EstadoChoices(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ENVIADO = 'ENVIADO', 'Enviado'
        COMPLETADO = 'COMPLETADO', 'Completado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    mascota = models.ForeignKey(
        Mascota,
        on_delete=models.CASCADE,
        related_name='recordatorios',
        verbose_name='Mascota',
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoChoices.choices,
        default=TipoChoices.CONTROL,
        verbose_name='Tipo',
    )
    titulo = models.CharField(max_length=150, verbose_name='Título')
    descripcion = models.TextField(blank=True, default='', verbose_name='Descripción')
    fecha_programada = models.DateField(verbose_name='Fecha programada')
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.PENDIENTE,
        verbose_name='Estado',
    )
    vacuna = models.OneToOneField(
        Vacuna,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='recordatorio',
        verbose_name='Vacuna asociada',
    )
    ficha = models.OneToOneField(
        FichaClinica,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='recordatorio_control',
        verbose_name='Ficha asociada',
    )
    notas = models.TextField(blank=True, default='', verbose_name='Notas')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_envio = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de envío')

    class Meta:
        db_table = 'petcare_recordatorio'
        verbose_name = 'Recordatorio'
        verbose_name_plural = 'Recordatorios'
        ordering = ['fecha_programada', 'mascota__nombre']

    def clean(self):
        if self.vacuna_id and self.vacuna.mascota_id != self.mascota_id:
            raise ValidationError({'mascota': 'La mascota no coincide con la vacuna asociada.'})
        if self.ficha_id and self.ficha.mascota_id != self.mascota_id:
            raise ValidationError({'mascota': 'La mascota no coincide con la ficha asociada.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def badge_class(self):
        return {
            self.EstadoChoices.PENDIENTE: 'text-bg-warning',
            self.EstadoChoices.ENVIADO: 'text-bg-info',
            self.EstadoChoices.COMPLETADO: 'text-bg-success',
            self.EstadoChoices.CANCELADO: 'text-bg-secondary',
        }.get(self.estado, 'text-bg-secondary')

    def marcar_enviado(self):
        self.estado = self.EstadoChoices.ENVIADO
        self.fecha_envio = timezone.now()
        self.save(update_fields=['estado', 'fecha_envio'])

    def marcar_completado(self):
        self.estado = self.EstadoChoices.COMPLETADO
        self.save(update_fields=['estado'])

    def __str__(self):
        return f'{self.titulo} ({self.fecha_programada})'
