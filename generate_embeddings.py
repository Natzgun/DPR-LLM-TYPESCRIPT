import os
import json
import re
import ollama
import numpy as np
from tqdm import tqdm

# --- CONFIGURACIÓN PARA RÉPLICA CIENTÍFICA ---
DATASET_DIR = "dataset_ground_truth_v2"
METADATA_FILE = os.path.join(DATASET_DIR, "dataset_metadata_v2.json")
OUTPUT_FILE = "embeddings_typescript_replica.json"

# LISTA DE MODELOS PARA COMPARAR ARQUITECTURAS
# Usamos modelos que SOPORTAN embeddings en Ollama
MODELS = [
    # 1. Modelos de embedding dedicados (RECOMENDADOS)
    "nomic-embed-text:latest",   # ~137M params, bueno para código
    "bge-m3:latest",             # Multilingüe, buena calidad
    # "all-minilm:latest",       # Alternativa ligera
    # "mxbai-embed-large:latest" # Alta calidad
]

# NOTA: deepseek-coder y qwen2.5-coder son modelos GENERATIVOS (LLM)
# NO soportan embeddings nativamente en Ollama. Si necesitas usarlos,
# tendrías que extraer embeddings de la última capa oculta manualmente.

# Configuración de Ventana Deslizante (Vital para archivos grandes)
CHUNK_SIZE_CHARS = 4000  # Tamaño de cada chunk
OVERLAP_CHARS = 200      # Solapamiento entre chunks      

def get_sliding_window_embedding(model_name, text):
    """
    Genera embeddings usando ventana deslizante y promedio.
    Soporta tanto modelos de Embedding puros como modelos de Chat (Qwen/Deepseek).
    """
    # Dividir en chunks
    chunks = []
    start = 0
    
    # Seguridad: Si el texto es vacío
    if not text.strip(): return []

    # Si es pequeño, un solo chunk
    if len(text) <= CHUNK_SIZE_CHARS:
        chunks.append(text)
    else:
        # Loop de ventana deslizante
        while start < len(text):
            end = min(start + CHUNK_SIZE_CHARS, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            if end == len(text):
                break
            start += CHUNK_SIZE_CHARS - OVERLAP_CHARS
    
    vectors = []
    for chunk in chunks:
        try:
            # Ollama permite pedir embeddings a modelos de chat (qwen/deepseek)
            # El endpoint es el mismo.
            resp = ollama.embeddings(model=model_name, prompt=chunk)
            emb = resp.get("embedding")
            
            if emb:
                vectors.append(emb)
            else:
                # A veces los modelos de chat devuelven vacío si el prompt es raro
                print(f"   ⚠️ Vector vacío recibido de {model_name}")
                
        except Exception as e:
            print(f"   ⚠️ Error en chunk con {model_name}: {e}")

    if not vectors:
        return []
    
    # Promedio de los vectores (Mean Pooling) para tener 1 solo vector por archivo
    return np.mean(vectors, axis=0).tolist()

def clean_typescript_code(code):
    """Limpieza estándar (sin ser destructiva)"""
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)  # Quitar bloques /* */
    code = re.sub(r'//.*', '', code)  # Quitar comentarios de línea
    lines = [line.strip() for line in code.split('\n') if line.strip()]
    return '\n'.join(lines)


def load_dataset_from_metadata():
    """Carga los archivos desde el metadata JSON del dataset"""
    if not os.path.exists(METADATA_FILE):
        print(f"❌ No se encontró {METADATA_FILE}")
        return []
    
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    files = []
    samples = metadata.get("samples", [])
    
    for sample in samples:
        # Convertir rutas Windows a Linux y hacerlas relativas al repo
        file_path = sample.get("file_path", "")
        # Quitar backslashes de Windows y el primer separador
        file_path = file_path.replace("\\", "/").lstrip("/")
        
        # La ruta completa es: repos/<file_path> o dataset_ground_truth_v2/<pattern>/<archivo>
        # Verificamos si existe en repos/
        full_path_repos = os.path.join("repos", file_path)
        
        # Buscar también en el directorio del dataset por patrón
        pattern_name = sample.get("pattern_name", "Unknown")
        filename = os.path.basename(file_path)
        full_path_dataset = os.path.join(DATASET_DIR, pattern_name, filename)
        
        # Intentar encontrar el archivo
        if os.path.exists(full_path_repos):
            actual_path = full_path_repos
        elif os.path.exists(full_path_dataset):
            actual_path = full_path_dataset
        else:
            # Búsqueda alternativa en el directorio del patrón
            pattern_dir = os.path.join(DATASET_DIR, pattern_name)
            if os.path.exists(pattern_dir):
                # Buscar archivo que contenga el nombre
                for f_name in os.listdir(pattern_dir):
                    if f_name.endswith(('.ts', '.tsx')):
                        actual_path = os.path.join(pattern_dir, f_name)
                        break
                else:
                    continue
            else:
                continue
        
        files.append({
            "path": actual_path,
            "filename": filename,
            "label": pattern_name,
            "confidence": sample.get("confidence_score", 0),
            "source_repo": sample.get("source_repo", "unknown")
        })
    
    return files


