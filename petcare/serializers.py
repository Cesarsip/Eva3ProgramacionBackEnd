"""
Serializadores de la API REST de PetCare.

Incluyen validaciones de negocio reutilizando el método ``full_clean()`` de
los modelos (disponibilidad, choques de horario, coherencia clínica, etc.).
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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


def _errores_modelo(exc):
    """Convierte un ValidationError de Django al formato de DRF."""
    if hasattr(exc, 'message_dict'):
        errores = {}
        for campo, mensajes in exc.message_dict.items():
            clave = 'non_field_errors' if campo == '__all__' else campo
            errores[clave] = mensajes
        return errores
    return exc.messages


def _validar_instancia(instancia):
    """Ejecuta las validaciones del modelo y las traduce a errores DRF."""
    try:
        instancia.full_clean()
    except DjangoValidationError as exc:
        raise serializers.ValidationError(_errores_modelo(exc)) from exc


# =====================================================================
# AUTENTICACIÓN Y USUARIOS
# =====================================================================
class UsuarioSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'nombre_completo', 'rol', 'rol_display', 'rut', 'telefono',
            'is_active', 'is_staff', 'password',
        ]
        read_only_fields = ['is_staff']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        usuario = Usuario(**validated_data)
        if password:
            usuario.set_password(password)
        else:
            usuario.set_unusable_password()
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UsuarioResumenSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'nombre_completo', 'email', 'rol', 'rol_display']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Agrega claims personalizados al JWT (rol, nombre y privilegios) y permite
    iniciar sesión indistintamente con nombre de usuario o correo electrónico.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        token['rol'] = user.rol
        token['rol_display'] = user.get_rol_display()
        token['nombre_completo'] = user.nombre_completo
        token['is_staff'] = user.is_staff
        return token

    def validate(self, attrs):
        identificador = attrs.get('username', '')
        if identificador and '@' in identificador:
            usuario = Usuario.objects.filter(email__iexact=identificador).first()
            if usuario:
                attrs['username'] = usuario.get_username()
        data = super().validate(attrs)
        data['usuario'] = UsuarioSerializer(self.user).data
        return data


class RegistroTutorSerializer(serializers.Serializer):
    """Registro público de un tutor y creación de su perfil de cliente."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    rut = serializers.CharField(max_length=20)
    telefono = serializers.CharField(max_length=25)
    direccion = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_username(self, value):
        if Usuario.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('Ese nombre de usuario ya está en uso.')
        return value

    def validate_email(self, value):
        if Usuario.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Ese correo ya está registrado.')
        if Tutor.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Ese correo ya está registrado como tutor.')
        return value

    def validate_rut(self, value):
        if Tutor.objects.filter(rut__iexact=value).exists():
            raise serializers.ValidationError('Ese RUT ya está registrado.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        nombres = validated_data.pop('first_name')
        apellidos = validated_data.pop('last_name')
        rut = validated_data.pop('rut')
        telefono = validated_data.pop('telefono')
        direccion = validated_data.pop('direccion', '')

        usuario = Usuario.objects.create_user(
            rol=Usuario.RolChoices.TUTOR,
            password=password,
            first_name=nombres,
            last_name=apellidos,
            rut=rut,
            telefono=telefono,
            **validated_data,
        )
        tutor = Tutor.objects.create(
            usuario=usuario,
            nombres=nombres,
            apellidos=apellidos,
            rut=rut,
            email=usuario.email,
            telefono=telefono,
            direccion=direccion,
        )
        return tutor


# =====================================================================
# TUTORES Y MASCOTAS
# =====================================================================
class TutorSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    total_mascotas = serializers.IntegerField(read_only=True)
    usuario_detalle = UsuarioResumenSerializer(source='usuario', read_only=True)

    class Meta:
        model = Tutor
        fields = [
            'id', 'usuario', 'usuario_detalle', 'nombres', 'apellidos',
            'nombre_completo', 'rut', 'email', 'telefono', 'direccion',
            'activo', 'fecha_registro', 'total_mascotas',
        ]
        read_only_fields = ['fecha_registro']

    def validate(self, attrs):
        instancia = self.instance or Tutor()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        _validar_instancia(instancia)
        return attrs


class MascotaSerializer(serializers.ModelSerializer):
    tutor_nombre = serializers.CharField(source='tutor.nombre_completo', read_only=True)
    especie_display = serializers.CharField(source='get_especie_display', read_only=True)
    sexo_display = serializers.CharField(source='get_sexo_display', read_only=True)
    edad = serializers.CharField(read_only=True)

    class Meta:
        model = Mascota
        fields = [
            'id', 'tutor', 'tutor_nombre', 'nombre', 'especie', 'especie_display',
            'raza', 'sexo', 'sexo_display', 'fecha_nacimiento', 'peso_kg',
            'microchip', 'color', 'observaciones', 'activo', 'edad',
            'fecha_registro',
        ]
        read_only_fields = ['fecha_registro']

    def validate(self, attrs):
        if 'microchip' in attrs and not attrs['microchip']:
            attrs['microchip'] = None
        instancia = self.instance or Mascota()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        _validar_instancia(instancia)
        return attrs


# =====================================================================
# PROFESIONALES Y HORARIOS
# =====================================================================
class ProfesionalSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    usuario_detalle = UsuarioResumenSerializer(source='usuario', read_only=True)

    class Meta:
        model = Profesional
        fields = [
            'id', 'usuario', 'usuario_detalle', 'nombres', 'apellidos',
            'nombre_completo', 'especialidad', 'registro_profesional',
            'email', 'telefono', 'activo', 'fecha_registro',
        ]
        read_only_fields = ['fecha_registro']

    def validate(self, attrs):
        instancia = self.instance or Profesional()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        _validar_instancia(instancia)
        return attrs


class HorarioAtencionSerializer(serializers.ModelSerializer):
    profesional_nombre = serializers.CharField(source='profesional.nombre_completo', read_only=True)
    dia_display = serializers.CharField(source='get_dia_semana_display', read_only=True)

    class Meta:
        model = HorarioAtencion
        fields = [
            'id', 'profesional', 'profesional_nombre', 'dia_semana',
            'dia_display', 'hora_inicio', 'hora_fin', 'activo',
        ]

    def validate(self, attrs):
        def valor(campo):
            return attrs.get(campo, getattr(self.instance, campo, None))

        profesional = valor('profesional')
        dia = valor('dia_semana')
        inicio = valor('hora_inicio')
        fin = valor('hora_fin')

        if inicio and fin and inicio >= fin:
            raise serializers.ValidationError(
                {'hora_fin': 'La hora de término debe ser posterior a la de inicio.'}
            )

        if profesional and dia is not None and inicio and fin:
            existentes = HorarioAtencion.objects.filter(
                profesional=profesional,
                dia_semana=dia,
                activo=True,
            )
            if self.instance:
                existentes = existentes.exclude(pk=self.instance.pk)
            for horario in existentes:
                if inicio < horario.hora_fin and fin > horario.hora_inicio:
                    raise serializers.ValidationError({
                        'hora_inicio': (
                            'El horario se solapa con el bloque '
                            f'{horario.hora_inicio:%H:%M}-{horario.hora_fin:%H:%M}.'
                        )
                    })

        instancia = self.instance or HorarioAtencion()
        for campo, dato in attrs.items():
            setattr(instancia, campo, dato)
        _validar_instancia(instancia)
        return attrs


# =====================================================================
# CITAS
# =====================================================================
class CitaSerializer(serializers.ModelSerializer):
    mascota_nombre = serializers.CharField(source='mascota.nombre', read_only=True)
    tutor_nombre = serializers.CharField(source='mascota.tutor.nombre_completo', read_only=True)
    profesional_nombre = serializers.CharField(source='profesional.nombre_completo', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    badge_class = serializers.CharField(read_only=True)

    class Meta:
        model = Cita
        fields = [
            'id', 'mascota', 'mascota_nombre', 'tutor_nombre', 'profesional',
            'profesional_nombre', 'fecha', 'hora', 'motivo', 'estado',
            'estado_display', 'badge_class', 'notas', 'fecha_creacion',
            'fecha_actualizacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        instancia = self.instance or Cita()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)

        if user and user.is_authenticated and not user.puede_gestionar_clinica:
            if self.instance is None:
                # Un tutor no puede crear una cita ya confirmada o atendida.
                attrs['estado'] = Cita.EstadoChoices.PROGRAMADA
                instancia.estado = attrs['estado']
            if instancia.mascota_id and instancia.mascota.tutor.usuario_id != user.id:
                raise serializers.ValidationError({
                    'mascota': 'Solo puedes agendar citas para tus propias mascotas.'
                })

        if instancia.estado in (
            Cita.EstadoChoices.PROGRAMADA,
            Cita.EstadoChoices.CONFIRMADA,
        ):
            _validar_instancia(instancia)
        return attrs


# =====================================================================
# FICHA CLÍNICA, RECETAS Y EXÁMENES
# =====================================================================
class RecetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receta
        fields = ['id', 'medicamento', 'dosis', 'frecuencia', 'duracion', 'indicaciones']
        read_only_fields = ['id']


class ExamenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Examen
        fields = ['id', 'tipo', 'resultado', 'fecha', 'archivo_url', 'observaciones']
        read_only_fields = ['id']


class FichaClinicaSerializer(serializers.ModelSerializer):
    mascota = serializers.PrimaryKeyRelatedField(
        queryset=Mascota.objects.all(), required=False
    )
    profesional = serializers.PrimaryKeyRelatedField(
        queryset=Profesional.objects.all(), required=False
    )
    mascota_nombre = serializers.CharField(source='mascota.nombre', read_only=True)
    profesional_nombre = serializers.CharField(source='profesional.nombre_completo', read_only=True)
    recetas = RecetaSerializer(many=True, required=False)
    examenes = ExamenSerializer(many=True, required=False)

    class Meta:
        model = FichaClinica
        fields = [
            'id', 'mascota', 'mascota_nombre', 'cita', 'profesional',
            'profesional_nombre', 'fecha', 'motivo_consulta', 'diagnostico',
            'tratamiento', 'observaciones', 'peso_kg', 'temperatura',
            'frecuencia_cardiaca', 'proxima_revision', 'recetas', 'examenes',
            'fecha_creacion', 'fecha_actualizacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']

    def validate(self, attrs):
        instancia = self.instance or FichaClinica()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)

        if instancia.cita_id:
            if not instancia.mascota_id:
                instancia.mascota_id = instancia.cita.mascota_id
            if not instancia.profesional_id:
                instancia.profesional_id = instancia.cita.profesional_id
        _validar_instancia(instancia)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        recetas = validated_data.pop('recetas', [])
        examenes = validated_data.pop('examenes', [])
        ficha = FichaClinica.objects.create(**validated_data)
        for receta in recetas:
            receta.pop('ficha', None)
            Receta.objects.create(ficha=ficha, **receta)
        for examen in examenes:
            examen.pop('ficha', None)
            Examen.objects.create(ficha=ficha, **examen)
        return ficha

    @transaction.atomic
    def update(self, instance, validated_data):
        recetas = validated_data.pop('recetas', None)
        examenes = validated_data.pop('examenes', None)
        ficha = super().update(instance, validated_data)
        if recetas is not None:
            ficha.recetas.all().delete()
            for receta in recetas:
                receta.pop('ficha', None)
                Receta.objects.create(ficha=ficha, **receta)
        if examenes is not None:
            ficha.examenes.all().delete()
            for examen in examenes:
                examen.pop('ficha', None)
                Examen.objects.create(ficha=ficha, **examen)
        return ficha


# =====================================================================
# VACUNAS Y RECORDATORIOS
# =====================================================================
class VacunaSerializer(serializers.ModelSerializer):
    mascota_nombre = serializers.CharField(source='mascota.nombre', read_only=True)
    profesional_nombre = serializers.CharField(source='profesional.nombre_completo', read_only=True)

    class Meta:
        model = Vacuna
        fields = [
            'id', 'mascota', 'mascota_nombre', 'nombre', 'fecha_aplicacion',
            'proxima_dosis', 'profesional', 'profesional_nombre', 'lote',
            'observaciones',
        ]

    def validate(self, attrs):
        instancia = self.instance or Vacuna()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        _validar_instancia(instancia)
        return attrs


class RecordatorioSerializer(serializers.ModelSerializer):
    mascota_nombre = serializers.CharField(source='mascota.nombre', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    badge_class = serializers.CharField(read_only=True)

    class Meta:
        model = Recordatorio
        fields = [
            'id', 'mascota', 'mascota_nombre', 'tipo', 'tipo_display', 'titulo',
            'descripcion', 'fecha_programada', 'estado', 'estado_display',
            'badge_class', 'vacuna', 'ficha', 'notas', 'fecha_creacion',
            'fecha_envio',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_envio']

    def validate(self, attrs):
        instancia = self.instance or Recordatorio()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        _validar_instancia(instancia)
        return attrs
