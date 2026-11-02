# PetCare · Sistema de Gestión de Clínica Veterinaria

Proyecto de **Desarrollo Backend (EVA 3)** — Django + Django REST Framework + PostgreSQL desplegado en AWS EC2.

| Dato | Valor |
|---|---|
| **Aplicación desplegada** | <http://52.21.173.229/> |
| **Repositorio GitHub** | <https://github.com/Cesarsip/Eva3ProgramacionBackEnd> |
| **Estudiante** | Cesar Antonio Aedo Álvarez |
| **Correo** | cesar.aedo05@inacapmail.cl |
| **Sección / Grupo** | IEC-N4-C2 · Grupo 1 |
| **Asignatura** | Desarrollo Backend |
| **Docente** | Marcelo Alvarado |
| **Año** | 2026 |
| **Proyecto asignado** | Proyecto 1 — PetCare (clínica veterinaria) |

> **URL pública (IP elástica AWS):** <http://52.21.173.229/>
> Documentación de la API: <http://52.21.173.229/api/docs/>
> *(requiere sesión de personal de la clínica)*

### Rutas principales

| Ruta | Qué muestra | Acceso |
|---|---|---|
| `/` | Portada pública de PetCare | Público |
| `/login/` | Inicio de sesión | Público |
| `/registro/` | Registro de tutores | Público |
| `/dashboard/` | Panel de gestión | Sesión iniciada |
| `/admin/` | Panel de administración PetCare (Django Admin) | Personal (`is_staff`) |
| `/api/docs/` | Swagger UI | Personal de la clínica |
| `/api/redoc/` | Redoc | Personal de la clínica |
| `/api/schema/` | Esquema OpenAPI | Personal de la clínica |
| `/health/` | Estado del servicio | Público |
| Cualquier otra ruta web | Muestra la portada | Público |

> **Importante:** la portada `/` es la página pública. Para ver el sistema hay que
> pulsar **Ingresar** y autenticarse; el login redirige a `/dashboard/`. El enlace
> **Administración** aparece en el menú lateral solo para usuarios con `is_staff`;
> su pantalla de acceso está personalizada con la identidad de PetCare (no muestra
> el Django por defecto). Cualquier otra ruta desconocida vuelve a la portada.

---

## 1. Descripción

PetCare es una aplicación web para administrar una clínica veterinaria. Permite gestionar
tutores, mascotas, profesionales con sus horarios, citas médicas, fichas clínicas con
recetas y exámenes, vacunas y recordatorios automáticos. Incluye una interfaz HTML con
Bootstrap 5, una API REST documentada con OpenAPI (Swagger/Redoc) y un panel de
administración personalizado con la identidad visual de PetCare.

El dominio está modelado con reglas de negocio reales: validación de disponibilidad,
prevención de choques de agenda, generación automática de recordatorios y control de
acceso por roles.

---

## 2. Stack tecnológico

- **Python 3.12+** / **Django 6.1**
- **Django REST Framework** + **SimpleJWT** (autenticación Bearer)
- **drf-spectacular** (OpenAPI 3, Swagger UI y Redoc)
- **PostgreSQL 16** (producción y desarrollo)
- **Bootstrap 5.3.3** e iconos vendorizados (la app funciona sin CDN)
- **Gunicorn** + **Nginx** (reverse proxy) + **systemd** en AWS EC2
- **Ubuntu 26.04 LTS**, IP elástica `52.21.173.229`
- **django-filter** para filtros de la API

---

## 3. Funcionalidades y CRUD

| Módulo | CRUD | Notas |
|---|---|---|
| Usuarios y roles | Crear / listar / editar (Admin) | Roles: Administrador, Veterinario, Recepcionista, Tutor |
| Tutores | CRUD completo (Admin/Recepción) | Búsqueda por nombre, RUT, correo y teléfono |
| Mascotas | CRUD completo (personal) | El tutor solo ve sus propias mascotas |
| Profesionales | CRUD completo (Admin) | Registro profesional y especialidad |
| Horarios de atención | CRUD completo (Admin) | Bloques por día de la semana |
| Citas | CRUD completo | Agenda por profesional, cambio de estados |
| Fichas clínicas | CRUD completo (Vet/Admin) | Recetas y exámenes como formularios inline |
| Vacunas | CRUD completo (Vet/Admin) | Genera recordatorio de próxima dosis |
| Recordatorios | CRUD completo | Envío y cierre de avisos |
| API REST | CRUD vía ViewSets | Documentada en `/api/docs/` |
| Django Admin | Panel personalizado | Inlines, filtros, búsqueda y acciones |

