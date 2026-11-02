"""Pruebas automáticas de las reglas de negocio y los permisos de PetCare."""
from datetime import time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from .models import (
    Cita,
    FichaClinica,
    HorarioAtencion,
    Mascota,
    Profesional,
    Recordatorio,
    Tutor,
    Usuario,
    Vacuna,
)


class BasePetCareTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user(
            username='admin_test',
            password='ClaveSegura123!',
            email='admin@test.cl',
            first_name='Admin',
            last_name='Test',
            rol=Usuario.RolChoices.ADMINISTRADOR,
            is_staff=True,
            is_superuser=True,
        )
        cls.vet_user = Usuario.objects.create_user(
            username='vet_test',
            password='ClaveSegura123!',
            email='vet@test.cl',
            first_name='Vet',
            last_name='Test',
            rol=Usuario.RolChoices.VETERINARIO,
        )
        cls.recepcion = Usuario.objects.create_user(
            username='recep_test',
            password='ClaveSegura123!',
            email='recepcion@test.cl',
            first_name='Recep',
            last_name='Test',
            rol=Usuario.RolChoices.RECEPCIONISTA,
        )
        cls.tutor_user = Usuario.objects.create_user(
            username='tutor_test',
            password='ClaveSegura123!',
            email='tutor@test.cl',
            first_name='Tutor',
            last_name='Test',
            rol=Usuario.RolChoices.TUTOR,
        )
        cls.otro_tutor_user = Usuario.objects.create_user(
            username='tutor_otro',
            password='ClaveSegura123!',
            email='otro@test.cl',
            first_name='Otro',
            last_name='Tutor',
            rol=Usuario.RolChoices.TUTOR,
        )

        cls.tutor = Tutor.objects.create(
            usuario=cls.tutor_user,
            nombres='Tutor',
            apellidos='Test',
            rut='11.111.111-1',
            email='tutor@test.cl',
            telefono='+56 9 1111 1111',
        )
        cls.otro_tutor = Tutor.objects.create(
            usuario=cls.otro_tutor_user,
            nombres='Otro',
            apellidos='Tutor',
            rut='22.222.222-2',
            email='otro@test.cl',
            telefono='+56 9 2222 2222',
        )

        cls.profesional = Profesional.objects.create(
            usuario=cls.vet_user,
            nombres='Camila',
            apellidos='Rojas',
            especialidad='Medicina General',
            registro_profesional='VET-TEST-1',
            email='camila@test.cl',
        )
        cls.profesional_sin_horario = Profesional.objects.create(
            nombres='Sin',
            apellidos='Horario',
            especialidad='Cardiología',
            registro_profesional='VET-TEST-2',
            email='sinhorario@test.cl',
        )
        for dia in range(7):
            HorarioAtencion.objects.create(
                profesional=cls.profesional,
                dia_semana=dia,
                hora_inicio=time(9, 0),
                hora_fin=time(18, 0),
            )

        cls.mascota = Mascota.objects.create(
            tutor=cls.tutor,
            nombre='Luna',
            especie=Mascota.EspecieChoices.PERRO,
            raza='Golden',
            sexo=Mascota.SexoChoices.HEMBRA,
            fecha_nacimiento=timezone.localdate() - timedelta(days=900),
            peso_kg='25.00',
            microchip='TEST-LUNA-1',
        )
        cls.mascota_otro = Mascota.objects.create(
            tutor=cls.otro_tutor,
            nombre='Milo',
            especie=Mascota.EspecieChoices.GATO,
            sexo=Mascota.SexoChoices.MACHO,
            fecha_nacimiento=timezone.localdate() - timedelta(days=400),
            microchip='TEST-MILO-2',
        )

    def fecha_futura(self):
        return timezone.localdate() + timedelta(days=1)


