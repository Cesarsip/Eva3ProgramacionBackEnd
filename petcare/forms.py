"""Formularios HTML de PetCare con estilos Bootstrap 5."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction

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


class EstiloPetCareMixin:
    """Aplica clases de Bootstrap a todos los widgets del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')
            if campo.required:
                widget.attrs.setdefault('required', 'required')


class FechaHoraLocalInput(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, attrs=None, format=None):
        attrs = attrs or {}
        attrs.setdefault('class', 'form-control')
        super().__init__(attrs=attrs, format=format or '%Y-%m-%dT%H:%M')


class LoginForm(EstiloPetCareMixin, AuthenticationForm):
    username = forms.CharField(
        label='Usuario o correo',
        widget=forms.TextInput(attrs={'placeholder': 'usuario@petcare.cl', 'autofocus': True}),
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
    )


class RegistroTutorForm(EstiloPetCareMixin, UserCreationForm):
    """Registro público: crea el usuario Tutor y su ficha de contacto."""

    first_name = forms.CharField(label='Nombres', max_length=150)
    last_name = forms.CharField(label='Apellidos', max_length=150)
    email = forms.EmailField(label='Correo electrónico')
    rut = forms.CharField(label='RUT', max_length=20)
    telefono = forms.CharField(label='Teléfono', max_length=25)
    direccion = forms.CharField(
        label='Dirección',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Calle, número, comuna'}),
    )

    class Meta:
        model = Usuario
        fields = [
            'username', 'first_name', 'last_name', 'email', 'rut',
            'telefono', 'direccion',
        ]

    def clean_email(self):
        email = self.cleaned_data['email']
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ese correo ya está registrado.')
        if Tutor.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ese correo ya está registrado como tutor.')
        return email

    def clean_rut(self):
        rut = self.cleaned_data['rut']
        if Tutor.objects.filter(rut__iexact=rut).exists():
            raise forms.ValidationError('Ese RUT ya está registrado.')
        return rut

    @transaction.atomic
    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = Usuario.RolChoices.TUTOR
        usuario.email = self.cleaned_data['email']
        usuario.rut = self.cleaned_data['rut']
        usuario.telefono = self.cleaned_data['telefono']
        if commit:
            usuario.save()
            Tutor.objects.create(
                usuario=usuario,
                nombres=self.cleaned_data['first_name'],
                apellidos=self.cleaned_data['last_name'],
                rut=self.cleaned_data['rut'],
                email=self.cleaned_data['email'],
                telefono=self.cleaned_data['telefono'],
                direccion=self.cleaned_data.get('direccion', ''),
            )
        return usuario


class TutorForm(EstiloPetCareMixin, forms.ModelForm):
    class Meta:
        model = Tutor
        fields = ['nombres', 'apellidos', 'rut', 'email', 'telefono', 'direccion', 'activo']
        widgets = {
            'direccion': forms.TextInput(attrs={'placeholder': 'Calle, número, comuna'}),
        }