def get_files_from_directory():
    """Alternativa: buscar archivos directamente en el directorio"""
    files = []
    if os.path.exists(DATASET_DIR):
        for root, dirs, filenames in os.walk(DATASET_DIR):
            for filename in filenames:
                if filename.endswith(".ts") or filename.endswith(".tsx"):
                    files.append({
                        "path": os.path.join(root, filename),
                        "filename": filename,
                        "label": os.path.basename(root),
                        "confidence": 1.0,
                        "source_repo": "local"
                    })
    return files


def main():
    print("--- REPLICACIÓN PANDEY ET AL. (2025) - STEP 1: EMBEDDINGS ---")
    
    # Verificar modelos antes de empezar
    try:
        installed = [m['name'] for m in ollama.list()['models']]
        print(f"Modelos instalados: {installed}")
        missing_models = []
        for m in MODELS:
            base_name = m.split(':')[0]
            if not any(base_name in ins for ins in installed):
                missing_models.append(m)
                print(f"❌ ADVERTENCIA: No veo '{m}' instalado. Ejecuta: ollama pull {m}")
        
        if missing_models:
            print(f"\n⚠️  Faltan {len(missing_models)} modelos. ¿Continuar con los disponibles? (s/n)")
            # Comentar esto si quieres que continúe automáticamente
            # resp = input()
            # if resp.lower() != 's':
            #     return
    except Exception as e:
        print(f"⚠️ No se pudo verificar modelos de Ollama: {e}")

    # Cargar archivos - intentar primero desde metadata, si falla usar directorio
    files = get_files_from_directory()  # Más simple y directo
    
    if not files:
        print("❌ No se encontraron archivos TypeScript en el dataset")
        return
    
    print(f"📂 Archivos a procesar: {len(files)}")
    
    # Mostrar distribución de patrones
    pattern_counts = {}
    for f in files:
        pattern_counts[f["label"]] = pattern_counts.get(f["label"], 0) + 1
    print(f"📊 Distribución de patrones: {pattern_counts}")
    
    final_data = []

    # Iterar por archivo
    for f in tqdm(files, desc="Procesando Archivos"):
        try:
            with open(f["path"], "r", encoding="utf-8", errors="ignore") as fr:
                content = fr.read()
            
            cleaned = clean_typescript_code(content)
            if not cleaned:
                continue

            file_entry = {
                "filename": f["filename"],
                "label": f["label"],
                "source_repo": f.get("source_repo", "unknown"),
                "confidence": f.get("confidence", 1.0),
                "code_length": len(cleaned),
                "vectors": {}
            }

            # Generar vector con CADA modelo para este archivo
            for model_name in MODELS:
                vec = get_sliding_window_embedding(model_name, cleaned)
                if vec:
                    file_entry["vectors"][model_name] = {
                        "embedding": vec,
                        "dimension": len(vec)
                    }
            
            # Solo guardamos si se generó al menos un vector
            if file_entry["vectors"]:
                final_data.append(file_entry)

        except Exception as e:
            print(f"Error archivo {f['filename']}: {e}")

    # Guardar resultado
    print(f"\n💾 Guardando {OUTPUT_FILE}...")
    
    output_data = {
        "metadata": {
            "total_files": len(final_data),
            "models_used": MODELS,
            "chunk_size": CHUNK_SIZE_CHARS,
            "overlap": OVERLAP_CHARS,
            "pattern_distribution": pattern_counts
        },
        "embeddings": final_data
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        json.dump(output_data, out, indent=2)
    
    print(f"✅ Proceso terminado. {len(final_data)} archivos procesados.")
    print("   Listo para fase de Clasificación (k-NN).")

if __name__ == "__main__":
    main()