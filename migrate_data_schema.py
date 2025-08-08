# C:/proyecto-roomista/data_integrity_toolkit/migrate_data_schema.py
# -*- coding: utf-8 -*-

"""
# migrate_data_schema.py
#
################################################################################
#                                                                              #
#              SCRIPT DE MIGRACIÓN DE ESQUEMAS EN FIRESTORE                    #
#                                                                              #
################################################################################
#
# DESCRIPCIÓN FUNCIONAL:
#
# Este es un script de ejecución ÚNICA diseñado para migrar y alinear la
# estructura de los datos en Firestore con la estrategia de datos definitiva
# de la aplicación. Su objetivo es preparar los datos para que sean compatibles
# tanto con las funcionalidades nativas de Firestore como con la indexación
# de alto rendimiento de Algolia.
#
# El script realiza dos tareas principales:
#
# 1.  CREACIÓN DE CAMPOS "_unix" PARA ALGOLIA:
#     - Para los campos de fecha que se usarán en filtros de rango en Algolia,
#       este script crea una versión numérica duplicada con el sufijo "_unix".
#     - Lee un campo de tipo 'Timestamp' de Firestore (ej. 'availableFrom')
#       y genera su contraparte numérica (ej. 'availableFrom_unix') que
#       contiene los segundos de la época de Unix.
#
# 2.  CORRECCIÓN DE TIMESTAMPS HISTÓRICOS:
#     - Corrige los campos de fecha de auditoría (como 'createdAt') que fueron
#       guardados históricamente como 'Number' (en milisegundos).
#     - Lee el valor numérico y lo convierte al tipo 'Timestamp' nativo de
#       Firestore, asegurando la consistencia y legibilidad en la base de datos.
#
# COLECCIONES AFECTADAS Y OPERACIONES ESPECÍFICAS:
#
#   A. Para la colección `listings`:
#      - CREA `availableFrom_unix` (Number) a partir de `availableFrom` (Timestamp).
#      - CREA `availableUntil_unix` (Number) a partir de `availableUntil` (Timestamp).
#      - CORRIGE `createdAt` y `updatedAt` de `Number` a `Timestamp`.
#
#   B. Para la colección `users`:
#      - CREA `desiredMoveInDate_unix` (Number) a partir de `desiredMoveInDate` (Timestamp).
#      - CREA `desiredMoveOutDate_unix` (Number) a partir de `desiredMoveOutDate` (Timestamp).
#      - CORRIGE `createdAt` y `updatedAt` (si existen) de `Number` a `Timestamp`.
#
# SEGURIDAD Y EJECUCIÓN:
#
# - IDEMPOTENTE: El script está diseñado para ser seguro. Si se ejecuta varias
#   veces, no causará daño, ya que solo modifica los campos que cumplen las
#   condiciones de tipo incorrecto.
# - EFICIENCIA: Utiliza escrituras por lotes (Batched Writes) para minimizar
#   el número de operaciones de escritura en Firebase.
# - ¡IMPORTANTE!: Siempre es una buena práctica realizar una copia de seguridad
#   (backup) de tu base de datos de Firestore antes de ejecutar cualquier
#   script de migración masiva.
#
# CÓMO EJECUTAR:
# - Asegúrate de que el archivo `config.py` con las credenciales de Firebase
#   esté en el mismo directorio.
# - Ejecuta el script desde la terminal: `python migrate_data_schema.py`
#
"""

import sys
import os
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore

try:
    import config
except ImportError:
    print("Error: El archivo de configuración 'config.py' no fue encontrado.")
    sys.exit(1)