class CitaBusinessRulesTest(BasePetCareTest):
    def test_cita_valida_dentro_del_horario(self):
        cita = Cita.objects.create(
            mascota=self.mascota,
            profesional=self.profesional,
            fecha=self.fecha_futura(),
            hora=time(10, 0),
            motivo='Control general',
        )
        self.assertEqual(cita.estado, Cita.EstadoChoices.PROGRAMADA)

    def test_rechaza_fecha_pasada(self):
        with self.assertRaises(ValidationError):
            Cita.objects.create(
                mascota=self.mascota,
                profesional=self.profesional,
                fecha=timezone.localdate() - timedelta(days=1),
                hora=time(10, 0),
                motivo='Control',
            )

    def test_rechaza_hora_fuera_de_horario(self):
        with self.assertRaises(ValidationError):
            Cita.objects.create(
                mascota=self.mascota,
                profesional=self.profesional,
                fecha=self.fecha_futura(),
                hora=time(8, 0),
                motivo='Control',
            )

    def test_rechaza_profesional_sin_horario(self):
        with self.assertRaises(ValidationError):
            Cita.objects.create(
                mascota=self.mascota,
                profesional=self.profesional_sin_horario,
                fecha=self.fecha_futura(),
                hora=time(10, 0),
                motivo='Control',
            )

    def test_rechaza_choque_de_horario_del_profesional(self):
        Cita.objects.create(
            mascota=self.mascota,
            profesional=self.profesional,
            fecha=self.fecha_futura(),
            hora=time(10, 0),
            motivo='Primera cita',
        )
        with self.assertRaises(ValidationError):
            Cita.objects.create(
                mascota=self.mascota_otro,
                profesional=self.profesional,
                fecha=self.fecha_futura(),
                hora=time(10, 0),
                motivo='Cita duplicada',
            )

    def test_rechaza_choque_de_horario_de_la_mascota(self):
        segundo_profesional = Profesional.objects.create(
            nombres='Otro',
            apellidos='Veterinario',
            especialidad='Dermatología',
            registro_profesional='VET-TEST-3',
            email='otro@test.cl',
        )
        HorarioAtencion.objects.create(
            profesional=segundo_profesional,
            dia_semana=self.fecha_futura().weekday(),
            hora_inicio=time(9, 0),
            hora_fin=time(18, 0),
        )
        Cita.objects.create(
            mascota=self.mascota,
            profesional=self.profesional,
            fecha=self.fecha_futura(),
            hora=time(11, 0),
            motivo='Primera cita',
        )
        with self.assertRaises(ValidationError):
            Cita.objects.create(
                mascota=self.mascota,
                profesional=segundo_profesional,
                fecha=self.fecha_futura(),
                hora=time(11, 0),
                motivo='Cita duplicada de la mascota',
            )

    def test_cancelar_libera_el_horario(self):
        fecha = self.fecha_futura()
        cita = Cita.objects.create(
            mascota=self.mascota,
            profesional=self.profesional,
            fecha=fecha,
            hora=time(12, 0),
            motivo='Control',
        )
        cita.cancelar()
        self.assertEqual(cita.estado, Cita.EstadoChoices.CANCELADA)
        # El mismo bloque puede reutilizarse porque la cita cancelada ya no está activa.
        nueva = Cita.objects.create(
            mascota=self.mascota_otro,
            profesional=self.profesional,
            fecha=fecha,
            hora=time(12, 0),
            motivo='Reagendamiento',
        )
        self.assertEqual(nueva.estado, Cita.EstadoChoices.PROGRAMADA)