### 3.1 Fallback de rutas (estilo EVA 2 / CarritoShop)

El proyecto incluye un `re_path` comodín al final de `petcare_project/urls.py`.
Cualquier URL web que no exista muestra la portada en lugar de la pantalla 404
genérica, igual que el fallback de CarritoShop (EVA 2). La portada se renderiza
directamente: aunque tengas la sesión iniciada, una ruta desconocida como
`/poto` muestra la portada y no el dashboard. Se excluyen `/admin/`, `/api/`,
`/static/` y `/media/` para no interferir con el panel de Django, la API ni los
archivos estáticos. Las rutas válidas sin barra final (por ejemplo `/login`)
conservan el comportamiento normal de Django y redirigen a `/login/`.

---

## 4. Reglas de negocio implementadas

### 4.1 Agenda sin choques de horario

Al crear o editar una cita el sistema valida:

1. La fecha no puede ser pasada.
2. El profesional debe estar activo y tener un bloque de atención para ese día.
3. La hora debe estar dentro del bloque de atención (con duración de 30 minutos).
4. No puede existir otra cita activa del mismo profesional en el mismo bloque.
5. La mascota tampoco puede tener dos citas activas a la misma hora.

Las citas canceladas o no asistidas liberan el bloque. Además existen restricciones
`UniqueConstraint` a nivel de base de datos para reforzar la integridad.

La API expone `GET /api/citas/disponibilidad/?profesional=ID&fecha=AAAA-MM-DD` para
calcular los bloques libres y ocupados.

### 4.2 Recordatorios automáticos

Mediante señales de Django (`petcare/signals.py`):

- Al registrar una **vacuna con próxima dosis**, se crea un recordatorio de tipo
  `VACUNA` para esa fecha.
- Al registrar una **ficha con próxima revisión**, se crea un recordatorio de tipo
  `CONTROL`.
- Si la fecha cambia, el recordatorio se actualiza y vuelve a estado `PENDIENTE`.
- Si se elimina la fecha futura o el registro de origen, el recordatorio pendiente
  se elimina.

### 4.3 Ficha clínica y atención

- Solo **veterinarios y administradores** pueden crear o editar fichas clínicas.
- La recepcionista puede gestionar agenda, tutores y mascotas, pero **no** el historial
  clínico.
- Una ficha puede asociarse a una cita; al guardarla, la cita pasa a `ATENDIDA`.
- Recetas y exámenes se registran en la misma pantalla mediante formularios inline.

### 4.4 Roles y privacidad de datos

- **Tutor:** solo accede a sus mascotas, citas, fichas, vacunas y recordatorios.
  Puede solicitar una cita y cancelar las propias; no puede confirmarlas ni atenderlas.
- **Recepcionista:** agenda, tutores y mascotas; sin acceso a fichas ni vacunas.
- **Veterinario:** agenda y todo el historial clínico.
- **Administrador:** acceso total a los módulos, incluyendo eliminaciones y el
  panel de administración.

Las restricciones se aplican tanto en las vistas HTML (decorador `rol_requerido` y
consultas filtradas) como en la API (permisos DRF por rol y por objeto).

---

## 5. Seguridad

- Autenticación por **sesión** para la interfaz y **JWT** para la API.
- Contraseñas con hashing de Django y validadores de robustez.
- Permisos por rol y por objeto en cada ViewSet.
- `DEBUG=False`, `SECRET_KEY` y credenciales de base de datos en variables de entorno.
- `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` restringidos a la IP elástica.
- Protección CSRF en formularios, `X-Frame-Options: DENY` y `X-Content-Type-Options`.
- PostgreSQL escucha solo en `127.0.0.1`; no se expone el puerto 5432.
- Gunicorn escucha en `127.0.0.1:8000`; solo Nginx publica el puerto 80.
- Puertos abiertos en el Security Group: **22, 80 y 443**.

