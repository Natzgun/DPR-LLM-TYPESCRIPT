"""
Dataset Quality Validator & Enhancer
====================================

Este script analiza el dataset existente y:
1. Detecta y elimina duplicados
2. Valida que cada archivo realmente contenga el patrón asignado
3. Calcula métricas de calidad del dataset
4. Genera un reporte detallado
5. Sugiere mejoras

Usar después de la minería para asegurar calidad del Ground Truth.
"""

import os
import re
import json
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set
from pathlib import Path

# Importar detectores del minero v2
try:
    from mining_repo_v2 import (
        SPECIALIZED_DETECTORS, 
        GenericPatternDetector,
        TypeScriptAnalyzer,
        PATTERNS_CONFIG
    )
except ImportError:
    print("⚠️ No se pudo importar mining_repo_v2. Usando detectores básicos.")
    SPECIALIZED_DETECTORS = {}


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

DATASET_DIR = "dataset_ground_truth_v2"
REPORT_FILE = "dataset_quality_report.json"

PATTERNS = [
    "Singleton", "Factory", "AbstractFactory", "Builder", "Prototype",
    "Adapter", "Bridge", "Composite", "Decorator", "Facade", "Flyweight", "Proxy",
    "ChainOfResponsibility", "Command", "Interpreter", "Iterator", "Mediator",
    "Memento", "Observer", "State", "Strategy", "TemplateMethod", "Visitor"
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class FileAnalysis:
    """Análisis de un archivo del dataset"""
    file_path: str
    assigned_pattern: str
    detected_patterns: List[Tuple[str, float]]  # (pattern, confidence)
    is_valid: bool
    validation_reason: str
    code_metrics: Dict
    content_hash: str


@dataclass
class DatasetReport:
    """Reporte completo del dataset"""
    total_files: int
    valid_files: int
    invalid_files: int
    duplicates: int
    pattern_distribution: Dict[str, int]
    misclassified: List[Dict]
    quality_score: float
    recommendations: List[str]


# ============================================================================
# ANALIZADOR DE CALIDAD
# ============================================================================

class DatasetQualityValidator:
    """Valida y analiza la calidad del dataset"""
    
    def __init__(self, dataset_dir: str):
        self.dataset_dir = dataset_dir
        self.analyses: List[FileAnalysis] = []
        self.hashes: Dict[str, List[str]] = defaultdict(list)  # hash -> files
        self.pattern_counts: Dict[str, int] = defaultdict(int)
        
    def compute_hash(self, content: str) -> str:
        """Computa hash normalizado del contenido"""
        # Normalizar: eliminar comentarios, espacios, etc.
        normalized = re.sub(r'//.*|/\*.*?\*/', '', content, flags=re.DOTALL)
        normalized = re.sub(r'\s+', '', normalized)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def analyze_code_metrics(self, content: str) -> Dict:
        """Calcula métricas de código"""
        lines = content.split('\n')
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('//')]
        
        return {
            "total_lines": len(lines),
            "code_lines": len(code_lines),
            "classes": len(TypeScriptAnalyzer.extract_classes(content)),
            "interfaces": len(TypeScriptAnalyzer.extract_interfaces(content)),
            "methods": len(TypeScriptAnalyzer.extract_methods(content)),
            "imports": len(TypeScriptAnalyzer.extract_imports(content)),
            "has_abstract": bool(re.search(r'abstract\s+class', content)),
            "has_implements": bool(re.search(r'implements\s+\w+', content)),
            "has_extends": bool(re.search(r'extends\s+\w+', content)),
        }
    
    def detect_patterns(self, content: str, file_path: str) -> List[Tuple[str, float]]:
        """Detecta patrones en el archivo usando los detectores avanzados"""
        detections = []
        
        for pattern_name in PATTERNS:
            if pattern_name in SPECIALIZED_DETECTORS:
                detector = SPECIALIZED_DETECTORS[pattern_name]
                detected, confidence, _ = detector.detect(content, file_path)
                if detected:
                    detections.append((pattern_name, confidence))
            elif PATTERNS_CONFIG:
                detected, confidence, _ = GenericPatternDetector.detect(
                    content, file_path, pattern_name
                )
                if detected:
                    detections.append((pattern_name, confidence))
        
        # Ordenar por confianza
        detections.sort(key=lambda x: x[1], reverse=True)
        return detections
    
    def analyze_file(self, file_path: str, assigned_pattern: str) -> FileAnalysis:
        """Analiza un archivo individual"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            content_hash = self.compute_hash(content)
            metrics = self.analyze_code_metrics(content)
            detected = self.detect_patterns(content, file_path)
            
            # Validar
            is_valid = True
            reason = "OK"
            
            # Check 1: Archivo muy pequeño
            if metrics["code_lines"] < 5:
                is_valid = False
                reason = "Archivo muy pequeño (< 5 líneas de código)"
            
            # Check 2: No tiene clases ni interfaces
            elif metrics["classes"] == 0 and metrics["interfaces"] == 0:
                is_valid = False
                reason = "No contiene clases ni interfaces"
            
            # Check 3: Patrón detectado no coincide con asignado
            elif detected:
                best_detected = detected[0][0]
                if best_detected != assigned_pattern:
                    # Verificar si el patrón asignado está entre los detectados
                    assigned_confidence = 0
                    for p, c in detected:
                        if p == assigned_pattern:
                            assigned_confidence = c
                            break
                    
                    if assigned_confidence < 0.3:
                        is_valid = False
                        reason = f"Patrón detectado ({best_detected}) difiere del asignado ({assigned_pattern})"
            
            # Check 4: No se detectó ningún patrón
            elif not detected and SPECIALIZED_DETECTORS:
                is_valid = False
                reason = "No se detectó ningún patrón de diseño"
            
            return FileAnalysis(
                file_path=file_path,
                assigned_pattern=assigned_pattern,
                detected_patterns=detected,
                is_valid=is_valid,
                validation_reason=reason,
                code_metrics=metrics,
                content_hash=content_hash
            )
            
        except Exception as e:
            return FileAnalysis(
                file_path=file_path,
                assigned_pattern=assigned_pattern,
                detected_patterns=[],
                is_valid=False,
                validation_reason=f"Error leyendo archivo: {e}",
                code_metrics={},
                content_hash=""
            )
    
    def find_duplicates(self) -> Dict[str, List[str]]:
        """Encuentra archivos duplicados"""
        duplicates = {}
        for hash_val, files in self.hashes.items():
            if len(files) > 1:
                duplicates[hash_val] = files
        return duplicates
    
    def validate_dataset(self) -> DatasetReport:
        """Valida todo el dataset"""
        print("🔍 Analizando dataset...")
        
        total = 0
        valid = 0
        invalid = 0
        misclassified = []
        
        for pattern in PATTERNS:
            pattern_dir = os.path.join(self.dataset_dir, pattern)
            if not os.path.exists(pattern_dir):
                continue
            
            for filename in os.listdir(pattern_dir):
                if not filename.endswith('.ts'):
                    continue
                
                file_path = os.path.join(pattern_dir, filename)
                analysis = self.analyze_file(file_path, pattern)
                self.analyses.append(analysis)
                
                # Track hash para duplicados
                if analysis.content_hash:
                    self.hashes[analysis.content_hash].append(file_path)
                
                total += 1
                self.pattern_counts[pattern] += 1
                
                if analysis.is_valid:
                    valid += 1
                else:
                    invalid += 1
                    misclassified.append({
                        "file": file_path,
                        "assigned": pattern,
                        "detected": analysis.detected_patterns[:3],
                        "reason": analysis.validation_reason
                    })
        
        # Encontrar duplicados
        duplicates = self.find_duplicates()
        dup_count = sum(len(files) - 1 for files in duplicates.values())
        
        # Calcular quality score
        if total > 0:
            quality_score = (valid - dup_count) / total
        else:
            quality_score = 0.0
        
        # Generar recomendaciones
        recommendations = self.generate_recommendations(
            dict(self.pattern_counts), misclassified, duplicates, quality_score
        )
        
        return DatasetReport(
            total_files=total,
            valid_files=valid,
            invalid_files=invalid,
            duplicates=dup_count,
            pattern_distribution=dict(self.pattern_counts),
            misclassified=misclassified[:50],  # Limitar a 50
            quality_score=quality_score,
            recommendations=recommendations
        )
    
    def generate_recommendations(
        self, 
        distribution: Dict[str, int],
        misclassified: List,
        duplicates: Dict,
        quality_score: float
    ) -> List[str]:
        """Genera recomendaciones de mejora"""
        recommendations = []
        
        # 1. Calidad general
        if quality_score < 0.7:
            recommendations.append(
                "⚠️ Quality score bajo ({:.1%}). Revisar manualmente archivos inválidos.".format(quality_score)
            )
        
        # 2. Desbalance
        if distribution:
            avg = sum(distribution.values()) / len(distribution)
            underrepresented = [p for p, c in distribution.items() if c < avg * 0.3]
            overrepresented = [p for p, c in distribution.items() if c > avg * 2]
            
            if underrepresented:
                recommendations.append(
                    f"📉 Patrones sub-representados: {', '.join(underrepresented)}. "
                    "Buscar más ejemplos de estos patrones."
                )
            
            if overrepresented:
                recommendations.append(
                    f"📈 Patrones sobre-representados: {', '.join(overrepresented)}. "
                    "Considerar balancear con undersampling."
                )
        
        # 3. Duplicados
        if duplicates:
            recommendations.append(
                f"🔄 Encontrados {sum(len(f)-1 for f in duplicates.values())} duplicados. "
                "Ejecutar limpieza con --remove-duplicates."
            )
        
        # 4. Misclassificados
        if len(misclassified) > 10:
            recommendations.append(
                f"❌ {len(misclassified)} archivos posiblemente mal clasificados. "
                "Revisar manualmente o re-ejecutar minería con detectores mejorados."
            )
        
        # 5. Patrones faltantes
        missing = [p for p in PATTERNS if distribution.get(p, 0) == 0]
        if missing:
            recommendations.append(
                f"🚫 Patrones sin ejemplos: {', '.join(missing)}. "
                "Agregar repositorios educativos específicos."
            )
        
        return recommendations
    
    def clean_duplicates(self, dry_run: bool = True) -> int:
        """Elimina archivos duplicados (mantiene el primero)"""
        duplicates = self.find_duplicates()
        removed = 0
        
        for hash_val, files in duplicates.items():
            # Mantener el primer archivo, eliminar el resto
            for file_to_remove in files[1:]:
                if dry_run:
                    print(f"   [DRY-RUN] Eliminaría: {file_to_remove}")
                else:
                    os.remove(file_to_remove)
                    print(f"   ❌ Eliminado: {file_to_remove}")
                removed += 1
        
        return removed
    
    def export_report(self, report: DatasetReport, output_file: str):
        """Exporta el reporte a JSON"""
        report_dict = {
            "summary": {
                "total_files": report.total_files,
                "valid_files": report.valid_files,
                "invalid_files": report.invalid_files,
                "duplicates": report.duplicates,
                "quality_score": report.quality_score
            },
            "pattern_distribution": report.pattern_distribution,
            "misclassified_samples": report.misclassified,
            "recommendations": report.recommendations
        }
        
        with open(output_file, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        print(f"📄 Reporte guardado en: {output_file}")
    
    def print_report(self, report: DatasetReport):
        """Imprime reporte en consola"""
        print("\n" + "=" * 70)
        print("📊 REPORTE DE CALIDAD DEL DATASET")
        print("=" * 70)
        
        print(f"\n📁 Directorio: {self.dataset_dir}")
        print(f"📄 Total archivos: {report.total_files}")
        print(f"✅ Válidos: {report.valid_files}")
        print(f"❌ Inválidos: {report.invalid_files}")
        print(f"🔄 Duplicados: {report.duplicates}")
        print(f"🎯 Quality Score: {report.quality_score:.1%}")
        
        print("\n📈 DISTRIBUCIÓN POR PATRÓN:")
        print("-" * 40)
        for pattern in sorted(report.pattern_distribution.keys()):
            count = report.pattern_distribution[pattern]
            bar = "█" * min(count, 30)
            print(f"   {pattern:25} {count:4} {bar}")
        
        if report.misclassified:
            print(f"\n⚠️ ARCHIVOS POSIBLEMENTE MAL CLASIFICADOS ({len(report.misclassified)}):")
            print("-" * 40)
            for item in report.misclassified[:10]:
                print(f"   📄 {os.path.basename(item['file'])}")
                print(f"      Asignado: {item['assigned']}")
                print(f"      Razón: {item['reason']}")
        
        if report.recommendations:
            print("\n💡 RECOMENDACIONES:")
            print("-" * 40)
            for rec in report.recommendations:
                print(f"   {rec}")
        
        print("\n" + "=" * 70)


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Validador de calidad del dataset")
    parser.add_argument("--dataset", default=DATASET_DIR, help="Directorio del dataset")
    parser.add_argument("--remove-duplicates", action="store_true", help="Eliminar duplicados")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar qué se eliminaría")
    parser.add_argument("--export", default=REPORT_FILE, help="Archivo de reporte JSON")
    
    args = parser.parse_args()
    
    validator = DatasetQualityValidator(args.dataset)
    
    # Validar
    report = validator.validate_dataset()
    
    # Mostrar reporte
    validator.print_report(report)
    
    # Exportar
    validator.export_report(report, args.export)
    
    # Limpiar duplicados si se solicita
    if args.remove_duplicates:
        print("\n🧹 LIMPIEZA DE DUPLICADOS:")
        removed = validator.clean_duplicates(dry_run=args.dry_run)
        print(f"   Total eliminados: {removed}")


if __name__ == "__main__":
    main()
