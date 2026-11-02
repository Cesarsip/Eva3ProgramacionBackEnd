# Registro de uso de Inteligencia Artificial

**Proyecto:** PetCare — Sistema de Gestión de Clínica Veterinaria
**Asignatura:** Desarrollo Backend (EVA 3)
**Estudiante:** Cesar Antonio Aedo Álvarez
**Herramienta utilizada:** Asistente de IA integrado en el editor (OpenCode / modelo de lenguaje)
**Periodo:** Octubre de 2026

---

## 1. Propósito del uso de IA

La IA se utilizó como **copiloto de desarrollo** para:

- Proponer la arquitectura del proyecto y la organización de carpetas.
- Generar código base de modelos, vistas, formularios, serializers, permisos y pruebas.
- Redactar documentación técnica y este registro.
- Sugerir comandos de despliegue para Ubuntu/AWS.

Todas las propuestas fueron **revisadas, adaptadas, ejecutadas y verificadas** localmente
antes de incorporarlas al repositorio. La IA no tomó decisiones autónomas sobre el
entorno del estudiante ni accedió a credenciales fuera de las proporcionadas para el
despliegue autorizado.

---

## 2. Prompts representativos y resultados

### Prompt 1 — Contexto y arquitectura

> "Necesito desarrollar el Proyecto 1 de EVA 3: PetCare, una clínica veterinaria.
> Debo usar Django, PostgreSQL, CRUD completo, 4 casos de negocio, Django Admin
> personalizado, API y despliegue en AWS EC2. Propón la arquitectura de apps,
> modelos y roles."

**Resultado utilizado:** separación en `petcare` (dominio) y `petcare_project`
(configuración); roles `ADMINISTRADOR`, `VETERINARIO`, `RECEPCIONISTA` y `TUTOR`;
modelos `Usuario`, `Tutor`, `Mascota`, `Profesional`, `HorarioAtencion`, `Cita`,
`FichaClinica`, `Receta`, `Examen`, `Vacuna` y `Recordatorio`.

**Decisión del estudiante:** se mantuvo la separación y se agregaron validaciones de
negocio en los modelos (`clean()` y `save()`), no solo en los formularios.

---

### Prompt 2 — Reglas de agenda

> "Implementa las validaciones de una cita: fecha no pasada, profesional con horario,
> hora dentro del bloque, sin choque para el profesional ni para la mascota, y que
> cancelar libere el cupo. Agrega restricciones a nivel de base de datos."

**Resultado utilizado:** validaciones en `Cita.clean()`/`save()`, cálculo de bloques de
30 minutos en `HorarioAtencion`, y `UniqueConstraint` condicionales
`uniq_cita_activa_profesional` y `uniq_cita_activa_mascota`.

**Verificación:** pruebas `CitaBusinessRulesTest` (6 casos) ejecutadas con
`python manage.py test petcare`.

---

### Prompt 3 — Recordatorios automáticos

> "Cuando se registre una vacuna con próxima dosis o una ficha con próxima revisión,
> crea automáticamente un recordatorio. Si la fecha cambia, actualízalo; si se elimina
> la fecha o el registro, elimina el aviso pendiente."

**Resultado utilizado:** `petcare/signals.py` con señales `post_save` para crear o
actualizar el aviso; al quitar la fecha se elimina el recordatorio pendiente y, al
borrar la vacuna o la ficha, la relación 1:1 con `on_delete=CASCADE` elimina el
recordatorio asociado. La lógica es idempotente y devuelve el estado a `PENDIENTE`
cuando cambia la fecha.

**Verificación:** pruebas `RecordatoriosAutomaticosTest` (5 casos, incluido el
borrado en cascada del origen).

---

### Prompt 4 — Permisos por rol y por objeto

> "Un tutor solo debe ver sus propias mascotas, citas, fichas, vacunas y recordatorios.
> La recepcionista gestiona agenda pero no fichas clínicas. El veterinario gestiona lo
> clínico. El administrador tiene acceso total. Aplícalo en HTML y en la API."

**Resultado utilizado:** decorador `rol_requerido`, consultas filtradas
(`mascotas_visibles`, `citas_visibles`, etc.), permisos DRF
(`LecturaAutenticadaEscrituraPersonal`, `LecturaAutenticadaEscrituraVeterinario`,
`EsTutorPropietarioOStaff`) y el permiso específico `PermisoCitas` para permitir que un
tutor solicite y cancele únicamente sus propias citas.

**Verificación:** pruebas `RolesYVistasTest` y `ApiTest`; además se comprobó que un tutor
no puede crear una cita para una mascota ajena ni confirmar citas.

---

### Prompt 5 — Django Admin personalizado

> "Personaliza el admin de PetCare con list_display, list_filter, search_fields,
> inlines, date_hierarchy, acciones masivas y cabeceras del sitio. Debe verse como un
> panel de clínica veterinaria."

**Resultado utilizado:** `petcare/admin.py` con inlines de mascotas, horarios, recetas,
exámenes, vacunas y recordatorios; acciones para confirmar/cancelar/atender citas y
marcar recordatorios; columnas con colores para el estado de las citas.

---

### Prompt 6 — Interfaz HTML

> "Crea las plantillas con Bootstrap 5 para home, login, registro, dashboard y CRUD de
> tutores, mascotas, profesionales, citas, fichas, vacunas y recordatorios. Incluye
> calendario mensual, paginación y mensajes. No uses CDN para que funcione sin internet."

