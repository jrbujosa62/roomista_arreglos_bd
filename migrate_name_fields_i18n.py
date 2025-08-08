# C:/proyecto-roomista/data_integrity_toolkit/migrate_i18n_schema.py
# -*- coding: utf-8 -*-

"""
# migrate_i18n_schema.py
#
################################################################################
#                                                                              #
#        SCRIPT DE MIGRACIÓN PARA REFACTORIZAR CAMPOS MULTILINGÜES             #
#                                                                              #
################################################################################
#
# DESCRIPCIÓN FUNCIONAL:
#
# Este es un script de ejecución ÚNICA diseñado para migrar la estrategia de
# internacionalización (i18n) de los datos en Firestore. El objetivo es pasar
# de un esquema con campos duplicados con sufijos de idioma (ej. 'titleEn',
# 'titleEs') a un esquema más limpio con un único campo de contenido y un
# nuevo campo 'sourceLanguage' que define el idioma original.
#
# El script realiza las siguientes tareas específicas:
#
# 1.  ELIMINACIÓN DE CAMPOS EN ESPAÑOL (_es):
#     - Para cada documento, elimina los campos que terminan en "Es",
#       ya que su contraparte en inglés ("En") se considerará la fuente
#       de verdad.
#
# 2.  RENOMBRADO DE CAMPOS EN INGLÉS (_en):
#     - Renombra todos los campos que terminan en "En" eliminando el sufijo.
#       Por ejemplo, 'titleEn' se convierte en 'title' y conserva su valor.
#
# 3.  ADICIÓN DEL CAMPO 'sourceLanguage':
#     - Añade un nuevo campo 'sourceLanguage' con el valor "en" a cada
#       documento procesado, estableciendo el inglés como el idioma de origen.
#
# COLECCIONES AFECTADAS Y OPERACIONES ESPECÍFICAS:
#
#   A. Para la colección `listings`:
#      - ELIMINA: `descriptionEs`, `propertyStrengthsEs`, `tenantStrengthsSearchedEs`, `titleEs`.
#      - RENOMBRA: `descriptionEn` -> `description`, `propertyStrengthsEn` -> `propertyStrengths`, etc.
#      - AÑADE: `sourceLanguage: "en"`.
#
#   B. Para la colección `users`:
#      - ELIMINA: `bioEs`, `flatmateTraitsEs`, `genderEs`, `professionEs`, etc.
#      - RENOMBRA: `bioEn` -> `bio`, `flatmateTraitsEn` -> `flatmateTraits`, etc.
#      - AÑADE: `sourceLanguage: "en"`.
#
# SEGURIDAD Y EJECUCIÓN:
#
# - IDEMPOTENTE: El script no causará daño si se ejecuta varias veces.
# - EFICIENCIA: Usa escrituras por lotes (Batched Writes) de Firestore.
# - ¡IMPORTANTE!: Realiza una copia de seguridad (backup) de tu base de
#   datos antes de ejecutar este script.
#
# CÓMO EJECUTAR:
# - Asegúrate de que el archivo `config.py` con las credenciales de Firebase
#   esté en el mismo directorio.
# - Ejecuta el script desde la terminal: `python migrate_i18n_schema.py`
#
"""


import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Obtenemos la ruta raíz del proyecto ('proyecto-roomista')
#    __file__ es la ruta al script actual.
#    El primer os.path.dirname() nos da su directorio (data_integrity_toolkit).
#    El segundo os.path.dirname() nos sube al directorio padre (la raíz del proyecto).
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# 2. Añadimos la ruta raíz a la lista de rutas donde Python busca módulos.
sys.path.insert(0, project_root)

try:
    # 3. Ahora Python puede encontrar la carpeta 'config' en la raíz y
    #    desde ahí importar el módulo 'config.py'.
    from config import config
except ImportError:
    print("Error: El archivo de configuración 'config/config.py' no fue encontrado.")
    print(f"Se intentó buscar en la ruta: {os.path.join(project_root, 'config')}")
    sys.exit(1)