class RecordatoriosAutomaticosTest(BasePetCareTest):
    def test_vacuna_con_proxima_dosis_crea_recordatorio(self):
        proxima = timezone.localdate() + timedelta(days=20)
        vacuna = Vacuna.objects.create(
            mascota=self.mascota,
            nombre='Rabia',
            fecha_aplicacion=timezone.localdate(),
            proxima_dosis=proxima,
            profesional=self.profesional,
        )
        recordatorio = Recordatorio.objects.get(vacuna=vacuna)
        self.assertEqual(recordatorio.tipo, Recordatorio.TipoChoices.VACUNA)
        self.assertEqual(recordatorio.fecha_programada, proxima)
        self.assertEqual(recordatorio.estado, Recordatorio.EstadoChoices.PENDIENTE)

    def test_cambio_de_proxima_dosis_actualiza_recordatorio(self):
        vacuna = Vacuna.objects.create(
            mascota=self.mascota,
            nombre='Rabia',
            fecha_aplicacion=timezone.localdate(),
            proxima_dosis=timezone.localdate() + timedelta(days=20),
            profesional=self.profesional,
        )
        recordatorio = Recordatorio.objects.get(vacuna=vacuna)
        recordatorio.marcar_enviado()

        nueva_fecha = timezone.localdate() + timedelta(days=40)
        vacuna.proxima_dosis = nueva_fecha
        vacuna.save()

        recordatorio.refresh_from_db()
        self.assertEqual(recordatorio.fecha_programada, nueva_fecha)
        self.assertEqual(recordatorio.estado, Recordatorio.EstadoChoices.PENDIENTE)
        self.assertIsNone(recordatorio.fecha_envio)

    def test_sin_proxima_dosis_elimina_aviso_pendiente(self):
        vacuna = Vacuna.objects.create(
            mascota=self.mascota,
            nombre='Rabia',
            fecha_aplicacion=timezone.localdate(),
            proxima_dosis=timezone.localdate() + timedelta(days=20),
            profesional=self.profesional,
        )
        vacuna.proxima_dosis = None
        vacuna.save()
        self.assertFalse(Recordatorio.objects.filter(vacuna=vacuna).exists())

    def test_ficha_con_proxima_revision_crea_recordatorio_de_control(self):
        ficha = FichaClinica.objects.create(
            mascota=self.mascota,
            profesional=self.profesional,
            motivo_consulta='Control anual',
            diagnostico='Paciente sano',
            tratamiento='Sin tratamiento',
            proxima_revision=timezone.localdate() + timedelta(days=30),
        )
        recordatorio = Recordatorio.objects.get(ficha=ficha)
        self.assertEqual(recordatorio.tipo, Recordatorio.TipoChoices.CONTROL)
        self.assertEqual(recordatorio.fecha_programada, ficha.proxima_revision)

    def test_eliminar_origen_elimina_su_recordatorio(self):
        vacuna = Vacuna.objects.create(
            mascota=self.mascota,
            nombre='Rabia',
            fecha_aplicacion=timezone.localdate(),
            proxima_dosis=timezone.localdate() + timedelta(days=20),
            profesional=self.profesional,
        )
        ficha = FichaClinica.objects.create(
            mascota=self.mascota,
            profesional=self.profesional,
            motivo_consulta='Control anual',
            diagnostico='Paciente sano',
            tratamiento='Sin tratamiento',
            proxima_revision=timezone.localdate() + timedelta(days=30),
        )
        vacuna_id = vacuna.pk
        ficha_id = ficha.pk
        vacuna.delete()
        ficha.delete()
        self.assertFalse(Recordatorio.objects.filter(vacuna_id=vacuna_id).exists())
        self.assertFalse(Recordatorio.objects.filter(ficha_id=ficha_id).exists())


class RolesYVistasTest(BasePetCareTest):
    def test_dashboard_requiere_login(self):
        respuesta = self.client.get(reverse('dashboard'))
        self.assertEqual(respuesta.status_code, 302)

    def test_tutor_no_puede_entrar_al_listado_de_tutores(self):
        self.client.force_login(self.tutor_user)
        respuesta = self.client.get(reverse('tutores_lista'))
        self.assertEqual(respuesta.status_code, 403)

    def test_recepcionista_no_puede_crear_ficha_clinica(self):
        self.client.force_login(self.recepcion)
        respuesta = self.client.get(reverse('ficha_crear'))
        self.assertEqual(respuesta.status_code, 403)

    def test_veterinario_puede_crear_ficha_clinica(self):
        self.client.force_login(self.vet_user)
        respuesta = self.client.get(reverse('ficha_crear'))
        self.assertEqual(respuesta.status_code, 200)

    def test_tutor_solo_ve_sus_mascotas(self):
        self.client.force_login(self.tutor_user)
        respuesta = self.client.get(reverse('mascotas_lista'))
        self.assertContains(respuesta, 'Luna')
        self.assertNotContains(respuesta, 'Milo')

    def test_admin_accede_al_panel(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse('admin:index'))
        self.assertEqual(respuesta.status_code, 200)


