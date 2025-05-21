# GanaBosques Web Admin

**GanaBosques Web Admin** es una aplicación web destinada a usuarios con permisos administrativos dentro del sistema GanaBosques. Su propósito es facilitar la administración de usuarios, la importación de datos clave (como capas espaciales y proveedores), y la visualización de información geoespacial y riesgos asociados a la deforestación.

## 🧩 Funcionalidades principales

- 📥 **Importación de datos espaciales** al sistema y publicación automática en GeoServer.
- 🧾 **Carga y verificación de códigos SIT de proveedores** con asignación por empresa y año.
- 👥 **Gestión de usuarios y roles** 
- 🗺️ **Visualización de mapas y riesgos** 

## ⚙️ Tecnologías utilizadas

- **Python 3.10+**
- **Flask** – Framework web ligero
- **MongoDB** – Base de datos NoSQL
- **MongoEngine** – ORM para MongoDB
- **Bootstrap 5** – Interfaz responsiva
- **GeoServer** – Publicación de capas geoespaciales
- **Docker** – Para levantar servicios como GeoServer y MongoDB

## 📁 Estructura del proyecto

ganabosques_web_admin/
│
├── src/
│ ├── app.py # App principal
│ ├── config.py # Configuraciones dinámicas
│ ├── routes/
│ │ ├── home.py
│ │ ├── spatial_data_management.py
│ │ └── suppliers_data_management.py
│ ├── static/
│ │ └── img/
│ │ └── banner_vacas.png
│ ├── templates/
│ │ ├── base.html
│ │ ├── home.html
│ │ ├── import_suppliers.html
│ │ └── upload.html
│ ├── data/
│ │ └── layers/
│ │ ├── administrative_risk_annual/
│ │ ├── mosaic_properties/
│ │ │ ├── indexer.properties
│ │ │ └── timeregex.properties
│ │ └── smbyc/
│ └── tmp/
│
├── uploaded_codes/ # Códigos SIT cargados
├── uploaded_files/ # Archivos espaciales cargados
├── config.py # Configuración según entorno
├── requirements.txt # Lista de dependencias
├── .env # Variables de entorno (no subir)
└── README.md

## 🚀 Instalación y ejecución local
###1. Clona el repositorio
git clone https://github.com/CIAT-DAPA/ganabosques_web_admin.git
cd ganabosques_web_admin

###2.Crea entorno virtual (opcional pero recomendado)
python -m venv env
source env/bin/activate        # En Linux/macOS
env\Scripts\activate           # En Windows

###3.Instala las dependencias
pip install -r requirements.txt

###4.Crea el archivo .env
cp .env.example .env    # o créalo manualmente con las variables necesarias

###5.Inicia la aplicación
cd src
python app.py
Accede a: http://localhost:5000
