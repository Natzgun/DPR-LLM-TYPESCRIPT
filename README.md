# DPR-LLM-typescript: Design Pattern Retrieval & Embeddings Analysis

Este proyecto tiene como objetivo construir un dataset de "Ground Truth" de implementaciones de patrones de diseño (GoF) en **TypeScript**, extrayéndolos de repositorios reales de GitHub. Posteriormente, utiliza modelos de lenguaje locales (via Ollama) para generar embeddings de estos fragmentos de código, permitiendo tareas de análisis, búsqueda semántica o clasificación.

## 🚀 Flujo de Trabajo

El proyecto consta de tres etapas principales:

### 1. Minería de Datos (`mining_repo.py`)
- **Búsqueda:** Utiliza la API de GitHub para encontrar repositorios de TypeScript etiquetados con temas como `design-patterns`, `software-architecture`, etc.
- **Filtrado:** Descarta repositorios con pocas estrellas (< 15) para asegurar una calidad mínima.
- **Extracción:** Clona temporalmente los repositorios y busca carpetas que coincidan con los nombres de los 23 patrones de diseño GoF (ej. `Singleton`, `Factory`, `Strategy`).
- **Organización:** Copia los archivos `.ts` encontrados a la carpeta `dataset_ground_truth/`, organizados por patrón y renombrados para mantener la trazabilidad del origen (`RepoName__FileName.ts`).

### 2. Generación de Embeddings (`generate_embeddings.py`)
- **Preprocesamiento:** Limpia el código TypeScript extraído (elimina comentarios, reduce espacios, trunca a un límite seguro de tokens).
- **Inferencia Local:** Utiliza **Ollama** para generar embeddings vectoriales del código utilizando múltiples modelos:
  - `nomic-embed-text`
  - `qwen2.5-coder`
  - `llama3.2`
- **Persistencia:** Guarda los embeddings y metadatos resultantes en `embeddings_dataset.json`.

### 3. Análisis (`analysis.ipynb`)
- Cuaderno Jupyter (previsto) para explorar, visualizar (t-SNE/PCA) o evaluar la calidad de los embeddings generados.

## 🛠️ Requisitos Previos

- **Python 3.10+**
- **Ollama**: Debe estar instalado y ejecutándose localmente (`ollama serve`).
- **Modelos Ollama**: Debes tener descargados los modelos utilizados:
  ```bash
  ollama pull nomic-embed-text
  ollama pull qwen2.5-coder:7b
  ollama pull llama3.2
  ```
- **GitHub Token**: Necesario para el script de minería.

## 📦 Instalación

1. Clona este repositorio.
2. Instala las dependencias (usar UV de preferencia):
   ```bash
   pip install -r requirements.txt
   # O si usas poetry/otro gestor, revisa pyproject.toml
   ```
3. Configura tu token de GitHub en un archivo `.env`:
   ```env
   GITHUB_TOKEN=ghp_tu_token_secreto_aqui
   ```

## ▶️ Uso

1. **Generar el Dataset:**
   Ejecuta el minero para buscar y descargar código.
   ```bash
   python mining_repo.py
   ```
   *Esto creará la carpeta `dataset_ground_truth/`.*

2. **Generar Embeddings:**
   Procesa el dataset con Ollama.
   ```bash
   python generate_embeddings.py
   ```
   *Esto generará el archivo `embeddings_dataset.json`.*

## 📂 Estructura de Carpetas

```
.
├── dataset_ground_truth/       # Dataset generado (Código fuente limpio)
│   ├── AbstractFactory/
│   ├── Singleton/
│   │   ├── repo-a__Instance.ts
│   │   └── ...
│   └── ...
├── embeddings_dataset.json     # Resultado final con vectores
├── generate_embeddings.py      # Script de generación de embeddings
├── mining_repo.py              # Script de minería de GitHub
├── analysis.ipynb              # Notebook de análisis
```