class DocumentacionYFallbackTest(BasePetCareTest):
    def test_ruta_web_desconocida_redirige_al_inicio(self):
        respuesta = self.client.get('/ruta-que-no-existe/')
        self.assertRedirects(respuesta, reverse('home'))

    def test_ruta_valida_sin_barra_final_conserva_append_slash(self):
        respuesta = self.client.get('/login')
        self.assertRedirects(respuesta, reverse('login'))

    def test_admin_no_es_capturado_por_el_fallback(self):
        respuesta = self.client.get('/admin/', follow=False)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/admin/login/', respuesta['Location'])

    def test_login_del_admin_usa_la_plantilla_de_petcare(self):
        respuesta = self.client.get('/admin/login/')
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.content.decode()
        self.assertIn('Panel de administración', html)
        self.assertIn('PetCare', html)
        # No debe aparecer el texto por defecto de Django.
        self.assertNotIn('Django administration', html)
        self.assertNotIn('Please correct the error below', html)

    def test_api_desconocida_no_se_redirige_a_la_portada(self):
        respuesta = self.client.get('/api/ruta-que-no-existe/')
        self.assertEqual(respuesta.status_code, 404)

    def test_documentacion_bloqueada_para_anonimo(self):
        respuesta = self.client.get(reverse('swagger-ui'))
        self.assertIn(respuesta.status_code, (401, 403))

    def test_documentacion_disponible_para_admin(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse('schema'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('\xf3', respuesta['Content-Disposition'])
        self.assertIn('petcare-schema', respuesta['Content-Disposition'])

    def test_documentacion_bloqueada_para_tutor(self):
        self.client.force_login(self.tutor_user)
        respuesta = self.client.get(reverse('swagger-ui'))
        self.assertEqual(respuesta.status_code, 403)


class ApiTest(BasePetCareTest):
    def setUp(self):
        self.api = APIClient()

    def test_login_jwt_incluye_rol(self):
        respuesta = self.api.post(
            reverse('token_obtain_pair'),
            {'username': 'tutor_test', 'password': 'ClaveSegura123!'},
            format='json',
        )
        self.assertEqual(respuesta.status_code, 200)
        token = AccessToken(respuesta.data['access'])
        self.assertEqual(token['rol'], Usuario.RolChoices.TUTOR)
        self.assertIn('usuario', respuesta.data)

    def test_tutor_solo_ve_sus_mascotas_en_api(self):
        self.api.force_authenticate(self.tutor_user)
        respuesta = self.api.get('/api/mascotas/')
        self.assertEqual(respuesta.status_code, 200)
        nombres = [item['nombre'] for item in respuesta.data['results']]
        self.assertIn('Luna', nombres)
        self.assertNotIn('Milo', nombres)

    def test_admin_ve_todas_las_mascotas_en_api(self):
        self.api.force_authenticate(self.admin)
        respuesta = self.api.get('/api/mascotas/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['count'], 2)

    def test_tutor_no_puede_crear_mascotas(self):
        self.api.force_authenticate(self.tutor_user)
        respuesta = self.api.post('/api/mascotas/', {
            'tutor': self.tutor.pk,
            'nombre': 'Nueva',
            'especie': 'PERRO',
        }, format='json')
        self.assertEqual(respuesta.status_code, 403)

    def test_tutor_puede_cancelar_su_cita(self):
        cita = Cita.objects.create(
            mascota=self.mascota,
            profesional=self.profesional,
            fecha=self.fecha_futura(),
            hora=time(15, 0),
            motivo='Control',
        )
        self.api.force_authenticate(self.tutor_user)
        respuesta = self.api.post(f'/api/citas/{cita.pk}/cancelar/')
        self.assertEqual(respuesta.status_code, 200)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.EstadoChoices.CANCELADA)

    def test_tutor_no_puede_agendar_cita_para_mascota_ajena(self):
        self.api.force_authenticate(self.tutor_user)
        respuesta = self.api.post('/api/citas/', {
            'mascota': self.mascota_otro.pk,
            'profesional': self.profesional.pk,
            'fecha': self.fecha_futura(),
            'hora': '16:00',
            'motivo': 'Intento sobre mascota ajena',
        }, format='json')
        self.assertEqual(respuesta.status_code, 400)

    def test_tutor_no_puede_confirmar_citas(self):
        cita = Cita.objects.create(
            mascota=self.mascota,
            profesional=self.profesional,
            fecha=self.fecha_futura(),
            hora=time(16, 0),
            motivo='Control',
        )
        self.api.force_authenticate(self.tutor_user)
        respuesta = self.api.post(f'/api/citas/{cita.pk}/confirmar/')
        self.assertEqual(respuesta.status_code, 403)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.EstadoChoices.PROGRAMADA)

    def test_disponibilidad_muestra_bloques_y_ocupa_citas(self):
        fecha = self.fecha_futura()
        Cita.objects.create(
            mascota=self.mascota,
            profesional=self.profesional,
            fecha=fecha,
            hora=time(10, 0),
            motivo='Control',
        )
        self.api.force_authenticate(self.admin)
        respuesta = self.api.get('/api/citas/disponibilidad/', {
            'profesional': self.profesional.pk,
            'fecha': fecha.isoformat(),
        })
        self.assertEqual(respuesta.status_code, 200)
        bloques = {item['hora']: item['disponible'] for item in respuesta.data['horarios']}
        self.assertFalse(bloques['10:00'])
        self.assertTrue(bloques['10:30'])

    def test_no_autenticado_no_accede_a_la_api(self):
        respuesta = self.api.get('/api/mascotas/')
        self.assertEqual(respuesta.status_code, 401)
