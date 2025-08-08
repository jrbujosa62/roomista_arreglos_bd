# Elimina los usuario caseros de  Algolia
# Este script elimina todos los usuarios con el rol 'casero' del índice de Algolia  "users".    
# Requiere las credenciales de Algolia en el archivo config.py
# Uso:
# python cleanup_algolia_caseros.py           
import asyncio
import sys
from algoliasearch.search.client import SearchClient
from config import config

INDEX_NAME = "users"

async def cleanup_caseros():
    async with SearchClient(config.ALGOLIA_APP_ID, config.ALGOLIA_ADMIN_KEY) as client:
        try:
            print(f"Conectado a Algolia APP_ID={config.ALGOLIA_APP_ID}")
            resp = await client.delete_by(
                index_name=INDEX_NAME,
                delete_by_params={"filters": "role:casero"},
            )
            await client.wait_for_task(index_name=INDEX_NAME, task_id=resp.task_id)
            print("✅ Usuarios con rol 'casero' eliminados correctamente.")
        except Exception as e:
            print(f"❌ Error en Algolia: {e}")

async def main():
    if not hasattr(config, "ALGOLIA_APP_ID") or not hasattr(config, "ALGOLIA_ADMIN_KEY"):
        print("❌ Variables faltantes en config.py")
        sys.exit(1)
    confirm = input(f"Confirmar eliminación de todos los usuarios 'casero' del índice '{INDEX_NAME}'? (si): ")
    if confirm.lower() == "si":
        await cleanup_caseros()
    else:
        print("Operación cancelada.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nUsuario interrumpió el proceso.")
    except Exception as e:
        print(f"Error al ejecutar script: {e}")