---

## 6. Instalación local

### 6.1 Requisitos

- Python 3.12+
- PostgreSQL 16 en `127.0.0.1:5432`

### 6.2 Base de datos

```bash
psql -U postgres -f init_db.sql
```

El script crea el rol `petcare_user`, la base `petcare_db` y otorga permisos.
Cambia la contraseña de ejemplo antes de usarlo en un entorno real.

### 6.3 Entorno virtual y dependencias

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 6.4 Variables de entorno

```bash
copy .env.example .env    # Windows
cp .env.example .env      # Linux/macOS
```

Edita `.env` con los datos reales de tu base y una `DJANGO_SECRET_KEY` segura.

### 6.5 Migraciones y datos de demostración

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Abre <http://127.0.0.1:8000/>.

---

## 7. Credenciales de demostración

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin` | `AdminPetCare2026!` |
| Veterinario | `veterinario` | `VetPetCare2026!` |
| Recepcionista | `recepcion` | `Recepcion2026!` |
| Tutor | `tutor` | `TutorPetCare2026!` |

> En producción estas claves deben cambiarse. El comando `seed_demo` solo crea datos
> de ejemplo y es idempotente.

---

## 8. API REST

### 8.1 Documentación

- Swagger UI: <http://52.21.173.229/api/docs/>
- Redoc: <http://52.21.173.229/api/redoc/>
- Esquema OpenAPI: <http://52.21.173.229/api/schema/>

> **Acceso restringido:** la documentación solo está disponible para personal de la
> clínica con sesión iniciada (Administrador, Veterinario o Recepcionista). Un tutor
> o un visitante anónimo recibe **403**. Para abrirla, inicia sesión en
> <http://52.21.173.229/login/> y luego visita `/api/docs/`.

### 8.2 Autenticación JWT

```http
POST /api/auth/token/
Content-Type: application/json

