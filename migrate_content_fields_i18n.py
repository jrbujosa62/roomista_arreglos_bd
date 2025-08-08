# C:/proyecto-roomista/data_integrity_toolkit/migrate_content_fields_i18n_sch.py
# -*- coding: utf-8 -*-

"""
# migrate_content_fields_i18n_sch.py
#
################################################################################
#                                                                              #
#    SCRIPT DE MIGRACIÓN PARA ESTANDARIZAR EL CONTENIDO DE CAMPOS (i18n)       #
#                                                                              #
################################################################################
#
# DESCRIPCIÓN FUNCIONAL:
#
# Este es un script de ejecución ÚNICA diseñado para estandarizar el contenido
# de ciertos campos en Firestore. El objetivo es traducir valores heredados
# (ej. en español) a los valores estandarizados definidos en el esquema
# de datos (ej. en inglés), asegurando la consistencia a través de la base de datos.
#
# El script utiliza un mapa de conversión interno para realizar las traducciones.
#
# TAREAS ESPECÍFICAS:
#
# 1.  ITERA sobre cada documento en las colecciones especificadas ('users', 'listings').
# 2.  VERIFICA el contenido de campos predefinidos.
# 3.  MANEJA CAMPOS DE TEXTO (string): Si el valor del campo coincide con una clave
#     en el mapa de conversión (ej. 'role' == 'inquilino'), lo actualiza al
#     nuevo valor ('tenant').
# 4.  MANEJA CAMPOS DE LISTA (list): Para campos que son listas (ej. 'property_strengths'),
#     itera sobre cada elemento de la lista y lo traduce si encuentra una
#     correspondencia en el mapa.
#
# SEGURIDAD Y EJECUCIÓN:
#
# - IDEMPOTENTE: El script está diseñado para no causar cambios si se ejecuta
#   múltiples veces sobre datos ya migrados.
# - EFICIENCIA: Utiliza escrituras por lotes (Batched Writes) de Firestore para
#   minimizar el número de operaciones de escritura.
# - ¡IMPORTANTE!: Realiza una copia de seguridad (backup) de tu base de
#   datos antes de ejecutar este script.
#
# CÓMO EJECUTAR:
# - Asegúrate de que el archivo `config.py` con las credenciales de Firebase
#   esté en el directorio `config` en la raíz del proyecto.
# - Ejecuta el script desde la terminal: `python migrate_content_fields_i18n_sch.py`
#
"""

import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Obtenemos la ruta raíz del proyecto ('proyecto-roomista')
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Añadimos la ruta raíz a la lista de rutas donde Python busca módulos.
sys.path.insert(0, project_root)

try:
    # 3. Importamos la configuración de Firebase
    from config import config
except ImportError:
    print("Error: El archivo de configuración 'config/config.py' no fue encontrado.")
    print(f"Se intentó buscar en la ruta: {os.path.join(project_root, 'config')}")
    sys.exit(1)


