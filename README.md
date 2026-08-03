# GanaBosques Web Admin

![GitHub release](https://img.shields.io/github/v/release/CIAT-DAPA/ganabosques_web_admin)
![GitHub tag](https://img.shields.io/github/v/tag/CIAT-DAPA/ganabosques_web_admin)

## 📌 Descripción
GanaBosques Web Admin es una aplicación web de administración para el ecosistema GanaBosques. Está construida con Flask 3.1 sobre Python, persiste información en MongoDB mediante MongoEngine y centraliza su lógica de negocio en un solo punto de arranque: [src/app.py](src/app.py). Desde ahí se cargan las variables de entorno, se inicializa Flask-Login, se conecta a MongoDB y se registran todos los blueprints de administración, carga de datos, usuarios, roles y autenticación.

La aplicación también integra servicios externos para autenticación con Keycloak, publicación de capas en GeoServer y validación de tokens contra la API de GanaBosques. El resultado es un panel administrativo orientado a operación interna, no una API pública.

## 🎯 Rol en el ecosistema
Este componente funciona como la consola administrativa del ecosistema GanaBosques. Su misión es permitir la carga, edición y deshabilitación de catálogos administrativos y productivos, la administración de usuarios y roles, la importación de capas espaciales y la sincronización con servicios externos que sostienen la operación del sistema.

En la arquitectura general, consume autenticación de Keycloak, consulta y actualiza MongoDB, publica información geoespacial en GeoServer y valida la sesión del usuario contra la API backend de GanaBosques. En términos prácticos:

- Recibe sesiones autenticadas desde Keycloak.
- Procesa formularios y pantallas de mantenimiento sobre colecciones de MongoDB.
- Publica y actualiza capas geoespaciales y mosaicos en GeoServer.
- Importa códigos, proveedores y niveles administrativos desde CSV y archivos comprimidos.
- Controla el acceso al panel según el rol administrativo del usuario.

## 🏗️ Estructura del proyecto
```text
ganabosques_web_admin/
├── .github/
│   └── workflows/
│       └── pipeline.yaml
├── pipelines/
│   └── pipeline-test.yml
├── config.py
├── DOCKER_GUIE.md
├── Dockerfile
├── Jenkinsfile
├── README.md
├── README_api.md
├── src/
│   ├── app.py
│   ├── extensions.py
│   ├── geoserver_import.py
│   ├── requirements.txt
│   ├── decorators/
│   │   ├── __init__.py
│   │   └── auth.py
│   ├── forms/
│   │   ├── adm1_form.py
│   │   ├── adm2_form.py
│   │   ├── adm3_form.py
│   │   ├── adm_import.py
│   │   ├── configuration_form.py
│   │   ├── enterprise_form.py
│   │   ├── farm_form.py
│   │   └── login_form.py
│   ├── models/
│   │   └── User.py
│   ├── routes/
│   │   ├── adm1_routes.py
│   │   ├── adm2_routes.py
│   │   ├── adm3_routes.py
│   │   ├── adm_import.py
│   │   ├── adminlevel_data_management.py
│   │   ├── configuration_routes.py
│   │   ├── data_management.py
│   │   ├── enterprise_routes.py
│   │   ├── farm_routes.py
│   │   ├── home.py
│   │   ├── role_routes.py
│   │   ├── spatial_data_management.py
│   │   ├── suppliers_data_management.py
│   │   └── user_routes.py
│   ├── services/
│   │   ├── farmpolygons_service.py
│   │   └── oauth_service.py
│   ├── static/
│   │   └── img/
│   ├── templates/
│   │   ├── adm1/
│   │   ├── adm2/
│   │   ├── adm3/
│   │   ├── configuration/
│   │   ├── enterprise/
│   │   ├── farm/
│   │   ├── role/
│   │   ├── user/
│   │   ├── base.html
│   │   ├── base_login.html
│   │   ├── data_management.html
│   │   ├── home.html
│   │   ├── import_suppliers.html
│   │   ├── importar_administrativos.html
│   │   ├── login.html
│   │   ├── login_copy.html
│   │   └── upload.html
│   ├── tools/
│   │   ├── __init__.py
│   │   └── log_print.py
│   └── utils/
│       ├── properties_nad_atd/
│       │   ├── indexer.properties
│       │   └── timeregex.properties
│       └── properties_smbyc/
│           ├── indexer.properties
│           └── timeregex.properties
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_decorators_auth.py
│   ├── test_farmpolygons_service.py
│   ├── test_forms.py
│   ├── test_geoserver_import_helpers.py
│   ├── test_log_print.py
│   ├── test_oauth_service.py
│   └── test_user_model.py
├── uploaded_codes/
└── uploaded_files/
```

> Nota: `.env` y los archivos de log o carga son artefactos locales del entorno y no forman parte del código fuente de la aplicación.

## ⚙️ Requisitos
- Python 3.12.X
- `pip`
- Dependencias clave fijadas en [src/requirements.txt](src/requirements.txt):
  - Flask 3.1.0
  - mongoengine 0.29.1
  - pymongo 4.12.1
  - pandas 2.2.3
  - pyproj 3.7.1
  - shapely 2.1.2
  - gsconfig-py3 1.0.7
  - gunicorn 22.0.0
  - python-dotenv 1.1.0
  - requests 2.32.3
  - certifi 2025.4.26
  - Werkzeug 3.1.3
  - Jinja2 3.1.6
  - click 8.1.8
  - authlib
  - flask-wtf
  - wtforms
  - `ganabosques_orm` desde GitHub (`git+https://github.com/CIAT-DAPA/ganabosques_orm`)

## 🔐 Variables de entorno
Las variables consumidas por el código son las siguientes. No se incluyen `HOST` ni `PORT` porque son parámetros de ejecución del servidor y no parte del contrato funcional del panel.

| Variable | Ejemplo | Descripción |
| --- | --- | --- |
| `DEBUG` | `false` | Activa o desactiva el modo depuración de Flask. |
| `SECRET_KEY` | `xxxxxxxx` | Clave secreta de Flask para sesiones y mensajes flash. |
| `MONGO_URI` | `mongodb://mongo:27017` | URI de conexión a MongoDB usada al iniciar la app y los procesos de importación. |
| `MONGO_DB_NAME` | `ganabosques` | Nombre de la base de datos MongoDB. |
| `API_BASE_URL` | `http://localhost:8000` | Base URL de la API de GanaBosques usada para validar el token. |
| `GEOSERVER_URL` | `http://geoserver:8080/geoserver` | URL base de GeoServer para publicar capas y mosaicos. |
| `GEOSERVER_USER` | `admin` | Usuario de GeoServer. |
| `GEOSERVER_PWD` | `geoserver` | Contraseña de GeoServer. |
| `GEO_WORKSPACE` | `deforestation` | Workspace por defecto para operaciones geoespaciales. |
| `KEYCLOAK_SERVER_URL` | `http://keycloak:8080` | URL base del servidor Keycloak. |
| `KEYCLOAK_REALM` | `GanaBosques` | Realm usado por el flujo OAuth/OIDC. |
| `KEYCLOAK_CLIENT_ID` | `GanaBosques` | Client ID registrado en Keycloak para este panel. |
| `KEYCLOAK_CLIENT_SECRET` | `xxxxxxxx` | Client secret del cliente Keycloak. |

## 🚀 Instalación
El proyecto puede ejecutarse de dos formas: de manera local con un entorno virtual de Python, o dentro de un contenedor Docker para replicar el entorno de despliegue. En ambos casos la configuración depende de las variables anteriores y de la conexión con MongoDB, GeoServer y Keycloak.

### Entorno local
Para este modo necesitas Python 3.12.X instalado, crear un entorno virtual e instalar las dependencias desde [src/requirements.txt](src/requirements.txt). El flujo local está pensado para desarrollo y depuración diaria.

```bash
git clone https://github.com/CIAT-DAPA/ganabosques_web_admin.git
cd ganabosques_web_admin
python -m venv env
```

Activar el entorno virtual:

Windows:
```bash
env\Scripts\activate
```

Linux/macOS:
```bash
source env/bin/activate
```

Instalar dependencias:
```bash
pip install -r src/requirements.txt
```

### Con Docker
Si prefieres un entorno reproducible, el repositorio incluye un [Dockerfile](Dockerfile) basado en `python:3.12-slim` que instala `gunicorn`, dependencias geoespaciales y ejecuta la app en el puerto 5000. La guía operativa completa está en [DOCKER_GUIE.md](DOCKER_GUIE.md).

## ▶️ Ejecutar el proyecto
Una vez instaladas las dependencias y definida la configuración, puedes levantar la aplicación en desarrollo con:

```bash
python src/app.py
```

### Producción
El despliegue en producción arranca la aplicación desde `src/` y redirige la salida a `app.log`:

```bash
cd src
nohup python app.py > app.log 2>&1 &
```

Cuando se ejecuta en contenedor, el `Dockerfile` usa este comando de arranque:

```bash
gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 app:app
```

La interfaz queda disponible en la raíz del servidor y la sesión se protege con Keycloak antes de entrar al panel.

## 📡 Rutas / Pantallas principales
| Pantalla | Ruta(s) | Descripción |
| --- | --- | --- |
| Autenticación (Login) | `/login`, `/login/keycloak`, `/auth/callback`, `/logout` | Flujo de acceso, callback OAuth y cierre de sesión con Keycloak. |
| Página Principal (Inicio) | `/`, `/home` | Redirige a login o al panel principal según la sesión. |
| Importar Datos Espaciales | `/importar` | Carga de shapefiles, mosaicos TIFF y publicación de capas en GeoServer. |
| Importar Proveedores | `/importar_proveedores`, `/descargar_encontrados`, `/descargar_no_encontrados` | Importa desde CSV la relación de proveedores y predios asociados a las empresas, y permite descargar los registros encontrados y no encontrados. |
| Consulta de Datos | `/data_management/data`, `/data_management/download`, `/data_management/check` | Consulta de configuraciones de descarga y validación de archivos recientes. |
| Gestión de Datos — Configuración | `/configuration/`, `/configuration/edit/<id>`, `/configuration/delete/<id>`, `/configuration/reset/<id>` | CRUD de configuraciones de descarga. |
| Gestión de Datos — Departamentos (ADM1) | `/adm1`, `/adm1/edit/<id>`, `/adm1/delete/<id>`, `/adm1/reset/<id>` | Administración de departamentos. |
| Gestión de Datos — Municipios (ADM2) | `/adm2`, `/adm2/edit/<id>`, `/adm2/delete/<id>`, `/adm2/reset/<id>`, `/api/adm2-by-adm1/<adm1_id>` | Administración de municipios y endpoint JSON dependiente de departamento. |
| Gestión de Datos — Veredas (ADM3) | `/adm3`, `/adm3/edit/<id>`, `/adm3/delete/<id>`, `/adm3/reset/<id>`, `/api/adm3-by-adm2/<adm2_id>` | Administración de veredas y endpoint JSON dependiente de municipio. |
| Gestión de Datos — Fincas | `/farm`, `/farm/edit/<id>`, `/farm/delete/<id>`, `/farm/reset/<id>` | Administración de fincas y asociaciones de extensión. |
| Gestión de Datos — Empresas | `/enterprise`, `/enterprise/edit/<id>`, `/enterprise/delete/<id>`, `/enterprise/reset/<id>`, `/enterprise/delete/permanent/<id>` | Administración de empresas con borrado lógico y permanente. |
| Gestión de Datos — Importar DIVIPOLA | `/importar-administrativos` | Carga masiva de la división político-administrativa de Colombia (departamentos, municipios, veredas). |
| Gestión de Usuarios | `/users`, `/users/create`, `/users/edit/<keycloak_id>`, `/users/password/<keycloak_id>`, `/users/delete/<keycloak_id>` | Administración de usuarios sincronizados con Keycloak. |
| Gestión de Usuarios — Roles | `/roles/`, `/roles/create`, `/roles/get/<role_id>`, `/roles/edit/<role_id>`, `/roles/delete/<role_id>` | Gestión de roles y permisos almacenados en MongoDB. |

## 🔒 Autenticación
La autenticación se apoya en Keycloak mediante OAuth/OIDC y Authlib. El servicio [src/services/oauth_service.py](src/services/oauth_service.py) configura los endpoints de autorización, token, userinfo, JWKS y logout usando `KEYCLOAK_SERVER_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID` y `KEYCLOAK_CLIENT_SECRET`.

El flujo real implementado es este:

1. El usuario entra en `/login/keycloak` y es redirigido a Keycloak.
2. Keycloak retorna al callback `/auth/callback` con un código de autorización.
3. La aplicación intercambia el código por tokens, obtiene la información del usuario y valida el `access_token` contra la API de GanaBosques en `API_BASE_URL/auth/token/validate`.
4. Solo se permite el acceso si la respuesta indica que el usuario es administrador (`user_db.admin = true`).
5. La sesión guarda `access_token`, `refresh_token`, `id_token` y `user_data` en Flask-Login.
6. Un `before_request` global protege casi todas las rutas del panel y redirige al login si no existe sesión activa.
7. El cierre de sesión limpia la sesión local y genera la URL de logout de Keycloak con `id_token_hint` y `post_logout_redirect_uri`.

## 🧪 Testing
El proyecto corre sus pruebas con `pytest`, cubriendo configuración, decoradores de autenticación, el servicio OAuth, el modelo de usuario, helpers de importación geoespacial y formularios. El comando localmente es:

```bash
python -m pytest
```

Este mismo repositorio tiene dos pipelines de CI configurados, cada uno con su propio comando:

- **GitHub Actions** (`.github/workflows/pipeline.yaml`):
  ```bash
  python -m pytest
  ```
- **Azure DevOps** (`pipelines/pipeline-test.yml`):
  ```bash
  python -m pytest --junitxml=test-results.xml
  ```

<!-- TODO: confirmar si alguno de los dos pipelines usa flags adicionales (ej. --maxfail, --disable-warnings) distintos a los mostrados arriba -->

## 👥 Mantenedores / Licencia
Mantenedores: [CIAT-DAPA](https://github.com/CIAT-DAPA) / Alliance Bioversity-CIAT.

- [stevensotelo](https://github.com/stevensotelo)
- [victor-993](https://github.com/victor-993)