{
  "username": "tutor",
  "password": "TutorPetCare2026!"
}
```

Respuesta:

```json
{
  "refresh": "<token>",
  "access": "<token>",
  "usuario": { "id": 4, "username": "tutor", "rol": "TUTOR", "...": "..." }
}
```

Usa el token en las demás peticiones:

```http
Authorization: Bearer <access>
```

También existen:

- `POST /api/auth/token/refresh/` — renovar el access token.
- `POST /api/auth/registro/` — registrar un tutor.
- `GET /api/auth/me/` — perfil del usuario autenticado.

### 8.3 Endpoints principales

| Recurso | Ruta |
|---|---|
| Tutores | `/api/tutores/` |
| Mascotas | `/api/mascotas/` |
| Historial de mascota | `/api/mascotas/{id}/historial/` |
| Profesionales | `/api/profesionales/` |
| Horarios | `/api/horarios/` |
| Citas | `/api/citas/` |
| Disponibilidad | `/api/citas/disponibilidad/?profesional=1&fecha=2026-11-02` |
| Confirmar cita | `POST /api/citas/{id}/confirmar/` |
| Cancelar cita | `POST /api/citas/{id}/cancelar/` |
| Atender cita | `POST /api/citas/{id}/atender/` |
| Fichas clínicas | `/api/fichas/` |
| Vacunas | `/api/vacunas/` |
| Recordatorios | `/api/recordatorios/` |
| Enviar recordatorio | `POST /api/recordatorios/{id}/enviar/` |
| Completar recordatorio | `POST /api/recordatorios/{id}/completar/` |
| Usuarios (solo Admin) | `/api/usuarios/` |
| Salud del servicio | `/health/` |

La API permite paginación (`?page=`), búsqueda (`?search=`) y filtros por campo
(`?estado=`, `?especie=`, `?profesional=`, etc.).

---

## 9. Panel de administración personalizado

Disponible en <http://52.21.173.229/admin/> para usuarios con `is_staff`.

La pantalla de acceso está personalizada con `templates/admin/login.html`: usa la
base, los estilos y los componentes de PetCare (`auth-wrapper`, `auth-card`, campos
con `includes/campo.html`), por lo que no se ve el login gris por defecto de Django
ni el texto "Django administration".

Personalizaciones incluidas en `petcare/admin.py`:

- Cabeceras del sitio adaptadas a PetCare (“PetCare · Administración Veterinaria”).
- Búsqueda, filtros, ordenamiento y paginación por modelo.
- Inlines de mascotas en tutores, vacunas y recordatorios en mascotas, recetas y
  exámenes en fichas clínicas, y horarios en profesionales.
- Campos de solo lectura para auditoría (`fecha_creacion`, `fecha_actualizacion`).
- Acciones masivas para confirmar, cancelar y atender citas.
- Acciones para marcar recordatorios como enviados o completados.
- Campos con autocompletado para relaciones.
- Validaciones del dominio heredadas de los modelos.

---

## 10. Pruebas automatizadas

```bash
python manage.py test petcare -v 2
```

Cobertura actual: **36 pruebas**, todas en verde. Se validan:

- Reglas de agenda (fecha pasada, fuera de horario, sin horario, choque de
  profesional y de mascota, liberación al cancelar).
- Recordatorios automáticos por vacuna y por próxima revisión, incluyendo
  actualización y eliminación.
- Permisos HTML por rol (tutor, recepción, veterinario, admin).
- API: JWT con rol, alcance de datos por tutor, bloqueo de escritura para tutores,
  cancelación de citas propias, rechazo de citas para mascotas ajenas y
  disponibilidad de bloques.
- Documentación OpenAPI restringida por rol, nombre de archivo ASCII del esquema,
  fallback de rutas web, exclusión de `/admin/` y `/api/` del comodín y plantilla
  personalizada del login de administración.

---

## 11. Despliegue en AWS EC2

### 11.1 Arquitectura

```text
Internet
   │  HTTP :80
   ▼
 Nginx (EC2, IP elástica 52.21.173.229)
   │  proxy_pass 127.0.0.1:8000
   ▼
 Gunicorn (systemd: petcare.service)
   │
   ▼
 Django 6.1 + PostgreSQL 16 (127.0.0.1:5432)
```

### 11.2 Pasos resumidos

```bash
# En la instancia Ubuntu
sudo apt update
sudo apt install -y python3-venv python3-pip postgresql nginx git

# Base de datos
sudo -u postgres psql -f init_db.sql
# (usar la contraseña de producción definida en .env)

# Código
git clone https://github.com/Cesarsip/Eva3ProgramacionBackEnd.git petcare
cd petcare
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# .env de producción con DEBUG=False, ALLOWED_HOSTS y CSRF_TRUSTED_ORIGINS
cp .env.example .env
nano .env

python manage.py migrate
python manage.py seed_demo
python manage.py collectstatic --noinput
```

Servicio systemd (`/etc/systemd/system/petcare.service`):

```ini
[Unit]
Description=PetCare Gunicorn
After=network.target postgresql.service

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/petcare
EnvironmentFile=/home/ubuntu/petcare/.env
ExecStart=/home/ubuntu/petcare/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8000 \
    petcare_project.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

Nginx (`/etc/nginx/sites-available/petcare`):

```nginx
server {
    listen 80;
    server_name 52.21.173.229;

    client_max_body_size 10M;

    location /static/ {
        alias /home/ubuntu/petcare/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /home/ubuntu/petcare/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/petcare /etc/nginx/sites-enabled/petcare
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl daemon-reload
sudo systemctl enable --now petcare
sudo nginx -t && sudo systemctl reload nginx
```

Verificación:

```bash
curl -I http://52.21.173.229/
curl http://52.21.173.229/health/
```

### 11.3 Estado verificado del despliegue (31/10/2026)