# ==============================================================================
# MAPA DE CONVERSIÓN DE CONTENIDO
# ------------------------------------------------------------------------------
# Define las traducciones de español a inglés para los valores de los campos.
# La estructura está anidada por colección y luego por nombre de campo.
# ==============================================================================
CONTENT_CONVERSION_MAP = {
    "users": {
        "flatmate_traits": {
            "Independencia": "independence",
            "Respeto": "respect",
            "Confianza": "trustworthiness",
            "Limpieza": "cleanliness",
            "Sociabilidad": "sociability"
        },
        "gender": {
            "Hombre": "male",
            "Mujer": "female",
            "Otro": "other"
        },
        "profile_status": {
            "iniciado": "started",
            "documento_creado": "document_created",
            "completado": "completed",
            "fallido": "failed"
        },
        "property_strengths_searched": {
            "Encanto/Estilo": "charm_style",
            "Insonorización": "sound_proofing",
            "Luminosidad": "brightness",
            "Vistas": "views",
            "Ambiente comunitario": "community_atmosphere",
            "Tamaño": "size"
        },
        "rental_type": {
            "propiedadEntera": "entire_property",
            "habitacion": "room"
        },
        "role": {
            "inquilino": "tenant",
            "casero": "landlord"
        },
        "strengths_roommate": {
            "Flexibilidad y adaptación": "flexibility_and_adaptation",
            "Comunicación abierta": "open_communication",
            "Aporto buen ambiente": "i_bring_a_good_atmosphere",
            "Respetuoso con el espacio": "respectful_of_space",
            "Responsabilidad doméstica": "domestic_responsibility",
            "Organización y limpieza": "organization_and_cleanliness"
        },
        "tenant_strengths": {
            "Contractual Responsibility": "contractual_responsibility",
            "Respect for the Community": "community_respect",
            "Property care": "property_care",
            "Clear Communication": "clear_communication"
        },
        "id_verification_status": {
            "Verified": "verified",
            "Pending": "pending",
            "Not_started": "not_started",
            "Failed": "failed"
        }
    },
    "listings": {
        "property_strengths": {
            "Charm/Style": "charm_style",
            "Soundproofing": "sound_proofing",
            "Brightness": "brightness",
            "Views": "views",
            "Community Atmosphere": "community_atmosphere",
            "Size": "size"
        },
        "rental_type": {
            "entireProperty": "entire_property",
            "room": "room"
        },
        "tenant_strengths_searched": {
            "Contractual Responsibility": "contractual_responsibility",
            "respect_for_the_community": "community_respect",
            "Property care": "property_care",
            "Clear Communication": "clear_communication"
        }
    }
}


def migrate_collection_content(db: firestore.client, collection_name: str, conversion_rules: dict):
    """
    Migra el contenido de los documentos de una colección específica.

    Args:
        db: Cliente de Firestore.
        collection_name: Nombre de la colección a migrar.
        conversion_rules: Diccionario con las reglas de conversión para esta colección.
    """
    print(f"\n--- Iniciando migración de contenido para la colección '{collection_name}' ---")
    collection_ref = db.collection(collection_name)
    docs = collection_ref.stream()
    batch = db.batch()
    docs_processed = 0
    updates_planned = 0

    for doc in docs:
        doc_data = doc.to_dict()
        update_payload = {}
        
        # Iterar sobre cada campo que tiene una regla de conversión
        for field, conversion_map in conversion_rules.items():
            if field not in doc_data:
                continue

            current_value = doc_data[field]
            made_a_change = False

            # --- Lógica para campos de tipo LISTA ---
            if isinstance(current_value, list):
                new_list = []
                for item in current_value:
                    # Traduce el item si está en el mapa, si no, lo deja como está
                    translated_item = conversion_map.get(item, item)
                    new_list.append(translated_item)
                    if translated_item != item:
                        made_a_change = True
                
                if made_a_change:
                    update_payload[field] = new_list

            # --- Lógica para campos de tipo STRING ---
            elif isinstance(current_value, str):
                # Traduce el valor si está en el mapa
                translated_value = conversion_map.get(current_value)
                if translated_value:
                    update_payload[field] = translated_value
                    made_a_change = True
        
        if update_payload:
            print(f"  -> Planificando actualización para {collection_name[:-1]} '{doc.id}'. Cambios: {list(update_payload.keys())}")
            batch.update(doc.reference, update_payload)
            updates_planned += 1
            if updates_planned % 499 == 0:
                print("--- Lote lleno, ejecutando escrituras... ---")
                batch.commit()
                batch = db.batch()
        
        docs_processed += 1

    if updates_planned > 0:
        print("--- Ejecutando escrituras finales del lote... ---")
        batch.commit()
        print(f"✅ Migración de contenido para {updates_planned} de {docs_processed} documentos en '{collection_name}' completada.")
    else:
        print(f"✅ No se necesitaron actualizaciones de contenido en '{collection_name}'.")


def main():
    """
    Función principal que inicializa Firebase y ejecuta todas las migraciones de contenido.
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

    # Ejecutar la migración para cada colección definida en el mapa de conversión
    if "listings" in CONTENT_CONVERSION_MAP:
        migrate_collection_content(db, "listings", CONTENT_CONVERSION_MAP["listings"])

    if "users" in CONTENT_CONVERSION_MAP:
        migrate_collection_content(db, "users", CONTENT_CONVERSION_MAP["users"])
    
    print("\n--- Migración de contenido i18n completada ---")


if __name__ == "__main__":
    main()