def migrate_listings(db: firestore.client):
    """
    Migra los documentos de la colección 'listings' al nuevo esquema de i18n.
    """
    print("\n--- Iniciando migración i18n de la colección 'listings' ---")
    listings_ref = db.collection('listings')
    docs = listings_ref.stream()
    batch = db.batch()
    docs_processed = 0

    fields_to_delete = [
        'description_es', 'propertyStrengths_es', 'tenantStrengthsSearched_es', 'title_es','sourceLanguage'
    ]
    fields_to_rename = {
        'availableUntil_unix': 'available_until_unix',
        'availableUntilUnix': 'available_until_unix',
        'availableUntil': 'available_until',
        'availableFromUnix': 'available_from_unix',
        'createdAtUnix': 'created_at_unix',
        'createdAt': 'created_at',  
        'propertyStrengths': 'property_strengths',
        'tenantStrengthsSearched': 'tenant_strengths_searched',
        'updatedAtUnix': 'updated_at_unix',
        'updatedAt': 'updated_at' 
    }

    for doc in docs:
        update_data = {}
        data = doc.to_dict()

        # 1. Añadir 'sourceLanguage' si no existe
        if 'sourceLanguage' not in data:
            update_data['source_language'] = 'en'
        
        # 2. Renombrar campos 'En' a su nueva versión sin sufijo
        for old_name, new_name in fields_to_rename.items():
            if old_name in data:
                update_data[new_name] = data[old_name]
                update_data[old_name] = firestore.DELETE_FIELD
        
        # 3. Eliminar campos 'Es'
        for field in fields_to_delete:
            if field in data:
                update_data[field] = firestore.DELETE_FIELD
        
        if update_data:
            print(f"  -> Planificando actualización para listing '{doc.id}'")
            batch.update(doc.reference, update_data)
            docs_processed += 1
            if docs_processed % 499 == 0:
                print("--- Lote lleno, ejecutando escrituras... ---")
                batch.commit()
                batch = db.batch()
    
    if docs_processed > 0:
        print("--- Ejecutando escrituras finales del lote... ---")
        batch.commit()
        print(f"✅ Migración i18n de {docs_processed} documentos en 'listings' completada.")
    else:
        print("✅ No se necesitaron actualizaciones de i18n en 'listings'.")


def migrate_users(db: firestore.client):
    """
    Migra los documentos de la colección 'users' al nuevo esquema de i18n.
    """
    print("\n--- Iniciando migración i18n de la colección 'users' ---")
    users_ref = db.collection('users')
    docs = users_ref.stream()
    batch = db.batch()
    docs_processed = 0

    fields_to_delete = [
        'bio_es', 'flatmateTraitsEs', 'gender_es', 'profession_es',
        'propertyStrengthsSearched_es', 'strengthsRoommate_es', 'tenantStrengths_es','sourceLanguage',
    ]
    
    fields_to_rename = {
        'availableUntil_unix': 'available_until_unix',
        'availableUntil': 'available_until',
        'availableFromUnix': 'available_from_unix',
        'createdAtUnix': 'created_at_unix',
        'createdAt': 'created_at',
        'desiredMoveInDateUnix': 'desired_move_in_date_unix',
        'desiredMoveInDate': 'desired_move_in_date',
        'desiredMoveOutDateUnix': 'desired_move_out_date_unix',
        'desiredMoveOutDate': 'desired_move_out_date',
        'flatmateTraits': 'flatmate_traits',
        'isStudent': 'is_student',
        'languagesSpoken': 'languages_spoken',
        'profileStatus': 'profile_status', 
        'propertyStrengths': 'property_strengths',
        'propertyStrengthsSearched': 'property_strengths_searched',
        'strengthsRoommate': 'strengths_roommate',
        'tenantStrengths': 'tenant_strengths',
        'updatedAtUnix': 'updated_at_unix',
        'updatedAt': 'updated_at'
    }

    for doc in docs:
        update_data = {}
        data = doc.to_dict()

        # 1. Añadir 'sourceLanguage' si no existe
        if 'sourceLanguage' not in data:
            update_data['source_language'] = 'en'

        # 2. Renombrar campos 'En'
        for old_name, new_name in fields_to_rename.items():
            if old_name in data:
                update_data[new_name] = data[old_name]
                update_data[old_name] = firestore.DELETE_FIELD

        # 3. Eliminar campos 'Es'
        for field in fields_to_delete:
            if field in data:
                update_data[field] = firestore.DELETE_FIELD

        if update_data:
            print(f"  -> Planificando actualización para user '{doc.id}'")
            batch.update(doc.reference, update_data)
            docs_processed += 1
            if docs_processed % 499 == 0:
                print("--- Lote lleno, ejecutando escrituras... ---")
                batch.commit()
                batch = db.batch()
    
    if docs_processed > 0:
        print("--- Ejecutando escrituras finales del lote... ---")
        batch.commit()
        print(f"✅ Migración i18n de {docs_processed} documentos en 'users' completada.")
    else:
        print("✅ No se necesitaron actualizaciones de i18n en 'users'.")


def main():
    """
    Función principal que inicializa Firebase y ejecuta todas las migraciones.
    """
    try:
        # Asegúrate de que el path al archivo de credenciales sea correcto
        if not os.path.exists(config.FIREBASE_SERVICE_ACCOUNT_KEY):
            print(f"Error: No se encuentra el archivo de credenciales de Firebase: {config.FIREBASE_SERVICE_ACCOUNT_KEY}")
            sys.exit(1)
        
        # Inicializa la app de Firebase solo si no ha sido inicializada antes
        if not firebase_admin._apps:
            cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT_KEY)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
    except Exception as e:
        print(f"Error crítico al inicializar Firebase: {e}")
        sys.exit(1)

    migrate_listings(db)
    migrate_users(db)
    print("\n--- Migración de esquemas i18n completada ---")


if __name__ == "__main__":
    main()