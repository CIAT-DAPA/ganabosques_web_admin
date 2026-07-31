docker build --no-cache -t ganabosques-web-admin .
# Guía de Docker - Ganabosques Web Admin

## Descripción general

Ganabosques Web Admin es una aplicación web Flask orientada a usuarios administrativos de la plataforma GanaBosques. Permite iniciar sesión con Keycloak, administrar usuarios y roles, cargar archivos, integrar información con MongoDB y GeoServer, y validar tokens contra la API backend.

Esta aplicación está pensada para ejecutarse en contenedor, de forma que el entorno sea consistente en desarrollo, pruebas y despliegues similares a producción, sin depender de un entorno virtual local.

## Qué incluye la imagen Docker

El [Dockerfile](Dockerfile) actual construye la imagen con:

- `python:3.12-slim` como base.
- Paquetes del sistema necesarios para compilación y librerías geoespaciales.
- Dependencias de Python definidas en [src/requirements.txt](src/requirements.txt).
- Todo el proyecto copiado en `/app`.
- Carpetas de carga creadas dentro del contenedor.
- `gunicorn` como punto de entrada para producción.

La aplicación expone Flask en el puerto `5000` dentro del contenedor.

## Construcción de la imagen

Desde la raíz del proyecto:

```bash
docker build -t ganabosques-web-admin .
```

Verifica que la imagen se creó correctamente:

```bash
docker images ganabosques-web-admin
```

## Variables de entorno

La configuración de la aplicación se lee desde variables de entorno definidas en [config.py](config.py) y, normalmente, en el archivo `.env`.

### Variables más importantes

| Variable | Descripción |
| --- | --- |
| `SECRET_KEY` | Clave secreta de Flask para sesiones y mensajes flash |
| `MONGO_URI` | Cadena de conexión a MongoDB |
| `MONGO_DB_NAME` | Nombre de la base de datos MongoDB |
| `API_BASE_URL` | URL de la API backend usada para validar tokens |
| `GEOSERVER_URL` | URL REST de GeoServer |
| `GEOSERVER_USER` | Usuario de GeoServer |
| `GEOSERVER_PWD` | Contraseña de GeoServer |
| `GEO_WORKSPACE` | Nombre del workspace de GeoServer |
| `KEYCLOAK_SERVER_URL` | URL base del servidor Keycloak |
| `KEYCLOAK_REALM` | Realm de Keycloak |
| `KEYCLOAK_CLIENT_ID` | ID del cliente configurado en Keycloak |
| `KEYCLOAK_CLIENT_SECRET` | Secreto del cliente Keycloak |
| `DEBUG` | Activa o desactiva el modo debug |
| `HOST` | Host usado cuando se ejecuta localmente con Python |
| `PORT` | Puerto usado cuando se ejecuta localmente con Python |

### Ejemplo de archivo .env

No copies credenciales reales en documentación pública. Usa valores de ejemplo y conserva los secretos reales en tu entorno local.

```env
DEBUG=true
SECRET_KEY=change-me
HOST=0.0.0.0
PORT=5000

MONGO_URI=mongodb://host.docker.internal:27017
MONGO_DB_NAME=ganabosques2

API_BASE_URL=http://host.docker.internal:5001

GEOSERVER_URL=http://host.docker.internal:8600/geoserver/rest/
GEOSERVER_USER=admin
GEOSERVER_PWD=change-me
GEO_WORKSPACE=deforestation

KEYCLOAK_SERVER_URL=https://keycloak.example.com
KEYCLOAK_REALM=GanaBosques
KEYCLOAK_CLIENT_ID=GanaBosques
KEYCLOAK_CLIENT_SECRET=change-me
```

## Ejecución del contenedor

### Opción 1: usando un archivo .env

```bash
docker run -d \
  --name ganabosques-web-admin \
  -p 5000:5000 \
  --env-file .env \
  ganabosques-web-admin
```

### Opción 2: pasando variables una por una