**Resultado utilizado:** plantillas en `templates/`, Bootstrap 5.3.3 e iconos
vendorizados en `static/vendor/`, hoja de estilos `static/css/petcare.css`, scripts en
`static/js/petcare.js`, calendario mensual y páginas de error 403/404/500.

---

### Prompt 7 — API REST y documentación

> "Expón el dominio con DRF ViewSets, JWT, filtros, búsqueda, paginación y documentación
> OpenAPI con drf-spectacular. Agrega un endpoint de disponibilidad y acciones para
> confirmar, cancelar y atender citas."

**Resultado utilizado:** `petcare/api_views.py`, `serializers.py`, `filters.py`,
router en `petcare/urls.py`, Swagger en `/api/docs/` y Redoc en `/api/redoc/`.

---

### Prompt 8 — Pruebas automatizadas

> "Escribe pruebas que cubran las reglas de agenda, los recordatorios automáticos, los
> permisos por rol y los endpoints principales de la API. Deben poder ejecutarse con
> `python manage.py test petcare`."

**Resultado utilizado:** `petcare/tests.py` con 26 pruebas iniciales. Se detectó y corrigió un
error real: el permiso de escritura bloqueaba que un tutor cancelara su propia cita por
API (devolvía 403). Se creó `PermisoCitas` y se agregó validación en el serializer.

**Verificación:** la suite final contiene 36 pruebas y se ejecutó con
`python manage.py test petcare` → `Ran 36 tests ... OK`.

---

### Prompt 9 — Despliegue en AWS

> "Guía el despliegue en Ubuntu EC2 con PostgreSQL, Gunicorn, Nginx y systemd, usando
> una IP elástica y sin exponer los puertos 5432 ni 8000."

**Resultado utilizado:** guía del README (sección 11), servicio systemd para Gunicorn en
`127.0.0.1:8000`, Nginx como reverse proxy en el puerto 80, `.env` de producción con
`DEBUG=False` y `ALLOWED_HOSTS` restringido.

**Decisión del estudiante:** el despliegue se ejecutó desde su equipo con la clave SSH
proporcionada, manteniendo PostgreSQL escuchando solo en localhost.

---

### Prompt 10 — Documentación

> "Redacta el README del proyecto con la URL pública, credenciales de prueba, reglas de
> negocio, endpoints, instalación local, despliegue AWS y mapeo con la rúbrica."

**Resultado utilizado:** `README.md` y este archivo `prompts_ia.md`.

---

### Prompt 11 — Login del admin con estilo PetCare

> "Quiero que /admin/login/ no se vea como Django: que use el mismo HTML, CSS y
> componentes que el resto de PetCare, sin textos técnicos de Django por defecto."

**Resultado utilizado:** `templates/admin/login.html`, que extiende `base.html` y
reutiliza `auth-wrapper`, `auth-card` y `includes/campo.html`, con POST a
`{{ app_path }}`, `{% csrf_token %}`, campo oculto `next` y mensajes de error de
`form.non_field_errors`. El enlace del menú lateral se rotuló **Administración**.

**Verificación:** prueba `test_login_del_admin_usa_la_plantilla_de_petcare`
(`/admin/login/` → 200, contiene “PetCare” y no contiene “Django administration”).

---

## 3. Errores detectados y corregidos durante el proceso

| Problema | Causa | Solución aplicada |
|---|---|---|
| 403 al cancelar una cita propia por API | `LecturaAutenticadaEscrituraPersonal` bloqueaba todo POST de un tutor antes de evaluar el objeto | Se creó `PermisoCitas`, que permite `create` y `cancelar` a tutores y delega el resto al permiso de objeto |
| Un tutor podía intentar agendar para una mascota ajena por API | El serializer no validaba la propiedad de la mascota | Se agregó validación en `CitaSerializer.validate` y se fuerza estado `PROGRAMADA` al crear como tutor |
| Advertencia de drf-spectacular por usuario anónimo | `get_queryset` accedía a `puede_gestionar_clinica` sin verificar autenticación | Se agregó guarda `is_authenticated` y `getattr(..., False)` |
| Plantilla base con dos bloques `content` | El layout público y privado estaban duplicados | Se unificó la estructura manteniendo un solo bloque `content` |
| Swagger UI se quedaba cargando el esquema | `Content-Disposition` con el título acentuado (`Gestión`) producía un byte no ASCII en la cabecera HTTP | Subclase `PetCareSpectacularAPIView._get_filename` que fuerza `petcare-schema.json/yaml` |

---

## 4. Validación humana

El estudiante:

1. Ejecutó `python manage.py check` y `python manage.py test petcare` hasta obtener
   **36 pruebas exitosas**.
2. Verificó manualmente el login con los cuatro roles y las restricciones de acceso.
3. Revisó el panel de Django Admin y las pantallas principales.
4. Autorizó y supervisó el despliegue en su instancia EC2.
5. Comprobó la aplicación publicada en `http://52.21.173.229/`.

---

## 5. Conclusión

La IA aceleró la generación de código y documentación, pero el valor del proyecto está
en la **verificación**: las reglas de negocio se probaron con una suite automatizada, los
permisos se validaron con usuarios reales de cada rol y el despliegue se comprobó en un
servidor AWS con PostgreSQL y Nginx. La IA se usó como apoyo, no como sustituto del
criterio técnico.
