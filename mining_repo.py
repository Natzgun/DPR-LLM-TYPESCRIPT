import os
import shutil
import time
import json
from github import Github
from git import Repo
from dotenv import load_dotenv

# --- CONFIGURACIÓN DE INVESTIGACIÓN ---
# Busca repositorios educativos o de referencia, no proyectos aleatorios que "quizás" usen patrones.
SEARCH_QUERIES = [
    "language:TypeScript stars:>1000",       # Proyectos generales muy populares
    "language:TypeScript stars:500..1000",   # Proyectos generales media-alta popularidad
    "topic:clean-architecture language:TypeScript", # Arquitecturas que fuerzan patrones
    "topic:nestjs language:TypeScript",      # Framework que usa patrones intensivamente
    "topic:design-patterns language:TypeScript" # Tu query original (Backup)
]

# Patrones GoF a buscar (Nombres de carpetas esperados)
PATTERNS_TO_MINE = [
    "Singleton", "Factory", "AbstractFactory", "Builder", "Prototype",
    "Adapter", "Bridge", "Composite", "Decorator", "Facade", "Flyweight", "Proxy",
    "ChainOfResponsibility", "Command", "Interpreter", "Iterator", "Mediator",
    "Memento", "Observer", "State", "Strategy", "TemplateMethod", "Visitor"
]

# Filtros de Calidad (Para asegurar un Ground Truth robusto)
MIN_STARS = 10          # Evita repositorios vacíos o tareas escolares sin validar
MAX_REPOS_TO_SCAN = 1000  # Ajusta esto según tu ancho de banda (ej. 100)
OUTPUT_DIR = "dataset_ground_truth"
TEMP_DIR = "temp_clones"

# --- INICIO DEL SCRIPT ---
def setup_environment():
    """Prepara las carpetas y limpia ejecuciones anteriores."""
    if os.path.exists(OUTPUT_DIR):
        print(f"⚠️  La carpeta {OUTPUT_DIR} ya existe. Se agregarán nuevos datos.")
    else:
        os.makedirs(OUTPUT_DIR)
    
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

    # Crear subcarpetas para cada patrón
    for pattern in PATTERNS_TO_MINE:
        os.makedirs(os.path.join(OUTPUT_DIR, pattern), exist_ok=True)

def is_valid_source_code(file_path):
    filename_lower = os.path.basename(file_path).lower()

    if "test" in filename_lower or "spec" in filename_lower:
        return False
    
    # [AGREGADO - ROBUSTEZ]
    # Razón: Al minar repos generales (no educativos), encontraremos bundles o archivos generados.
    # El paper analiza "source code", no código de máquina/minificado.
    try:
        # Filtro de tamaño (>1MB)
        if os.path.getsize(file_path) > 1_000_000: 
            return False

        with open(file_path, 'r', encoding = 'utf-8', errors='ignore') as f:
            # Leemos líneas para detectar minificación
            lines = f.readlines()
            if not lines: return False
            
            # Si una línea es larguísima (>1000 chars), suele ser código generado/minificado
            if max(len(line) for line in lines) > 1000:
                return False
                
            content = "".join(lines)
            
        structural_keywords = ['class ', 'interface ', 'abstract class ', 'implements ', 'extends ']

        if not any(keyword in content for keyword in structural_keywords):
            return False
            
        return True
    except Exception:
        return False

