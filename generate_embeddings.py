import os
import json
import re
import ollama
import numpy as np
from tqdm import tqdm

# --- CONFIGURACIÓN PARA RÉPLICA CIENTÍFICA ---
DATASET_DIR = "dataset_ground_truth_v2"
OUTPUT_FILE = "embeddings_typescript_replica.json"

# LISTA DE MODELOS PARA COMPARAR ARQUITECTURAS
# Incluimos Encoders (tipo RoBERTa) y Decoders (tipo CodeGPT) para imitar el paper.
MODELS = [
    # 1. El equivalente a RoBERTa (Ganador del Paper)
    "nomic-embed-text:latest", 
    
    # 2. El equivalente a CodeBERT (Encoder específico de código)
    # Si no tienes bge-m3, usa "all-minilm" o similar.
    "bge-m3:latest", 

    # 3. El equivalente a CodeGPT (Decoder / Generativo)
    # Estos son los que te dije que quitaras, pero DEBES usarlos para la réplica.
    "qwen2.5-coder:7b",       
    "deepseek-coder:6.7b"
]

# Configuración de Ventana Deslizante (Vital para archivos grandes como menciona el paper)
CHUNK_SIZE_CHARS = 4000  # Reducido un poco para asegurar que Qwen/Deepseek no exploten
OVERLAP_CHARS = 200      

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
    # Limpieza estándar (sin ser destructiva)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL) # Quitar bloques
    code = re.sub(r'//.*', '', code) # Quitar lineas
    lines = [line.strip() for line in code.split('\n') if line.strip()]
    return '\n'.join(lines)

def main():
    print("--- REPLICACIÓN PANDEY ET AL. (2025) - STEP 1: EMBEDDINGS ---")
    
    # Verificar modelos antes de empezar
    try:
        installed = [m['name'] for m in ollama.list()['models']]
        print(f"Modelos instalados: {installed}")
        for m in MODELS:
            # Verificación laxa (ignora tags version)
            base_name = m.split(':')[0]
            if not any(base_name in ins for ins in installed):
                print(f"❌ ADVERTENCIA: No veo '{m}' instalado. Ejecuta: ollama pull {m}")
    except:
        pass

    files = []
    # (Aquí iría tu función get_files_from_dataset que ya tienes)
    # Simulación rápida para que el script funcione si copias y pegas:
    if os.path.exists(DATASET_DIR):
        for root, dirs, filenames in os.walk(DATASET_DIR):
            for filename in filenames:
                if filename.endswith(".ts") or filename.endswith(".tsx"):
                    files.append({
                        "path": os.path.join(root, filename),
                        "filename": filename,
                        # Asumiendo estructura carpeta/Label/archivo.ts
                        "label": os.path.basename(root) 
                    })
    
    print(f"📂 Archivos a procesar: {len(files)}")
    
    final_data = []

    # Iterar por archivo (mejor que por modelo, para no leer el disco mil veces)
    for f in tqdm(files, desc="Procesando Archivos"):
        try:
            with open(f["path"], "r", encoding="utf-8", errors="ignore") as fr:
                content = fr.read()
            
            cleaned = clean_typescript_code(content)
            if not cleaned: continue

            file_entry = {
                "filename": f["filename"],
                "label": f["label"],
                "vectors": {}
            }

            # Generar vector con CADA modelo para este archivo
            for model_name in MODELS:
                vec = get_sliding_window_embedding(model_name, cleaned)
                if vec:
                    # Guardamos el vector bajo el nombre del modelo
                    file_entry["vectors"][model_name] = vec
            
            # Solo guardamos si se generó al menos un vector
            if file_entry["vectors"]:
                final_data.append(file_entry)

        except Exception as e:
            print(f"Error archivo {f['filename']}: {e}")

    # Guardar
    print(f"\n💾 Guardando {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        json.dump(final_data, out)
    
    print("✅ Proceso terminado. Listo para fase de Clasificación (k-NN).")

if __name__ == "__main__":
    main()