```bash
docker run -d \
  --name ganabosques-web-admin \
  -p 5000:5000 \
  -e SECRET_KEY=change-me \
  -e MONGO_URI=mongodb://host.docker.internal:27017 \
  -e MONGO_DB_NAME=ganabosques2 \
  -e API_BASE_URL=http://host.docker.internal:5001 \
  -e GEOSERVER_URL=http://host.docker.internal:8600/geoserver/rest/ \
  -e GEOSERVER_USER=admin \
  -e GEOSERVER_PWD=change-me \
  -e GEO_WORKSPACE=deforestation \
  -e KEYCLOAK_SERVER_URL=https://keycloak.example.com \
  -e KEYCLOAK_REALM=GanaBosques \
  -e KEYCLOAK_CLIENT_ID=GanaBosques \
  -e KEYCLOAK_CLIENT_SECRET=change-me \
  ganabosques-web-admin
```

## Acceso a la aplicación

Una vez iniciado el contenedor, abre:

```text
http://localhost:5000
```

Esta aplicación no expone Swagger ni ReDoc, porque no es una API FastAPI; es un panel web Flask.

## Persistencia de archivos cargados

La aplicación guarda archivos cargados dentro del contenedor en:

- `/app/uploaded_files`
- `/app/uploaded_codes`

Si quieres conservar esos archivos al recrear el contenedor, monta volúmenes.

### Linux o macOS

```bash
docker run -d \
  --name ganabosques-web-admin \
  -p 5000:5000 \
  --env-file .env \
  -v $(pwd)/uploaded_files:/app/uploaded_files \
  -v $(pwd)/uploaded_codes:/app/uploaded_codes \
  ganabosques-web-admin
```

### Windows PowerShell

```powershell
docker run -d `
  --name ganabosques-web-admin `
  -p 5000:5000 `
  --env-file .env `
  -v ${PWD}\uploaded_files:/app/uploaded_files `
  -v ${PWD}\uploaded_codes:/app/uploaded_codes `
  ganabosques-web-admin
```

## Logs

Ver logs del contenedor:

```bash
docker logs ganabosques-web-admin
```

Seguir logs en tiempo real:

```bash
docker logs -f ganabosques-web-admin
```

Ver las últimas 100 líneas:

```bash
docker logs --tail 100 ganabosques-web-admin
```

## Comandos útiles dentro del contenedor

Ver contenedores activos:

```bash
docker ps
```

Ver variables de entorno dentro del contenedor:

```bash
docker exec -it ganabosques-web-admin env
```

Entrar al shell del contenedor:

```bash
docker exec -it ganabosques-web-admin sh
```

## Actualización de la imagen

Si cambias código o dependencias, reconstruye la imagen:

```bash
docker stop ganabosques-web-admin
docker rm ganabosques-web-admin
docker build --no-cache -t ganabosques-web-admin .
```

Después, vuelve a ejecutar el contenedor con el mismo comando de `docker run`.

## Solución de problemas

### Error de conexión con MongoDB

Si aparece `ServerSelectionTimeoutError`, revisa que `MONGO_URI` apunte a un host accesible desde el contenedor.

Si MongoDB está corriendo en tu máquina local sobre Windows o macOS, `host.docker.internal` suele ser la opción correcta.

### Fallos al validar el token contra la API

La aplicación valida el token usando `API_BASE_URL`.

Si la API backend corre en tu equipo, verifica que el contenedor pueda alcanzar esa URL y que el puerto esté correcto.

### Errores al publicar o actualizar capas en GeoServer

Verifica que `GEOSERVER_URL`, `GEOSERVER_USER`, `GEOSERVER_PWD` y `GEO_WORKSPACE` coincidan con la instancia real de GeoServer.

### El puerto 5000 ya está ocupado

Si el puerto `5000` está en uso, mapea el contenedor a otro puerto:

```bash
docker run -d \
  --name ganabosques-web-admin \
  -p 5001:5000 \
  --env-file .env \
  ganabosques-web-admin
```

Luego abre:

```text
http://localhost:5001
```

## Notas sobre el Dockerfile actual

La imagen ya incluye las dependencias del sistema necesarias para librerías geoespaciales como Rasterio y GDAL, por lo que el contenedor es la forma más consistente de ejecutar el web admin.

Si agregas nuevas dependencias de Python, actualiza [src/requirements.txt](src/requirements.txt) y reconstruye la imagen.