class MascotaForm(EstiloPetCareMixin, forms.ModelForm):
    class Meta:
        model = Mascota
        fields = [
            'tutor', 'nombre', 'especie', 'raza', 'sexo', 'fecha_nacimiento',
            'peso_kg', 'microchip', 'color', 'observaciones', 'activo',
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
            'microchip': forms.TextInput(attrs={'placeholder': 'Opcional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_nacimiento'].input_formats = ['%Y-%m-%d']
        self.fields['tutor'].queryset = Tutor.objects.order_by('apellidos', 'nombres')


class ProfesionalForm(EstiloPetCareMixin, forms.ModelForm):
    class Meta:
        model = Profesional
        fields = [
            'nombres', 'apellidos', 'especialidad', 'registro_profesional',
            'email', 'telefono', 'activo',
        ]


class HorarioAtencionForm(EstiloPetCareMixin, forms.ModelForm):
    class Meta:
        model = HorarioAtencion
        fields = ['profesional', 'dia_semana', 'hora_inicio', 'hora_fin', 'activo']
        widgets = {
            'hora_inicio': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'hora_fin': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hora_inicio'].input_formats = ['%H:%M']
        self.fields['hora_fin'].input_formats = ['%H:%M']

    def clean(self):
        cleaned = super().clean()
        profesional = cleaned.get('profesional')
        dia = cleaned.get('dia_semana')
        inicio = cleaned.get('hora_inicio')
        fin = cleaned.get('hora_fin')
        if profesional and dia is not None and inicio and fin and inicio < fin:
            existentes = HorarioAtencion.objects.filter(
                profesional=profesional,
                dia_semana=dia,
                activo=True,
            ).exclude(pk=self.instance.pk)
            for horario in existentes:
                if inicio < horario.hora_fin and fin > horario.hora_inicio:
                    self.add_error(
                        'hora_inicio',
                        f'Se solapa con el bloque {horario.hora_inicio:%H:%M}-{horario.hora_fin:%H:%M}.',
                    )
                    break
        return cleaned


class CitaForm(EstiloPetCareMixin, forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['mascota', 'profesional', 'fecha', 'hora', 'motivo', 'notas']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'hora': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'motivo': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Motivo de la consulta'}),
            'notas': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Notas internas (opcional)'}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.fields['fecha'].input_formats = ['%Y-%m-%d']
        self.fields['hora'].input_formats = ['%H:%M']
        self.fields['profesional'].queryset = Profesional.objects.filter(activo=True).order_by(
            'apellidos', 'nombres'
        )

        mascotas = Mascota.objects.filter(activo=True).select_related('tutor')
        if usuario and not usuario.puede_gestionar_clinica:
            mascotas = mascotas.filter(tutor__usuario=usuario)
        self.fields['mascota'].queryset = mascotas.order_by('nombre')


class FichaClinicaForm(EstiloPetCareMixin, forms.ModelForm):
    class Meta:
        model = FichaClinica
        fields = [
            'mascota', 'cita', 'profesional', 'fecha', 'motivo_consulta',
            'diagnostico', 'tratamiento', 'observaciones', 'peso_kg',
            'temperatura', 'frecuencia_cardiaca', 'proxima_revision',
        ]
        widgets = {
            'fecha': FechaHoraLocalInput(format='%Y-%m-%dT%H:%M'),
            'proxima_revision': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'motivo_consulta': forms.Textarea(attrs={'rows': 3}),
            'diagnostico': forms.Textarea(attrs={'rows': 4}),
            'tratamiento': forms.Textarea(attrs={'rows': 4}),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].input_formats = [
            '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
        ]
        self.fields['proxima_revision'].input_formats = ['%Y-%m-%d']
        self.fields['mascota'].queryset = Mascota.objects.filter(activo=True).select_related('tutor')
        self.fields['profesional'].queryset = Profesional.objects.filter(activo=True)
        self.fields['cita'].queryset = Cita.objects.select_related('mascota', 'profesional').order_by(
            '-fecha', '-hora'
        )


class RecetaForm(EstiloPetCareMixin, forms.ModelForm):
    class Meta:
        model = Receta
        fields = ['medicamento', 'dosis', 'frecuencia', 'duracion', 'indicaciones']
        widgets = {'indicaciones': forms.Textarea(attrs={'rows': 2})}


class ExamenForm(EstiloPetCareMixin, forms.ModelForm):
    class Meta:
        model = Examen
        fields = ['tipo', 'resultado', 'fecha', 'archivo_url', 'observaciones']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'resultado': forms.Textarea(attrs={'rows': 2}),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].input_formats = ['%Y-%m-%d']


class VacunaForm(EstiloPetCareMixin, forms.ModelForm):
    class Meta:
        model = Vacuna
        fields = [
            'mascota', 'nombre', 'fecha_aplicacion', 'proxima_dosis',
            'profesional', 'lote', 'observaciones',
        ]
        widgets = {
            'fecha_aplicacion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'proxima_dosis': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_aplicacion'].input_formats = ['%Y-%m-%d']
        self.fields['proxima_dosis'].input_formats = ['%Y-%m-%d']
        self.fields['mascota'].queryset = Mascota.objects.filter(activo=True).select_related('tutor')
        self.fields['profesional'].queryset = Profesional.objects.filter(activo=True)


class RecordatorioForm(EstiloPetCareMixin, forms.ModelForm):
    class Meta:
        model = Recordatorio
        fields = [
            'mascota', 'tipo', 'titulo', 'descripcion', 'fecha_programada',
            'estado', 'vacuna', 'ficha', 'notas',
        ]
        widgets = {
            'fecha_programada': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'notas': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_programada'].input_formats = ['%Y-%m-%d']
        self.fields['mascota'].queryset = Mascota.objects.filter(activo=True).select_related('tutor')
        self.fields['vacuna'].queryset = Vacuna.objects.select_related('mascota')
        self.fields['ficha'].queryset = FichaClinica.objects.select_related('mascota')
