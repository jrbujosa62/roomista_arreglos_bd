# resync_tenants_to_algolia.py
#
################################################################################
#                                                                              #
#    SCRIPT PARA FORZAR LA RESINCRONIZACIÓN DE USUARIOS CON ALGOLIA            #
#                                                                              #
################################################################################
#
# DESCRIPCIÓN FUNCIONAL:
#
# Este script está diseñado para forzar la reactivación de la Cloud Function
# 'on_user_written' para todos los documentos de la colección 'users'.
#
# Lo hace realizando una pequeña actualización en cada documento: modifica el
# campo 'updated_at' a la fecha y hora actuales. Esta operación de escritura
# es detectada por Firestore, que a su vez invoca la Cloud Function
# correspondiente.
#
# El objetivo es repoblar el índice 'users' en Algolia con todos los usuarios
# que tengan el 'role' correcto ("tenant"), después de que la lógica de la
# Cloud Function haya sido corregida.
#
# CÓMO EJECUTAR:
# - Asegúrate de que el archivo `config.py` con las credenciales de Firebase
#   esté en el directorio correcto.
# - Asegúrate de haber corregido y desplegado la Cloud Function 'on_user_written'
#   para que busque 'role: "tenant"'.
# - Ejecuta el script desde la terminal: `python resync_tenants_to_algolia.py`
#


import sys
import os
import firebase_admin
import datetime
from firebase_admin import credentials, firestore

# --- Configuración de la Ruta del Proyecto (igual que en tu script anterior) ---
try:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    from config import config
except ImportError:
    print("Error: El archivo de configuración 'config/config.py' no fue encontrado.")
    sys.exit(1)


def resync_users(db: firestore.client):
    """
    Actualiza el campo 'updated_at' en todos los documentos de la colección 'users'
    para forzar una resincronización con Algolia.
    """
    print("\n--- Iniciando resincronización de la colección 'users' ---")
    users_ref = db.collection('users')
    docs = users_ref.stream()
    batch = db.batch()
    docs_processed = 0

    # Obtenemos la fecha y hora actual en UTC
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # Creamos el payload de actualización que se aplicará a cada documento
    update_payload = {'updated_at': now_utc}
    
    print(f"Se actualizará 'updated_at' a: {now_utc.isoformat()}")

    for doc in docs:
        batch.update(doc.reference, update_payload)
        docs_processed += 1
        
        # Ejecuta el lote cada 499 documentos para no exceder los límites de Firestore
        if docs_processed % 499 == 0:
            print(f"--- Lote de {docs_processed} documentos lleno, ejecutando escrituras... ---")
            batch.commit()
            # Inicia un nuevo lote
            batch = db.batch()
    
    # Asegúrate de ejecutar el último lote si no era un múltiplo de 499
    if docs_processed > 0:
        print("--- Ejecutando escrituras finales del lote... ---")
        batch.commit()
        print(f"✅ Se ha solicitado la actualización para {docs_processed} documentos en 'users'.")
        print("--- Las Cloud Functions ahora deberían estar procesando la sincronización con Algolia. ---")
    else:
        print("✅ No se encontraron documentos en 'users' para actualizar.")


def main():
    """
    Función principal que inicializa Firebase y ejecuta la resincronización.
    """
    try:
        if not os.path.exists(config.FIREBASE_SERVICE_ACCOUNT_KEY):
            print(f"Error: No se encuentra el archivo de credenciales: {config.FIREBASE_SERVICE_ACCOUNT_KEY}")
            sys.exit(1)
        
        if not firebase_admin._apps:
            cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT_KEY)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
    except Exception as e:
        print(f"Error crítico al inicializar Firebase: {e}")
        sys.exit(1)

    resync_users(db)
    print("\n--- Proceso de resincronización completado. ---")


if __name__ == "__main__":
    main()