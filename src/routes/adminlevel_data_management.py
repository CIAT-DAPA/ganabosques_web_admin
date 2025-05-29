from xml.etree.ElementTree import ParseError
from datetime import datetime
import pandas as pd
from ganabosques_orm.collections.adm1 import Adm1
from ganabosques_orm.collections.adm2 import Adm2
from ganabosques_orm.collections.adm3 import Adm3
from ganabosques_orm.auxiliaries.log import Log
import math

def importar_desde_csv(path, nivel='todo'):

    # Intentar abrir con utf-8, y si falla, usar latin1
    try:
        df = pd.read_csv(path, index_col=0, encoding='utf-8')
    except UnicodeDecodeError:
        print("Error al leer con UTF-8. Reintentando con 'latin1'...")
        try:
            df = pd.read_csv(path, index_col=0, encoding='latin1')
        except (UnicodeDecodeError, ParseError) as e:
            print("No se pudo leer el archivo con 'latin1' tampoco.")
            print(f"Detalles del error: {e}") 
            return

    nivel = nivel.lower()

    requeridos = {
        'departamento': ['COD_DEPARTAMENTO', 'NOMBRE_DEPARTAMENTO'],
        'municipio': ['COD_DEPARTAMENTO', 'COD_MUNICIPIO', 'NOMBRE_MUNICIPIO'],
        'vereda': ['COD_MUNICIPIO', 'COD_VEREDA', 'NOMBRE_VEREDA']
    }

    # Construir conjunto de columnas requeridas en base al nivel
    columnas_necesarias = set()
    if nivel == 'todo':
        for campos in requeridos.values():
            columnas_necesarias.update(campos)
    else:
        columnas_necesarias.update(requeridos[nivel])

    # Verificar columnas
    faltantes = [col for col in columnas_necesarias if col not in df.columns]
    if faltantes:
        print(f"No se puede procesar. Faltan columnas: {faltantes}")
        raise ValueError(f"No se puede procesar. Faltan columnas: {faltantes}")

    # Recorrer solo una vez
    for _, row in df.iterrows():
        if nivel in ['departamento', 'todo']:
            procesar_fila_departamento(row)
        if nivel in ['municipio', 'todo']:
            procesar_fila_municipio(row)
        if nivel in ['vereda', 'todo']:
            procesar_fila_vereda(row)

def get_log():
    now = datetime.now()
    return Log(enable=True, created=now, updated=now)


def procesar_fila_departamento(row):
    ext_id = convert_id(row['COD_DEPARTAMENTO'])
    name = row['NOMBRE_DEPARTAMENTO']

    if not ext_id or pd.isna(ext_id):
        print("Departamento con código vacío. No se crea.")
        return
    if not name or pd.isna(name):
        print(f"Departamento sin nombre para código {ext_id}. No se crea.")
        return
    
    if Adm1.objects(ext_id=ext_id).first():
        print(f"Departamento {ext_id} {name} ya existe. No se crea de nuevo.")
    else:
        Adm1(name=name, ext_id=ext_id, log=get_log()).save()
        print(f"Departamento {ext_id} creado con nombre '{name}'.")

def procesar_fila_municipio(row):
    cod_dep = convert_id(row['COD_DEPARTAMENTO'])
    cod_mpio = convert_id(row['COD_MUNICIPIO'])
    nombre_mpio = row['NOMBRE_MUNICIPIO']

    if not cod_dep or pd.isna(cod_dep):
        print("Municipio sin código de departamento. No se crea.")
        return
    if not cod_mpio or pd.isna(cod_mpio):
        print("Municipio con código vacío. No se crea.")
        return
    if not nombre_mpio or pd.isna(nombre_mpio):
        print(f"Municipio sin nombre para código {cod_mpio}. No se crea.")
        return
    
    adm1 = Adm1.objects(ext_id=cod_dep).first()
    if not adm1:
        print(f"Departamento {cod_dep} no existe. Municipio {cod_mpio} '{nombre_mpio}' no se crea.")
        return
    if Adm2.objects(ext_id=cod_mpio).first():
        print(f"Municipio {cod_mpio} {nombre_mpio} ya existe. No se crea de nuevo.")
    else:
        Adm2(name=nombre_mpio, ext_id=cod_mpio, adm1_id=adm1, log=get_log()).save()
        print(f"Municipio {cod_mpio} creado con nombre '{nombre_mpio}'.")

def procesar_fila_vereda(row):
    cod_mpio = convert_id(row['COD_MUNICIPIO'])
    cod_vereda = convert_id(row['COD_VEREDA'])
    nombre_vereda = row['NOMBRE_VEREDA']

    if not cod_mpio or pd.isna(cod_mpio):
        print("Vereda sin código de municipio. No se crea.")
        return
    if not cod_vereda or pd.isna(cod_vereda):
        print("Vereda con código vacío. No se crea.")
        return
    if not nombre_vereda or pd.isna(nombre_vereda):
        print(f"Vereda sin nombre para código {cod_vereda}. No se crea.")
        return

    adm2 = Adm2.objects(ext_id=cod_mpio).first()
    if not adm2:
        print(f"Municipio {cod_mpio} no existe. Vereda {cod_vereda} '{nombre_vereda}' no se crea.")
        return

    if Adm3.objects(ext_id=cod_vereda).first():
        print(f"Vereda {cod_vereda} {nombre_vereda} ya existe. No se crea de nuevo.")
    else:
        Adm3(name=nombre_vereda, ext_id=cod_vereda, adm2_id=adm2, log=get_log()).save()
        print(f"Vereda {cod_vereda} creada con nombre '{nombre_vereda}'.")

def convert_id(value):
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
        return str(int(float(value)))
    except (ValueError, TypeError):
        return None
