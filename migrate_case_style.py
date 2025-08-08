# C:/proyecto-roomista/data_integrity_toolkit/migrate_case_style.py
# -*- coding: utf-8 -*-

"""
# migrate_case_style.py
#
################################################################################
#                                                                              #
#      SCRIPT DE MIGRACIÓN PARA CORREGIR NOMENCLATURA DE CAMPOS                #
#                      DE camelCase a snake_case                               #
#                                                                              #
################################################################################
#
# DESCRIPCIÓN FUNCIONAL:
#
# Este es un script de ejecución ÚNICA diseñado para estandarizar los nombres de
# los campos en Firestore, convirtiéndolos de formato camelCase a snake_case,
# de acuerdo con el esquema definido en 'roomista-data-schema.json'.
#
# El script realiza las siguientes tareas específicas:
#
# 1.  ITERA sobre cada documento en las colecciones 'listings' y 'users'.
# 2.  RENOMBRA los campos:
#     - Para cada campo con nombre en camelCase, crea un nuevo campo en
#       snake_case con el mismo valor.
#     - Elimina el campo original en camelCase.
#
# COLECCIONES AFECTADAS Y OPERACIONES ESPECÍFICAS:
#
#   A. Para la colección `listings`:
#      - RENOMBRA: `acceptsStudents` -> `accepts_students`, `availableFrom` -> `available_from`, etc.
#
#   B. Para la colección `users`:
#      - RENOMBRA: `desiredMoveInDate` -> `desired_move_in_date`, `hasPets` -> `has_pets`, etc.
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
#   esté en el directorio correcto.
# - Ejecuta el script desde la terminal: `python migrate_case_style.py`
#
"""

import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Configuración de la ruta para importar desde la carpeta 'config'
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from config import config
except ImportError:
    print("Error: El archivo de configuración 'config/config.py' no fue encontrado.")
    print(f"Se intentó buscar en la ruta: {os.path.join(project_root, 'config')}")
    sys.exit(1)


# --- MAPEADOS DE CAMPO ---
# Define aquí todos los campos que necesitan ser renombrados para cada colección.

LISTINGS_FIELD_MAP = {
    'acceptsStudents': 'accepts_students',
    'availableFrom': 'available_from',
    'availableFrom_unix': 'available_from_unix',
    'bathroomCount': 'bathroom_count',
    'coverImageUrl': 'cover_image_url',
    'createdAt': 'created_at',
    'createdAt_unix': 'created_at_unix',
    'descriptionEn': 'description_en', # Asumiendo que aún no has corrido el script i18n
    'descriptionEs': 'description_es',
    'hasAC': 'has_ac',
    'hasDoorman': 'has_doorman',
    'hasElevator': 'has_elevator',
    'hasLivingRoom': 'has_living_room',
    'hasWifi': 'has_wifi',
    'imageUrls': 'image_urls',
    'isFurnished': 'is_furnished',
    'landlordName': 'landlord_name',
    'landlordUid': 'landlord_uid',
    'minimumStayMonths': 'minimum_stay_months',
    'petsAllowed': 'pets_allowed',
    'propertyStrengthsEn': 'property_strengths_en',
    'propertyStrengthsEs': 'property_strengths_es',
    'rentalType': 'rental_type',
    'roomCount': 'room_count',
    'smokingAllowed': 'smoking_allowed',
    'sourceLanguage': 'source_language',
    'tenantStrengthsSearchedEn': 'tenant_strengths_searched_en',
    'tenantStrengthsSearchedEs': 'tenant_strengths_searched_es',
    'titleEn': 'title_en',
    'titleEs': 'title_es',
    'updatedAt': 'updated_at',
    'updatedAt_unix': 'updated_at_unix'
}

USERS_FIELD_MAP = {
    'bioEn': 'bio_en',
    'bioEs': 'bio_es',
    'createdAt': 'created_at',
    'createdAt_unix': 'created_at_unix',
    'displayName': 'display_name',
    'idVerificationStatus': 'id_verification_status',
    'isVerified': 'is_verified',
    'photoURL': 'photo_url',
    'propertyStrengthsSearchedEn': 'property_strengths_searched_en',
    'propertyStrengthsSearchedEs': 'property_strengths_searched_es',
    'sourceLanguage': 'source_language',
    'tenantStrengthsEn': 'tenant_strengths_en',
    'tenantStrengthsEs': 'tenant_strengths_es',
    'desiredMoveInDate': 'desired_move_in_date',
    'desiredMoveInDate_unix': 'desired_move_in_date_unix',
    'desiredMoveOutDate': 'desired_move_out_date',
    'desiredMoveOutDate_unix': 'desired_move_out_date_unix',
    'genderEn': 'gender_en',
    'genderEs': 'gender_es',
    'hasPets': 'has_pets',
    'minimumStayMonths': 'minimum_stay_months',
    'needsAC': 'needs_ac',
    'needsElevator': 'needs_elevator',
    'needsFurnished': 'needs_furnished',
    'needsLivingRoom': 'needs_living_room',
    'needsWifi': 'needs_wifi',
    'professionEn': 'profession_en',
    'professionEs': 'profession_es',
    'rentalType': 'rental_type',
    'roomistaPhotoURL': 'roomista_photo_url',
    'searchAddress': 'search_address',
    'searchBudget': 'search_budget',
    'searchLocation': 'search_location',
    'searchRadius': 'search_radius',
    'strengthsRoommateEn': 'strengths_roommate_en',
    'strengthsRoommateEs': 'strengths_roommate_es'
}


def migrate_collection(db: firestore.client, collection_name: str, field_map: dict):
    """
    Migra los documentos de una colección para cambiar los nombres de los campos de camelCase a snake_case.
    """
    print(f"\n--- Iniciando migración de nombres de campo para la colección '{collection_name}' ---")
    collection_ref = db.collection(collection_name)
    docs = collection_ref.stream()
    batch = db.batch()
    docs_processed = 0
    updates_made = False

    for doc in docs:
        update_data = {}
        data = doc.to_dict()

        for old_name, new_name in field_map.items():
            if old_name in data:
                # Se encontró un campo para renombrar
                updates_made = True
                update_data[new_name] = data[old_name]
                update_data[old_name] = firestore.DELETE_FIELD
        
        if update_data:
            print(f"  -> Planificando actualización para {collection_name[:-1]} '{doc.id}'")
            batch.update(doc.reference, update_data)
            docs_processed += 1
            if docs_processed % 499 == 0:
                print("--- Lote lleno, ejecutando escrituras... ---")
                batch.commit()
                batch = db.batch()
    
    if docs_processed > 0:
        print("--- Ejecutando escrituras finales del lote... ---")
        batch.commit()
        print(f"✅ Migración de {docs_processed} documentos en '{collection_name}' completada.")
    
    if not updates_made:
         print(f"✅ No se necesitaron actualizaciones de nombres de campo en '{collection_name}'.")


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

    # Ejecutar la migración para cada colección
    migrate_collection(db, 'listings', LISTINGS_FIELD_MAP)
    migrate_collection(db, 'users', USERS_FIELD_MAP)

    print("\n--- Migración de camelCase a snake_case completada ---")


if __name__ == "__main__":
    main()