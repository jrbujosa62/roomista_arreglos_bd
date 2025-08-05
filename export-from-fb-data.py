# Fichero: export_firebase_data.py
#
# Descripción:
# Este script se conecta a un proyecto de Firebase y realiza dos acciones:
# 1. Exporta todas las colecciones principales de Firestore a ficheros JSON individuales.
# 2. Lista todos los archivos de Firebase Storage y guarda la lista en un fichero JSON.
#
# Uso:
# 1. Coloca tu 'serviceAccountKey.json' en la misma carpeta.
# 2. Ejecuta el script desde la terminal: python export_firebase_data.py

import firebase_admin
from firebase_admin import credentials, firestore, storage
import json
import os

# --- CONFIGURACIÓN ---
# Ruta a tu clave de cuenta de servicio de Firebase.
SERVICE_ACCOUNT_KEY_PATH = 'serviceAccountKey.json'

# Nombre de tu bucket de Firebase Storage (el que termina en .appspot.com).
# Lo puedes encontrar en la consola de Firebase -> Storage.
STORAGE_BUCKET_NAME = 'roomista-d167c.firebasestorage.app'

# Carpeta local donde se guardarán los ficheros exportados.
OUTPUT_FOLDER = 'backup-datos'

# Lista de las colecciones de primer nivel que quieres exportar de Firestore.
COLLECTIONS_TO_EXPORT = ['users', 'listings', 'matches']

# --- INICIO DEL SCRIPT ---

def export_firestore_to_json(db, output_dir):
    """
    Exporta las colecciones especificadas de Firestore a ficheros JSON.
    """
    print("--- Iniciando exportación de Firestore ---")
    
    for collection_name in COLLECTIONS_TO_EXPORT:
        print(f"Exportando colección: '{collection_name}'...")
        
        # Diccionario para almacenar los datos de la colección
        collection_data = {}
        
        # Obtenemos todos los documentos de la colección
        docs = db.collection(collection_name).stream()
        
        # Iteramos sobre cada documento y lo añadimos al diccionario
        for doc in docs:
            collection_data[doc.id] = doc.to_dict()
        
        # Creamos el nombre del fichero de salida
        output_file_path = os.path.join(output_dir, f"{collection_name}.json")
        
        # Escribimos el diccionario a un fichero JSON con formato legible
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(collection_data, f, indent=4, ensure_ascii=False, default=str)
            
        print(f" -> ¡Éxito! Colección '{collection_name}' guardada en '{output_file_path}'")
        
    print("--- Exportación de Firestore completada ---\n")


def list_storage_files_to_json(bucket, output_dir):
    """
    Lista todos los archivos de Firebase Storage y guarda la lista en un fichero JSON.
    """
    print("--- Iniciando listado de Firebase Storage ---")
    
    # Obtenemos un iterador de todos los "blobs" (archivos) en el bucket
    blobs = bucket.list_blobs()
    
    file_list = []
    
    print("Listando archivos...")
    for blob in blobs:
        file_info = {
            'name': blob.name,
            'size_bytes': blob.size,
            'content_type': blob.content_type,
            'created_at': blob.time_created,
            'updated_at': blob.updated
        }
        file_list.append(file_info)
    
    # Creamos el nombre del fichero de salida
    output_file_path = os.path.join(output_dir, "storage_files.json")
    
    # Escribimos la lista a un fichero JSON
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(file_list, f, indent=4, ensure_ascii=False, default=str)
        
    print(f" -> ¡Éxito! Lista de archivos de Storage guardada en '{output_file_path}'")
    print("--- Listado de Firebase Storage completado ---")


def main():
    """
    Función principal que orquesta la conexión y la exportación.
    """
    # Verificamos si la clave de servicio existe
    if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
        print(f"Error: No se encuentra el fichero de clave de servicio '{SERVICE_ACCOUNT_KEY_PATH}'.")
        print("Por favor, descárgalo desde la consola de Firebase y colócalo en esta carpeta.")
        return

    # Creamos la carpeta de salida si no existe
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Carpeta de salida '{OUTPUT_FOLDER}' creada.")

    try:
        # Inicializamos la app de Firebase con las credenciales y el bucket
        cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
        firebase_admin.initialize_app(cred, {
            'storageBucket': STORAGE_BUCKET_NAME
        })
        print("Conexión con Firebase establecida correctamente.")

        # Obtenemos las instancias de los servicios
        db = firestore.client()
        bucket = storage.bucket()

        # Ejecutamos las exportaciones
        export_firestore_to_json(db, OUTPUT_FOLDER)
        list_storage_files_to_json(bucket, OUTPUT_FOLDER)

    except Exception as e:
        print(f"\nHa ocurrido un error durante la ejecución: {e}")

# Punto de entrada del script
if __name__ == '__main__':
    main()