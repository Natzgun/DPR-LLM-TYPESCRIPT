"""
Test de conexión y funcionalidad de Ollama
Ejecuta esto ANTES del embedding_extractor.py
"""

import ollama
import numpy as np


def test_ollama_connection():
    """Verifica que Ollama esté corriendo"""
    print("=" * 60)
    print("TEST 1: Conexión a Ollama")
    print("=" * 60)
    
    try:
        models = ollama.list()
        print("✅ Ollama está corriendo")
        print(f"\nModelos instalados:")
        for model in models['models']:
            # model es un objeto, acceder a .model en lugar de ['name']
            print(f"  • {model.model}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Solución:")
        print("   1. Abre otra terminal")
        print("   2. Ejecuta: ollama serve")
        print("   3. Vuelve a ejecutar este script")
        return False


def test_embedding_extraction():
    """Prueba extracción de embeddings con código TypeScript de ejemplo"""
    print("\n" + "=" * 60)
    print("TEST 2: Extracción de Embeddings")
    print("=" * 60)
    
    # Código TypeScript de ejemplo (Singleton)
    sample_code = """
export class Singleton {
    private static instance: Singleton;
    
    private constructor() {
        console.log("Singleton created");
    }
    
    public static getInstance(): Singleton {
        if (!Singleton.instance) {
            Singleton.instance = new Singleton();
        }
        return Singleton.instance;
    }
}
"""
    
    models_to_test = [
        'nomic-embed-text:latest',
        'qwen2.5-coder:7b',
        'llama3.2:latest'
    ]
    
    results = {}
    
    for model in models_to_test:
        print(f"\n🧪 Probando: {model}")
        try:
            response = ollama.embeddings(
                model=model,
                prompt=sample_code
            )
            
            embedding = np.array(response['embedding'])
            results[model] = {
                'success': True,
                'dimension': len(embedding),
                'sample_values': embedding[:5].tolist()
            }
            
            print(f"   ✅ Funciona")
            print(f"   📊 Dimensión del vector: {len(embedding)}")
            print(f"   🔢 Primeros 5 valores: {embedding[:5]}")
            
        except Exception as e:
            results[model] = {'success': False, 'error': str(e)}
            print(f"   ❌ Error: {e}")
            if "not found" in str(e).lower():
                print(f"   💡 Solución: ollama pull {model}")
    
    return results


def print_summary(connection_ok: bool, embedding_results: dict):
    """Imprime resumen final"""
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    if not connection_ok:
        print("❌ Ollama no está corriendo")
        print("   Ejecuta 'ollama serve' en otra terminal")
        return
    
    print("✅ Ollama está corriendo")
    
    success_count = sum(1 for r in embedding_results.values() if r.get('success'))
    total_count = len(embedding_results)
    
    print(f"\nModelos funcionando: {success_count}/{total_count}")
    
    for model, result in embedding_results.items():
        status = "✅" if result.get('success') else "❌"
        print(f"  {status} {model}")
        if result.get('success'):
            print(f"      Dimensión: {result['dimension']}")
    
    if success_count == total_count:
        print("\n" + "=" * 60)
        print("✅ ¡TODO LISTO!")
        print("=" * 60)
        print("Puedes ejecutar: python embedding_extractor.py")
    else:
        print("\n" + "=" * 60)
        print("⚠ ACCIÓN REQUERIDA")
        print("=" * 60)
        print("Instala los modelos faltantes con:")
        for model, result in embedding_results.items():
            if not result.get('success'):
                print(f"  ollama pull {model}")


if __name__ == "__main__":
    print("🧪 TEST DE OLLAMA PARA TS-PATTERN-RECOGNITION\n")
    
    # Test 1: Conexión
    connection_ok = test_ollama_connection()
    
    if connection_ok:
        # Test 2: Embeddings
        embedding_results = test_embedding_extraction()
        
        # Resumen
        print_summary(connection_ok, embedding_results)
    else:
        print_summary(connection_ok, {})