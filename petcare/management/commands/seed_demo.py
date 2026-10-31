"""
Carga datos de demostración para PetCare.

Uso:
    python manage.py seed_demo

Es idempotente: se puede ejecutar varias veces sin duplicar registros.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from petcare.models import (
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


class Command(BaseCommand):
    help = 'Crea usuarios, profesionales, tutores, mascotas y registros clínicos de demostración.'

    def _proximo_dia_habil(self, dias):
        fecha = timezone.localdate() + timedelta(days=dias)
        while fecha.weekday() > 5:  # domingo cerrado
            fecha += timedelta(days=1)
        return fecha

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Creando datos de demostración de PetCare...')

        # -----------------------------------------------------------------
        # Usuarios
        # -----------------------------------------------------------------
        admin, _ = Usuario.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@petcare.cl',
                'first_name': 'Administrador',
                'last_name': 'PetCare',
                'rol': Usuario.RolChoices.ADMINISTRADOR,
                'is_staff': True,
                'is_superuser': True,
                'rut': '11.111.111-1',
                'telefono': '+56 9 1111 1111',
            },
        )
        if not admin.is_superuser:
            admin.is_staff = True
            admin.is_superuser = True
            admin.rol = Usuario.RolChoices.ADMINISTRADOR
            admin.save()
        if not admin.check_password('AdminPetCare2026!'):
            admin.set_password('AdminPetCare2026!')
            admin.save(update_fields=['password'])

        vet_user, _ = Usuario.objects.get_or_create(
            username='veterinario',
            defaults={
                'email': 'camila.rojas@petcare.cl',
                'first_name': 'Camila',
                'last_name': 'Rojas',
                'rol': Usuario.RolChoices.VETERINARIO,
                'rut': '22.222.222-2',
                'telefono': '+56 9 2222 2222',
            },
        )
        if not vet_user.check_password('VetPetCare2026!'):
            vet_user.set_password('VetPetCare2026!')
            vet_user.save(update_fields=['password'])

        recepcion, _ = Usuario.objects.get_or_create(
            username='recepcion',
            defaults={
                'email': 'recepcion@petcare.cl',
                'first_name': 'Valentina',
                'last_name': 'Soto',
                'rol': Usuario.RolChoices.RECEPCIONISTA,
                'rut': '33.333.333-3',
                'telefono': '+56 9 3333 3333',
            },
        )
        if not recepcion.check_password('Recepcion2026!'):
            recepcion.set_password('Recepcion2026!')
            recepcion.save(update_fields=['password'])

        tutor_user, _ = Usuario.objects.get_or_create(
            username='tutor',
            defaults={
                'email': 'maria.gonzalez@example.cl',
                'first_name': 'María',
                'last_name': 'González',
                'rol': Usuario.RolChoices.TUTOR,
                'rut': '12.345.678-9',
                'telefono': '+56 9 4444 4444',
            },
        )
        if not tutor_user.check_password('TutorPetCare2026!'):
            tutor_user.set_password('TutorPetCare2026!')
            tutor_user.save(update_fields=['password'])

        # -----------------------------------------------------------------
        # Profesionales y horarios
        # -----------------------------------------------------------------
        camila, _ = Profesional.objects.get_or_create(
            registro_profesional='VET-001',
            defaults={
                'usuario': vet_user,
                'nombres': 'Camila',
                'apellidos': 'Rojas',
                'especialidad': 'Medicina General',
                'email': 'camila.rojas@petcare.cl',
                'telefono': '+56 9 2222 2222',
            },
        )
        sebastian, _ = Profesional.objects.get_or_create(
            registro_profesional='VET-002',
            defaults={
                'nombres': 'Sebastián',
                'apellidos': 'Muñoz',
                'especialidad': 'Cirugía y Traumatología',
                'email': 'sebastian.munoz@petcare.cl',
                'telefono': '+56 9 5555 5555',
            },
        )

        for profesional in (camila, sebastian):
            for dia in range(0, 6):  # lunes a sábado
                HorarioAtencion.objects.get_or_create(
                    profesional=profesional,
                    dia_semana=dia,
                    hora_inicio='09:00',
                    defaults={'hora_fin': '13:00'},
                )
                if dia < 5:
                    HorarioAtencion.objects.get_or_create(
                        profesional=profesional,
                        dia_semana=dia,
                        hora_inicio='14:00',
                        defaults={'hora_fin': '18:00'},
                    )

        # -----------------------------------------------------------------
        # Tutores y mascotas
        # -----------------------------------------------------------------
        maria, _ = Tutor.objects.get_or_create(
            rut='12.345.678-9',
            defaults={
                'usuario': tutor_user,
                'nombres': 'María',
                'apellidos': 'González',
                'email': 'maria.gonzalez@example.cl',
                'telefono': '+56 9 4444 4444',
                'direccion': 'Av. Siempre Viva 123, Santiago',
            },
        )
        pedro, _ = Tutor.objects.get_or_create(
            rut='98.765.432-1',
            defaults={
                'nombres': 'Pedro',
                'apellidos': 'Silva',
                'email': 'pedro.silva@example.cl',
                'telefono': '+56 9 6666 6666',
                'direccion': 'Los Aromos 456, Ñuñoa',
            },
        )
        ana, _ = Tutor.objects.get_or_create(
            rut='15.678.912-3',
            defaults={
                'nombres': 'Ana',
                'apellidos': 'Torres',
                'email': 'ana.torres@example.cl',
                'telefono': '+56 9 7777 7777',
                'direccion': 'Pasaje El Roble 789, Maipú',
            },
        )

        luna, _ = Mascota.objects.get_or_create(
            microchip='CHIP-LUNA-001',
            defaults={
                'tutor': maria,
                'nombre': 'Luna',
                'especie': Mascota.EspecieChoices.PERRO,
                'raza': 'Golden Retriever',
                'sexo': Mascota.SexoChoices.HEMBRA,
                'fecha_nacimiento': timezone.localdate() - timedelta(days=365 * 3),
                'peso_kg': '28.50',
                'color': 'Dorado',
                'observaciones': 'Paciente sociable. Alergia leve a pulgas.',
            },
        )
        milo, _ = Mascota.objects.get_or_create(
            microchip='CHIP-MILO-002',
            defaults={
                'tutor': pedro,
                'nombre': 'Milo',
                'especie': Mascota.EspecieChoices.GATO,
                'raza': 'Siamés',
                'sexo': Mascota.SexoChoices.MACHO,
                'fecha_nacimiento': timezone.localdate() - timedelta(days=365 * 2),
                'peso_kg': '4.20',
                'color': 'Crema con puntas oscuras',
            },
        )
        rocky, _ = Mascota.objects.get_or_create(
            microchip='CHIP-ROCKY-003',
            defaults={
                'tutor': ana,
                'nombre': 'Rocky',
                'especie': Mascota.EspecieChoices.PERRO,
                'raza': 'Bulldog Francés',
                'sexo': Mascota.SexoChoices.MACHO,
                'fecha_nacimiento': timezone.localdate() - timedelta(days=365 * 5),
                'peso_kg': '12.80',
                'color': 'Atigrado',
                'observaciones': 'Displasia de cadera en seguimiento.',
            },
        )

        # -----------------------------------------------------------------
        # Citas
        # -----------------------------------------------------------------
        Cita.objects.get_or_create(
            profesional=camila,
            fecha=self._proximo_dia_habil(1),
            hora='10:00',
            defaults={
                'mascota': luna,
                'motivo': 'Control dermatológico y revisión de alergia.',
                'estado': Cita.EstadoChoices.CONFIRMADA,
            },
        )
        Cita.objects.get_or_create(
            profesional=sebastian,
            fecha=self._proximo_dia_habil(1),
            hora='11:00',
            defaults={
                'mascota': milo,
                'motivo': 'Vacunación anual y control general.',
                'estado': Cita.EstadoChoices.PROGRAMADA,
            },
        )
        Cita.objects.get_or_create(
            profesional=camila,
            fecha=self._proximo_dia_habil(2),
            hora='09:30',
            defaults={
                'mascota': rocky,
                'motivo': 'Cojera leve del miembro posterior derecho.',
                'estado': Cita.EstadoChoices.PROGRAMADA,
            },
        )

        # -----------------------------------------------------------------
        # Fichas clínicas, recetas y exámenes
        # -----------------------------------------------------------------
        ficha_luna, creada = FichaClinica.objects.get_or_create(
            mascota=luna,
            profesional=camila,
            motivo_consulta='Control anual y revisión de alergia.',
            defaults={
                'diagnostico': 'Dermatitis alérgica leve. Estado general conservado.',
                'tratamiento': 'Baños medicados cada 7 días y control de pulgas. Revisión en 3 semanas.',
                'observaciones': 'Sin lesiones secundarias. Se refuerza antiparasitario externo.',
                'peso_kg': '28.50',
                'temperatura': '38.4',
                'frecuencia_cardiaca': 92,
                'proxima_revision': timezone.localdate() + timedelta(days=21),
            },
        )
        if creada:
            Receta.objects.create(
                ficha=ficha_luna,
                medicamento='Prednisona 5 mg',
                dosis='1 comprimido',
                frecuencia='Cada 24 horas',
                duracion='5 días',
                indicaciones='Administrar con alimento. Suspender si presenta vómitos.',
            )
            Examen.objects.create(
                ficha=ficha_luna,
                tipo='Hemograma completo',
                resultado='Leve eosinofilia compatible con proceso alérgico.',
                fecha=timezone.localdate(),
                observaciones='Sin alteraciones hematológicas mayores.',
            )

        ficha_milo, creada = FichaClinica.objects.get_or_create(
            mascota=milo,
            profesional=sebastian,
            motivo_consulta='Control general previo a vacunación.',
            defaults={
                'diagnostico': 'Paciente sano. Vacunación al día.',
                'tratamiento': 'Aplicación de vacuna triple felina. Control en 12 meses.',
                'peso_kg': '4.20',
                'temperatura': '38.1',
                'frecuencia_cardiaca': 160,
                'proxima_revision': timezone.localdate() + timedelta(days=365),
            },
        )
        if creada:
            Examen.objects.create(
                ficha=ficha_milo,
                tipo='Perfil bioquímico',
                resultado='Valores dentro de rangos normales.',
                fecha=timezone.localdate(),
            )

        # -----------------------------------------------------------------
        # Vacunas (generan recordatorios por señal)
        # -----------------------------------------------------------------
        Vacuna.objects.get_or_create(
            mascota=luna,
            nombre='Rabia',
            fecha_aplicacion=timezone.localdate() - timedelta(days=300),
            defaults={
                'proxima_dosis': timezone.localdate() + timedelta(days=15),
                'profesional': camila,
                'lote': 'RAB-2026-041',
            },
        )
        Vacuna.objects.get_or_create(
            mascota=milo,
            nombre='Triple felina',
            fecha_aplicacion=timezone.localdate() - timedelta(days=200),
            defaults={
                'proxima_dosis': timezone.localdate() + timedelta(days=30),
                'profesional': sebastian,
                'lote': 'TF-2026-018',
            },
        )
        Vacuna.objects.get_or_create(
            mascota=rocky,
            nombre='Óctuple canina',
            fecha_aplicacion=timezone.localdate() - timedelta(days=100),
            defaults={
                'proxima_dosis': timezone.localdate() + timedelta(days=265),
                'profesional': camila,
                'lote': 'OCT-2026-007',
            },
        )

        Recordatorio.objects.get_or_create(
            mascota=rocky,
            titulo='Control post-operatorio de cadera',
            defaults={
                'tipo': Recordatorio.TipoChoices.CONTROL,
                'descripcion': 'Evaluar evolución de la displasia y ajustar tratamiento.',
                'fecha_programada': timezone.localdate() + timedelta(days=7),
                'estado': Recordatorio.EstadoChoices.PENDIENTE,
            },
        )

        self.stdout.write(self.style.SUCCESS('Datos de demostración cargados.'))
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Credenciales de prueba'))
        self.stdout.write('  Administrador : admin / AdminPetCare2026!')
        self.stdout.write('  Veterinario   : veterinario / VetPetCare2026!')
        self.stdout.write('  Recepcionista : recepcion / Recepcion2026!')
        self.stdout.write('  Tutor         : tutor / TutorPetCare2026!')
