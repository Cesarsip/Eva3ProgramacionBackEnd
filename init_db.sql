-- =====================================================================
-- PetCare - Creación de la base de datos PostgreSQL
-- Ejecutar como superusuario (postgres):
--   psql -U postgres -f init_db.sql
-- En AWS EC2 cambiar la contraseña por una segura.
-- =====================================================================

-- Usuario dedicado de la aplicación (no usar postgres para Django)
CREATE ROLE petcare_user LOGIN PASSWORD 'PetCareLocal2026Segura';

-- Base de datos UTF-8 propiedad del usuario de la aplicación
CREATE DATABASE petcare_db OWNER petcare_user ENCODING 'UTF8';

GRANT ALL PRIVILEGES ON DATABASE petcare_db TO petcare_user;

-- Permite crear la base de datos de pruebas de Django.
ALTER ROLE petcare_user CREATEDB;

-- Conectarse a la base para otorgar privilegios sobre el esquema público.
\connect petcare_db
GRANT ALL ON SCHEMA public TO petcare_user;