| Comprobación | Resultado |
|---|---|
| `systemctl is-active petcare nginx postgresql` | `active` en los tres servicios |
| `systemctl is-enabled petcare nginx postgresql` | `enabled` (arrancan al reiniciar) |
| Suite de pruebas en el servidor | **36 tests OK** |
| `GET /` | 200 |
| `GET /health/` | 200 |
| `GET /ruta-desconocida/` | 200 (muestra la portada, incluso con sesión iniciada) |
| `GET /login` sin barra final | 302 → `/login/` |
| `GET /api/ruta-desconocida/` | 404 (la API no se redirige) |
| `GET /api/docs/` sin sesión | 403 (solo personal) |
| `GET /api/docs/` con sesión admin | 200 |
| Swagger UI carga el esquema | 200, `Content-Disposition: petcare-schema.json` |
| `GET /api/docs/` con sesión tutor | 403 (correcto) |
| `GET /api/schema/` sin sesión | 403 (solo personal) |
| `GET /api/schema/` con sesión admin | 200 |
| `GET /static/css/petcare.css` | 200 |
| `GET /admin/` sin sesión | 302 → `/admin/login/` (plantilla PetCare) |
| Login admin + `/admin/` | 200 |
| Login tutor + `/tutores/` | 403 (correcto) |
| JWT tutor + `/api/mascotas/` | 200, solo su mascota |
| JWT admin + `/api/mascotas/` | 200, 3 mascotas |
| Verificación externa automatizada | **36/36 pruebas + 21/21 comprobaciones públicas** |

`python manage.py check --deploy` reporta únicamente 4 advertencias relacionadas con
HTTPS (`SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE`). Son esperables porque la entrega se publica por **HTTP con IP
elástica**, sin dominio ni certificado TLS. Si se agrega un dominio, basta con emitir
un certificado (por ejemplo, Let's Encrypt), habilitar `DJANGO_USE_HTTPS=True` en
`.env` y redirigir el puerto 80 al 443 en Nginx.

---

## 12. Estructura del proyecto

```text
Eva3ProgramacionBackEnd/
├── manage.py
├── requirements.txt
├── init_db.sql
├── .env.example
├── petcare_project/        # Configuración Django (settings, URLs, WSGI)
├── petcare/                # Aplicación de dominio
│   ├── models.py           # Usuarios, tutores, mascotas, agenda, clínica
│   ├── views.py            # Vistas HTML
│   ├── api_views.py        # ViewSets y endpoints JWT
│   ├── serializers.py      # Serializers DRF
│   ├── permissions.py      # Permisos por rol y objeto
│   ├── filters.py          # Filtros de la API
│   ├── forms.py            # Formularios HTML
│   ├── admin.py            # Django Admin personalizado
│   ├── signals.py          # Recordatorios automáticos
│   ├── tests.py            # 36 pruebas automatizadas
│   └── management/commands/seed_demo.py
├── templates/              # Plantillas Bootstrap 5
├── static/                 # CSS, JS y vendor (Bootstrap/Icons)
└── prompts_ia.md           # Registro del uso de IA
```

---

## 13. Mapeo con la rúbrica EVA 3

| Criterio | Evidencia |
|---|---|
| Repositorio GitHub público | <https://github.com/Cesarsip/Eva3ProgramacionBackEnd> |
| README con IP pública AWS | Este documento, sección superior y sección 11 |
| `prompts_ia.md` | [`prompts_ia.md`](prompts_ia.md) |
| Aplicación desplegada | <http://52.21.173.229/> |
| Defensa de Django Admin | Sección 9 + panel en `/admin/` (login con estilo PetCare) |
| PostgreSQL configurado | `settings.py`, `.env.example`, `init_db.sql` |
| CRUD completo + 4 casos | Secciones 3 y 4 |
| Seguridad, sesiones e IA | Secciones 5, 8 y `prompts_ia.md` |
| Despliegue AWS EC2 | Sección 11 |

---

## 14. Uso de inteligencia artificial

El desarrollo se apoyó en un asistente de IA como copiloto para generar estructura,
código base, pruebas y documentación. El registro de prompts, decisiones y validaciones
está en [`prompts_ia.md`](prompts_ia.md). Todo el código fue revisado, ejecutado y
probado localmente antes de su despliegue.

---

## 15. Autor

**Cesar Antonio Aedo Álvarez**
GitHub: [@Cesarsip](https://github.com/Cesarsip)
Correo: cesar.aedo05@inacapmail.cl