def analyze_and_extract(repo_name, local_path, metadata_list):
    """
    Recorre el repo clonado. Si encuentra una carpeta que coincide con un patrón,
    extrae los archivos .ts contenidos en ella.
    """
    print(f"   🔍 Analizando estructura de: {repo_name}...")
    
    for root, dirs, files in os.walk(local_path):
        # Normalizamos la ruta para buscar coincidencias
        path_parts = os.path.normpath(root).split(os.sep)
        
        # Heurística: ¿Alguna carpeta padre se llama igual que un patrón?
        # Buscamos coincidencias insensibles a mayúsculas/minúsculas (ej: "singleton", "Singleton")
        for pattern in PATTERNS_TO_MINE:
            # Check si el patrón está en la ruta (ej: /src/design-patterns/Singleton/...)
            if any(part.lower() == pattern.lower() for part in path_parts):
                
                for file in files:
                    if file.endswith(".ts") and not file.endswith(".d.ts"):
                        # Construir rutas
                        src_file = os.path.join(root, file)
                        if is_valid_source_code(src_file): 
                            # Renombramos para evitar colisiones: RepoName_OriginalName.ts
                            safe_repo_name = repo_name.replace("/", "_")
                            new_filename = f"{safe_repo_name}__{file}"
                            dest_file = os.path.join(OUTPUT_DIR, pattern, new_filename)
                            
                            # Copiar archivo
                            shutil.copy2(src_file, dest_file)
                            
                            # Guardar metadatos para el Paper (Validación)
                            metadata_list.append({
                                "pattern": pattern,
                                "original_repo": repo_name,
                                "original_path": src_file.replace(TEMP_DIR, ""),
                                "local_filename": new_filename
                            })

def main():
    # 1. Cargar Token (Crear archivo .env o ponerlo directo aquí para pruebas rápidas)
    load_dotenv() 
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
    # GITHUB_TOKEN = "TU_TOKEN_AQUI" # <--- ¡PEGA TU TOKEN AQUÍ SI NO USAS .ENV!

    if not GITHUB_TOKEN or GITHUB_TOKEN == "TU_TOKEN_AQUI":
        print("❌ Error: Necesitas un GitHub Token válido.")
        return

    g = Github(GITHUB_TOKEN)
    setup_environment()
    
    processed_repos = set()
    dataset_metadata = []

    print(f"🚀 Iniciando minería de repositorios para ICSE 2026...")
    print(f"🎯 Objetivo: Construir Dataset TypeScript Ground Truth")
    
    try:
        count = 0
        for query in SEARCH_QUERIES:
            if count >= MAX_REPOS_TO_SCAN: break
            
            print(f"\n🔎 Ejecutando consulta: '{query}'")
            # Buscar repositorios ordenados por estrellas (mejor calidad primero)
            repos = g.search_repositories(query=query, sort="stars", order="desc")
            
            for repo in repos:
                if count >= MAX_REPOS_TO_SCAN: break
                if repo.full_name in processed_repos: continue # Evitar duplicados
                if repo.stargazers_count < MIN_STARS: continue # Filtro de calidad

                print(f"\n[{count+1}/{MAX_REPOS_TO_SCAN}] Clonando: {repo.full_name} (⭐ {repo.stargazers_count})")
                
                repo_dir = os.path.join(TEMP_DIR, repo.name)
                
                try:
                    # 1. Clonar
                    Repo.clone_from(repo.clone_url, repo_dir, depth=1) # depth=1 es más rápido (sin historial)
                    
                    # 2. Analizar y Extraer
                    analyze_and_extract(repo.full_name, repo_dir, dataset_metadata)
                    
                    processed_repos.add(repo.full_name)
                    count += 1
                    
                except Exception as e:
                    print(f"⚠️  Error procesando {repo.full_name}: {e}")
                
                finally:
                    # 3. Limpieza inmediata para ahorrar espacio en disco
                    if os.path.exists(repo_dir):
                        # En Windows a veces git retiene archivos, forzamos espera
                        time.sleep(1)
                        try:
                            shutil.rmtree(repo_dir, ignore_errors=True)
                        except:
                            print("   ⚠️ No se pudo borrar carpeta temporal (Windows lock?), continuando...")

    except Exception as e:
        print(f"\n❌ Error crítico en la API: {e}")

    # Guardar Metadatos finales
    with open(f"{OUTPUT_DIR}/dataset_metadata.json", "w") as f:
        json.dump(dataset_metadata, f, indent=4)

    print("\n" + "="*50)
    print("✅ PROCESO COMPLETADO")
    print(f"📂 Dataset generado en: {os.path.abspath(OUTPUT_DIR)}")
    print(f"📄 Metadatos guardados en: {OUTPUT_DIR}/dataset_metadata.json")
    print("="*50)

if __name__ == "__main__":
    main()