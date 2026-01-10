import os
import json
import re
import ollama
from tqdm import tqdm

# --- CONFIGURACIÓN ---
DATASET_DIR = "dataset_ground_truth"
OUTPUT_FILE = "embeddings_dataset.json"

# Nombres exactos (Asegúrate que coincidan con 'ollama list')
MODELS = [
    "nomic-embed-text:latest",  # Agregamos :latest por seguridad
    "qwen2.5-coder:7b",         # Agregamos :7b porque así lo tienes instalado
    "llama3.2:latest"           # Agregamos :latest
]

# Límite de caracteres seguro para evitar error 500 (aprox 2000-3000 tokens)
MAX_CHARS = 12000 

def clean_typescript_code(code):
    """
    Limpieza y Truncado para evitar errores de contexto.
    """
    # 1. Eliminar comentarios de bloque
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # 2. Eliminar comentarios de línea
    code = re.sub(r'//.*', '', code)
    # 3. Eliminar imports (a veces meten ruido, opcional, aquí los dejamos por ahora)
    
    # 4. Colapsar espacios
    lines = [line.strip() for line in code.split('\n') if line.strip()]
    cleaned = ' '.join(lines)
    
    # 5. TRUNCADO DE SEGURIDAD (La solución al error 500)
    if len(cleaned) > MAX_CHARS:
        return cleaned[:MAX_CHARS]
    
    return cleaned

def check_models_availability():
    """Verifica qué modelos tienes instalados en Ollama"""
    try:
        models_info = ollama.list()
        # ollama.list() devuelve objetos, extraemos los nombres
        available_names = [m['name'] for m in models_info['models']]
        print(f"🤖 Modelos disponibles en tu Ollama: {available_names}")
        
        missing = []
        for m in MODELS:
            # Buscamos coincidencia parcial (ej: qwen2.5-coder:latest coincide con qwen2.5-coder)
            if not any(m in avail for avail in available_names):
                missing.append(m)
        
        if missing:
            print(f"❌ ALERTA: Parece que te faltan estos modelos o tienen otro tag: {missing}")
            print("   Por favor ejecuta 'ollama list' y actualiza la lista MODELS en el script.")
            return False
        return True
    except Exception as e:
        print(f"⚠️ No pude verificar los modelos automáticamente: {e}")
        return True # Intentamos continuar de todas formas

def get_files_from_dataset(base_dir):
    file_list = []
    if not os.path.exists(base_dir):
        print(f"❌ Error: No encuentro la carpeta '{base_dir}'")
        return []

    for pattern_name in os.listdir(base_dir):
        pattern_path = os.path.join(base_dir, pattern_name)
        if os.path.isdir(pattern_path):
            for filename in os.listdir(pattern_path):
                if filename.endswith(".ts"):
                    file_list.append({
                        "path": os.path.join(pattern_path, filename),
                        "pattern": pattern_name,
                        "filename": filename
                    })
    return file_list

def main():
    # 1. Verificación previa
    if not check_models_availability():
        input("Presiona ENTER para intentar continuar de todas formas o Ctrl+C para cancelar...")

    files = get_files_from_dataset(DATASET_DIR)
    print(f"📂 Archivos encontrados: {len(files)}")
    
    results = {}
    
    # Variable para mostrar un ejemplo al usuario
    example_shown = False

    # 2. Cargar y Limpiar
    print("🧹 Limpiando código fuente...")
    for f in files:
        try:
            with open(f["path"], "r", encoding="utf-8", errors="ignore") as file_read:
                content = file_read.read()
                cleaned_content = clean_typescript_code(content)
                
                # --- DEMOSTRACIÓN PARA EL USUARIO ---
                if not example_shown:
                    print("\n--- [VISTA PREVIA DE LIMPIEZA] ---")
                    print(f"Archivo: {f['filename']}")
                    print(f"Original: {len(content)} chars -> Limpio: {len(cleaned_content)} chars")
                    print(f"Fragmento: {cleaned_content[:200]}...")
                    print("----------------------------------\n")
                    example_shown = True
                # ------------------------------------

                results[f["path"]] = {
                    "filename": f["filename"],
                    "label": f["pattern"],
                    "embeddings": {} 
                }
                f["cleaned_content"] = cleaned_content
        except Exception as e:
            print(f"⚠️ Error leyendo {f['path']}: {e}")

    # 3. Generar Embeddings
    for model_name in MODELS:
        print(f"\n🧠 Procesando con modelo: {model_name}")
        
        # Usamos try/except dentro del loop para que un archivo malo no mate todo el proceso
        for f in tqdm(files, desc=f"Vectores ({model_name})"):
            if "cleaned_content" not in f or not f["cleaned_content"]:
                continue
                
            try:
                # Intentamos generar el embedding
                response = ollama.embeddings(
                    model=model_name,
                    prompt=f["cleaned_content"]
                )
                results[f["path"]]["embeddings"][model_name] = response["embedding"]
                
            except ollama.ResponseError as e:
                if e.status_code == 404:
                    print(f"\n❌ ERROR CRÍTICO: El modelo '{model_name}' no existe en Ollama.")
                    print("   Deteniendo este modelo. Instálalo con 'ollama pull'.")
                    break # Saltamos al siguiente modelo
                else:
                    print(f"\n⚠️ Error Ollama en {f['filename']}: {e}")
            except Exception as e:
                 print(f"\n⚠️ Error desconocido en {f['filename']}: {e}")

    # 4. Guardar
    print(f"\n💾 Guardando resultados en {OUTPUT_FILE}...")
    final_output = []
    for path, data in results.items():
        # Solo guardamos si tiene al menos un vector
        if data["embeddings"]:
            final_output.append({
                "filename": data["filename"],
                "label": data["label"],
                "embeddings": data["embeddings"]
            })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        json.dump(final_output, out)

    print(f"✅ ¡Proceso terminado! Se guardaron {len(final_output)} archivos procesados.")

if __name__ == "__main__":
    main()