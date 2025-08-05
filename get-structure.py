# Fichero: get-structure.py
#
# Descripción:
# Lee los ficheros JSON exportados de Firebase y genera automáticamente un
# documento Markdown (`roomista-structure.md`) que describe el esquema de datos
# de Firestore y la estructura de directorios de Storage.
#
# Uso:
# 1. Coloca este script en la misma carpeta que tus ficheros JSON exportados
#    (listings.json, users.json, etc.).
# 2. Ejecuta desde la terminal: python get-structure.py

import json
import os
from datetime import datetime
from collections import defaultdict

# --- CONFIGURACIÓN ---
INPUT_FILES = {
    'users': 'users.json',
    'listings': 'listings.json',
    'matches': 'matches.json',
    'storage': 'storage_files.json'
}
OUTPUT_FILE = './roomista/roomista-structure.md'
INPUT_FOLDER = 'backup-datos' # Carpeta donde están los JSON

# --- LÓGICA DE INFERENCIA DE TIPOS ---
def infer_type(value):
    """Infiere el tipo de dato de un valor para la documentación."""
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, int) or isinstance(value, float):
        return 'number'
    if isinstance(value, str):
        # Detección simple de Timestamps y URLs
        if value.endswith('Z') and 'T' in value:
            return 'timestamp'
        if value.startswith('http'):
            return 'string (URL)'
        return 'string'
    if isinstance(value, list):
        if not value:
            return 'array'
        # Infiere el tipo de los elementos del array
        element_type = infer_type(value[0])
        return f'array<{element_type}>'
    if isinstance(value, dict):
        # Detección de Geopoints
        if 'latitude' in value and 'longitude' in value:
            return 'geopoint'
        return 'map'
    return 'unknown'

def analyze_collection(file_path):
    """Analiza un fichero JSON de una colección y extrae su esquema."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Advertencia: No se encontró el fichero '{file_path}'. Se omitirá.")
        return None, None
    except json.JSONDecodeError:
        print(f"Error: El fichero '{file_path}' no es un JSON válido.")
        return None, None

    if not data:
        return {}, None

    all_fields = defaultdict(set)
    # Tomamos el primer documento como ejemplo, asumiendo que es representativo
    example_doc_id = next(iter(data))
    example_doc = data[example_doc_id]

    for doc_id, doc_data in data.items():
        for field, value in doc_data.items():
            all_fields[field].add(infer_type(value))

    # Consolidamos los tipos de datos (si un campo a veces es string y a veces null, lo dejamos como string)
    field_schema = {field: list(types)[0] for field, types in all_fields.items()}
    
    return field_schema, example_doc

def analyze_storage(file_path):
    """Analiza el JSON de Storage para deducir las estructuras de directorios."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Advertencia: No se encontró el fichero '{file_path}'. Se omitirá.")
        return []
    except json.JSONDecodeError:
        print(f"Error: El fichero '{file_path}' no es un JSON válido.")
        return []

    if not data:
        return []

    path_patterns = set()
    for file_info in data:
        path = file_info.get('name', '')
        parts = path.split('/')
        if len(parts) > 1:
            # Reemplazamos partes dinámicas con placeholders
            # Ejemplo: 'listings/xyz123/foto.jpg' -> 'listings/{listingId}/{fileName}'
            if parts[0] in ['listings', 'user_photos']:
                if len(parts) > 2:
                    placeholder_id = '{listingId}' if parts[0] == 'listings' else '{userId}'
                    pattern = f"/{parts[0]}/{placeholder_id}/{{fileName}}"
                    path_patterns.add(pattern)

    return sorted(list(path_patterns))


# --- GENERACIÓN DE MARKDOWN ---
def generate_markdown(schemas, storage_paths):
    """Genera el contenido del fichero Markdown a partir de los esquemas."""
    
    # Obtenemos la fecha actual para la cabecera
    today = datetime.now().strftime('%Y-%m-%d')
    
    md_content = [
        f"# Roomista - Estructura de Datos (Data Schema)",
        f"*Última actualización: {today}*",
        "",
        "## 1. Cloud Firestore",
        ""
    ]

    for name, (schema, example) in schemas.items():
        if schema is None: continue

        md_content.extend([
            f"### Colección: `{name}`",
            f"*Ruta: `/{name}/{{{name[:-1]}Id}}`*",
            f"*Descripción: (Añadir descripción aquí)*",
            "",
            "| Campo | Tipo de Dato | Ejemplo (de un documento) |",
            "|---|---|---|"
        ])
        
        # Ordenamos los campos para una salida consistente
        sorted_fields = sorted(schema.keys())

        for field in sorted_fields:
            field_type = schema[field]
            example_value = example.get(field)
            
            # Formateamos el ejemplo para que sea legible
            if isinstance(example_value, str):
                example_value_str = f'"{example_value[:30]}..."' if len(example_value) > 30 else f'"{example_value}"'
            elif isinstance(example_value, dict):
                 example_value_str = f'`{json.dumps(example_value)}`'
            else:
                example_value_str = f'`{example_value}`'
            
            md_content.append(f"| `{field}` | `{field_type}` | {example_value_str} |")
        
        md_content.append("\n---\n")

    md_content.extend([
        "## 2. Firebase Storage",
        ""
    ])

    if not storage_paths:
        md_content.append("*No se detectaron patrones de ruta en Storage.*")
    else:
        for path in storage_paths:
            md_content.extend([
                f"### Ruta: `{path}`",
                f"*Descripción: (Añadir descripción aquí)*",
                ""
            ])

    return "\n".join(md_content)


# --- FUNCIÓN PRINCIPAL ---
def main():
    print("Iniciando análisis de la estructura de Firebase...")
    
    # Asegurarse de que la carpeta de entrada existe
    if not os.path.isdir(INPUT_FOLDER):
        print(f"Error: La carpeta de entrada '{INPUT_FOLDER}' no existe.")
        print("Asegúrate de ejecutar primero el script de exportación.")
        return

    firestore_schemas = {}
    for name, filename in INPUT_FILES.items():
        if name != 'storage':
            file_path = os.path.join(INPUT_FOLDER, filename)
            schema, example = analyze_collection(file_path)
            if schema is not None:
                firestore_schemas[name] = (schema, example)

    storage_file_path = os.path.join(INPUT_FOLDER, INPUT_FILES['storage'])
    storage_patterns = analyze_storage(storage_file_path)

    print("Análisis completado. Generando fichero Markdown...")
    markdown_output = generate_markdown(firestore_schemas, storage_patterns)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(markdown_output)

    print(f"¡Éxito! La documentación de la estructura ha sido guardada en '{OUTPUT_FILE}'")

if __name__ == '__main__':
    main()