def migrate_listings(db: firestore.client):
    """
    Migra los documentos de la colección 'listings' al nuevo esquema.
    - Crea campos _unix a partir de Timestamps.
    - Convierte campos de fecha numéricos a Timestamps.
    """
    print("\n--- Iniciando migración de la colección 'listings' ---")
    listings_ref = db.collection('listings')
    docs = listings_ref.stream()
    batch = db.batch()
    docs_processed = 0

    for doc in docs:
        update_data = {}
        data = doc.to_dict()

        # 1. Crear campos _unix a partir de Timestamps existentes
        for field in ['availableFrom', 'availableUntil']:
            if field in data and isinstance(data[field], datetime):
                # .timestamp() devuelve segundos como float, lo convertimos a int
                update_data[f'{field}_unix'] = int(data[field].timestamp())

        # 2. Convertir campos de fecha numéricos a Timestamps de Firestore
        for field in ['createdAt', 'updatedAt']:
            if field in data and isinstance(data[field], (int, float)):
                # Asumimos que el número está en milisegundos
                seconds = data[field] / 1000.0
                update_data[field] = datetime.fromtimestamp(seconds, tz=timezone.utc)
        
        if update_data:
            print(f"  -> Planificando actualización para listing '{doc.id}' con: {update_data}")
            batch.update(doc.reference, update_data)
            docs_processed += 1
            # Los lotes están limitados a 500 operaciones. Hacemos commit si nos acercamos.
            if docs_processed % 499 == 0:
                print("--- Lote lleno, ejecutando escrituras... ---")
                batch.commit()
                batch = db.batch() # Iniciar un nuevo lote
    
    if docs_processed > 0:
        print("--- Ejecutando escrituras finales del lote... ---")
        batch.commit()
        print(f"✅ Migración de {docs_processed} documentos en 'listings' completada.")
    else:
        print("✅ No se necesitaron actualizaciones en 'listings'.")


def migrate_users(db: firestore.client):
    """
    Migra los documentos de la colección 'users' al nuevo esquema.
    """
    print("\n--- Iniciando migración de la colección 'users' ---")
    users_ref = db.collection('users')
    docs = users_ref.stream()
    batch = db.batch()
    docs_processed = 0

    for doc in docs:
        update_data = {}
        data = doc.to_dict()

        # Solo procesar si el rol es 'inquilino' para los campos de fechas deseadas
        if data.get('role') == 'inquilino':
            for field in ['desiredMoveInDate', 'desiredMoveOutDate']:
                 if field in data and isinstance(data[field], datetime):
                    update_data[f'{field}_unix'] = int(data[field].timestamp())
        
        # Convertir createdAt y updatedAt si son numéricos para cualquier usuario
        for field in ['createdAt', 'updatedAt']:
            if field in data and isinstance(data[field], (int, float)):
                seconds = data[field] / 1000.0
                update_data[field] = datetime.fromtimestamp(seconds, tz=timezone.utc)

        if update_data:
            print(f"  -> Planificando actualización para user '{doc.id}' con: {update_data}")
            batch.update(doc.reference, update_data)
            docs_processed += 1
            if docs_processed % 499 == 0:
                print("--- Lote lleno, ejecutando escrituras... ---")
                batch.commit()
                batch = db.batch()
    
    if docs_processed > 0:
        print("--- Ejecutando escrituras finales del lote... ---")
        batch.commit()
        print(f"✅ Migración de {docs_processed} documentos en 'users' completada.")
    else:
        print("✅ No se necesitaron actualizaciones en 'users'.")


def main():
    """
    Función principal que inicializa Firebase y ejecuta todas las migraciones.
    """
    try:
        if not os.path.exists(config.FIREBASE_SERVICE_ACCOUNT_KEY):
            print(f"Error: No se encuentra el archivo de credenciales de Firebase: {config.FIREBASE_SERVICE_ACCOUNT_KEY}")
            sys.exit(1)
        if not firebase_admin._apps:
            cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT_KEY)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        print(f"Error crítico al inicializar Firebase: {e}")
        sys.exit(1)

    migrate_listings(db)
    migrate_users(db)
    print("\n--- Migración de esquemas completada ---")


if __name__ == "__main__":
    main()