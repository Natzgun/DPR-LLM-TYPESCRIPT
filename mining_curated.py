"""
Mining Repository - Fuentes Curadas de Patrones
================================================

Este módulo contiene repositorios ESPECÍFICOS conocidos por tener implementaciones
excelentes de patrones de diseño. Es un complemento al minero automático.

Estos repos son usados en producción o son referencias educativas de alta calidad.
"""

import os
import shutil
import json
from typing import Dict, List
from dataclasses import dataclass, asdict
from git import Repo

# ============================================================================
# REPOSITORIOS CURADOS CON PATRONES CONOCIDOS
# ============================================================================

# Repositorios con patrones de diseño confirmados y sus ubicaciones
CURATED_REPOS = {
    # --- EDUCATIVOS (Ground Truth de alta confianza) ---
    "RefactoringGuru/design-patterns-typescript": {
        "url": "https://github.com/RefactoringGuru/design-patterns-typescript",
        "description": "Implementaciones oficiales de RefactoringGuru",
        "confidence": 0.95,
        "patterns": {
            "Singleton": ["src/Singleton/**/*.ts"],
            "Factory": ["src/FactoryMethod/**/*.ts"],
            "AbstractFactory": ["src/AbstractFactory/**/*.ts"],
            "Builder": ["src/Builder/**/*.ts"],
            "Prototype": ["src/Prototype/**/*.ts"],
            "Adapter": ["src/Adapter/**/*.ts"],
            "Bridge": ["src/Bridge/**/*.ts"],
            "Composite": ["src/Composite/**/*.ts"],
            "Decorator": ["src/Decorator/**/*.ts"],
            "Facade": ["src/Facade/**/*.ts"],
            "Flyweight": ["src/Flyweight/**/*.ts"],
            "Proxy": ["src/Proxy/**/*.ts"],
            "ChainOfResponsibility": ["src/ChainOfResponsibility/**/*.ts"],
            "Command": ["src/Command/**/*.ts"],
            "Iterator": ["src/Iterator/**/*.ts"],
            "Mediator": ["src/Mediator/**/*.ts"],
            "Memento": ["src/Memento/**/*.ts"],
            "Observer": ["src/Observer/**/*.ts"],
            "State": ["src/State/**/*.ts"],
            "Strategy": ["src/Strategy/**/*.ts"],
            "TemplateMethod": ["src/TemplateMethod/**/*.ts"],
            "Visitor": ["src/Visitor/**/*.ts"],
        }
    },
    
    # --- FRAMEWORKS REALES ---
    "nestjs/nest": {
        "url": "https://github.com/nestjs/nest",
        "description": "Framework NestJS - usa patrones extensivamente",
        "confidence": 0.85,
        "patterns": {
            "Singleton": [
                "packages/core/injector/instance-wrapper.ts",
                "packages/core/injector/container.ts",
            ],
            "Factory": [
                "packages/core/router/route-params-factory.ts",
                "packages/core/injector/module-token-factory.ts",
                "packages/core/exceptions/base-exception-filter-context.ts",
            ],
            "Decorator": [
                "packages/common/decorators/**/*.ts",
                "packages/core/services/reflector.service.ts",
            ],
            "Strategy": [
                "packages/core/guards/*.ts",
                "packages/core/interceptors/*.ts",
            ],
            "Observer": [
                "packages/microservices/client/*.ts",
            ],
            "Facade": [
                "packages/core/nest-application.ts",
                "packages/core/nest-factory.ts",
            ],
            "Proxy": [
                "packages/core/injector/lazy-module-loader/*.ts",
            ],
            "ChainOfResponsibility": [
                "packages/core/middleware/*.ts",
                "packages/core/pipes/pipes-context-creator.ts",
            ],
            "Composite": [
                "packages/core/injector/modules-container.ts",
            ],
        }
    },
    
    "typeorm/typeorm": {
        "url": "https://github.com/typeorm/typeorm",
        "description": "TypeORM - ORM con muchos patrones",
        "confidence": 0.85,
        "patterns": {
            "Builder": [
                "src/query-builder/**/*.ts",
            ],
            "Strategy": [
                "src/driver/**/*Driver.ts",
                "src/naming-strategy/*.ts",
            ],
            "Singleton": [
                "src/connection/ConnectionManager.ts",
            ],
            "Factory": [
                "src/entity-manager/EntityManagerFactory.ts",
                "src/repository/RepositoryFactory.ts",
            ],
            "Decorator": [
                "src/decorator/**/*.ts",
            ],
            "Observer": [
                "src/subscriber/*.ts",
            ],
            "Proxy": [
                "src/lazy-loading/*.ts",
            ],
            "Composite": [
                "src/metadata/EntityMetadata.ts",
            ],
        }
    },
    
    "inversify/InversifyJS": {
        "url": "https://github.com/inversify/InversifyJS",
        "description": "Inversify - IoC Container (patrones creacionales)",
        "confidence": 0.90,
        "patterns": {
            "Singleton": [
                "src/container/container.ts",
            ],
            "Factory": [
                "src/resolution/resolver.ts",
            ],
            "AbstractFactory": [
                "src/planning/planner.ts",
            ],
            "Decorator": [
                "src/annotation/*.ts",
            ],
        }
    },
    
    "ReactiveX/rxjs": {
        "url": "https://github.com/ReactiveX/rxjs",
        "description": "RxJS - Implementación canónica de Observer/Iterator",
        "confidence": 0.95,
        "patterns": {
            "Observer": [
                "src/internal/Observable.ts",
                "src/internal/Subscriber.ts",
                "src/internal/Subject.ts",
                "src/internal/Observer.ts",
            ],
            "Iterator": [
                "src/internal/operators/**/*.ts",
            ],
            "Decorator": [
                "src/internal/operators/tap.ts",
                "src/internal/operators/map.ts",
            ],
            "Factory": [
                "src/internal/observable/*.ts",
            ],
            "Strategy": [
                "src/internal/scheduler/*.ts",
            ],
        }
    },
    
    # --- REPOSITORIOS EDUCATIVOS ADICIONALES ---
    "torokmark/design_patterns_in_typescript": {
        "url": "https://github.com/torokmark/design_patterns_in_typescript",
        "description": "Colección educativa completa",
        "confidence": 0.90,
        "patterns": {
            "Singleton": ["singleton/**/*.ts"],
            "Factory": ["factory_method/**/*.ts"],
            "AbstractFactory": ["abstract_factory/**/*.ts"],
            "Builder": ["builder/**/*.ts"],
            "Prototype": ["prototype/**/*.ts"],
            "Adapter": ["adapter/**/*.ts"],
            "Bridge": ["bridge/**/*.ts"],
            "Composite": ["composite/**/*.ts"],
            "Decorator": ["decorator/**/*.ts"],
            "Facade": ["facade/**/*.ts"],
            "Flyweight": ["flyweight/**/*.ts"],
            "Proxy": ["proxy/**/*.ts"],
            "ChainOfResponsibility": ["chain_of_responsibility/**/*.ts"],
            "Command": ["command/**/*.ts"],
            "Interpreter": ["interpreter/**/*.ts"],
            "Iterator": ["iterator/**/*.ts"],
            "Mediator": ["mediator/**/*.ts"],
            "Memento": ["memento/**/*.ts"],
            "Observer": ["observer/**/*.ts"],
            "State": ["state/**/*.ts"],
            "Strategy": ["strategy/**/*.ts"],
            "TemplateMethod": ["template_method/**/*.ts"],
            "Visitor": ["visitor/**/*.ts"],
        }
    },
    
    "gztchan/design-patterns-in-typescript": {
        "url": "https://github.com/gztchan/design-patterns-in-typescript",
        "description": "Otra colección educativa popular",
        "confidence": 0.85,
        "patterns": {
            "Singleton": ["src/singleton/**/*.ts"],
            "Factory": ["src/factory-method/**/*.ts"],
            "Builder": ["src/builder/**/*.ts"],
            "Observer": ["src/observer/**/*.ts"],
            "Strategy": ["src/strategy/**/*.ts"],
            "Decorator": ["src/decorator/**/*.ts"],
            "Command": ["src/command/**/*.ts"],
            "State": ["src/state/**/*.ts"],
        }
    },
}

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

OUTPUT_DIR = "dataset_ground_truth_v2"
TEMP_DIR = "temp_clones_curated"

PATTERNS_TO_MINE = [
    "Singleton", "Factory", "AbstractFactory", "Builder", "Prototype",
    "Adapter", "Bridge", "Composite", "Decorator", "Facade", "Flyweight", "Proxy",
    "ChainOfResponsibility", "Command", "Interpreter", "Iterator", "Mediator",
    "Memento", "Observer", "State", "Strategy", "TemplateMethod", "Visitor"
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CuratedSample:
    """Muestra extraída de repositorio curado"""
    pattern_name: str
    source_repo: str
    file_path: str
    code_content: str
    confidence: float
    description: str
    extraction_type: str  # "curated"


# ============================================================================
# MINERO CURADO
# ============================================================================

class CuratedPatternMiner:
    """Minero para repositorios curados específicos"""
    
    def __init__(self):
        self.samples: List[CuratedSample] = []
        self.stats = {}
        
    def setup(self):
        """Configura directorios"""
        if os.path.exists(OUTPUT_DIR):
            print(f"📁 Agregando a dataset existente: {OUTPUT_DIR}")
        else:
            os.makedirs(OUTPUT_DIR)
        
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR)
        
        for pattern in PATTERNS_TO_MINE:
            os.makedirs(os.path.join(OUTPUT_DIR, pattern), exist_ok=True)
    
    def clone_repo(self, name: str, url: str) -> str:
        """Clona un repositorio"""
        repo_dir = os.path.join(TEMP_DIR, name.replace("/", "_"))
        
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
        
        print(f"   📥 Clonando {name}...")
        Repo.clone_from(url, repo_dir, depth=1)
        return repo_dir
    
    def match_glob(self, base_path: str, pattern: str) -> List[str]:
        """Encuentra archivos que coincidan con un patrón glob"""
        import fnmatch
        
        matches = []
        parts = pattern.split('/')
        
        for root, dirs, files in os.walk(base_path):
            rel_root = os.path.relpath(root, base_path)
            
            for file in files:
                if file.endswith('.ts') and not file.endswith('.d.ts'):
                    rel_path = os.path.join(rel_root, file).lstrip('./')
                    
                    # Match con glob simple
                    if '**' in pattern:
                        # Patrón recursivo
                        base_pattern = pattern.replace('**/', '').replace('**', '')
                        dir_match = pattern.split('**')[0].rstrip('/')
                        
                        if rel_root.startswith(dir_match) or dir_match in rel_root:
                            if fnmatch.fnmatch(file, base_pattern.split('/')[-1] if '/' in base_pattern else '*.ts'):
                                matches.append(os.path.join(root, file))
                    else:
                        if fnmatch.fnmatch(rel_path, pattern):
                            matches.append(os.path.join(root, file))
        
        return matches
    
    def is_valid_file(self, file_path: str) -> bool:
        """Valida que sea código fuente válido"""
        filename = os.path.basename(file_path).lower()
        
        if any(x in filename for x in ['test', 'spec', 'mock', '.d.ts']):
            return False
        
        try:
            size = os.path.getsize(file_path)
            if size > 200_000 or size < 100:  # Entre 100 bytes y 200KB
                return False
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Debe tener código estructurado
            if not any(kw in content for kw in ['class ', 'interface ', 'function ', 'export ']):
                return False
            
            return True
        except:
            return False
    
    def extract_from_repo(self, repo_name: str, repo_config: Dict, repo_dir: str):
        """Extrae patrones de un repositorio específico"""
        patterns_config = repo_config.get("patterns", {})
        base_confidence = repo_config.get("confidence", 0.8)
        description = repo_config.get("description", "")
        
        for pattern_name, globs in patterns_config.items():
            if pattern_name not in PATTERNS_TO_MINE:
                continue
            
            for glob_pattern in globs:
                files = self.match_glob(repo_dir, glob_pattern)
                
                for file_path in files:
                    if not self.is_valid_file(file_path):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        rel_path = os.path.relpath(file_path, repo_dir)
                        
                        sample = CuratedSample(
                            pattern_name=pattern_name,
                            source_repo=repo_name,
                            file_path=rel_path,
                            code_content=content,
                            confidence=base_confidence,
                            description=description,
                            extraction_type="curated"
                        )
                        
                        self.save_sample(sample)
                        self.samples.append(sample)
                        
                        # Actualizar stats
                        if pattern_name not in self.stats:
                            self.stats[pattern_name] = 0
                        self.stats[pattern_name] += 1
                        
                    except Exception as e:
                        print(f"      ⚠️ Error leyendo {file_path}: {e}")
    
    def save_sample(self, sample: CuratedSample):
        """Guarda un sample en el dataset"""
        safe_repo = sample.source_repo.replace("/", "_")
        filename = os.path.basename(sample.file_path)
        new_filename = f"{safe_repo}__{filename}"
        
        dest_path = os.path.join(OUTPUT_DIR, sample.pattern_name, new_filename)
        
        # Evitar sobrescribir
        counter = 1
        while os.path.exists(dest_path):
            name, ext = os.path.splitext(new_filename)
            dest_path = os.path.join(OUTPUT_DIR, sample.pattern_name, f"{name}_{counter}{ext}")
            counter += 1
        
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(sample.code_content)
    
    def run(self, repos_to_mine: List[str] = None):
        """Ejecuta minería de repositorios curados"""
        self.setup()
        
        print("🎯 MINERÍA DE REPOSITORIOS CURADOS")
        print("=" * 60)
        
        repos = repos_to_mine if repos_to_mine else list(CURATED_REPOS.keys())
        
        for repo_name in repos:
            if repo_name not in CURATED_REPOS:
                print(f"⚠️ Repo no encontrado en catálogo: {repo_name}")
                continue
            
            config = CURATED_REPOS[repo_name]
            print(f"\n📦 Procesando: {repo_name}")
            print(f"   📝 {config['description']}")
            
            try:
                repo_dir = self.clone_repo(repo_name, config["url"])
                self.extract_from_repo(repo_name, config, repo_dir)
                
                # Limpieza
                shutil.rmtree(repo_dir, ignore_errors=True)
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        self.save_metadata()
        self.print_summary()
    
    def save_metadata(self):
        """Guarda metadatos"""
        metadata = {
            "type": "curated",
            "total_samples": len(self.samples),
            "distribution": self.stats,
            "samples": [
                {
                    "pattern": s.pattern_name,
                    "repo": s.source_repo,
                    "file": s.file_path,
                    "confidence": s.confidence
                }
                for s in self.samples
            ]
        }
        
        with open(os.path.join(OUTPUT_DIR, "curated_metadata.json"), 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def print_summary(self):
        """Imprime resumen"""
        print("\n" + "=" * 60)
        print("✅ EXTRACCIÓN CURADA COMPLETADA")
        print("=" * 60)
        print(f"📊 Total muestras: {len(self.samples)}")
        print("\n📈 Por patrón:")
        
        for pattern in sorted(self.stats.keys()):
            print(f"   {pattern}: {self.stats[pattern]}")
        
        print("=" * 60)


def main():
    """Punto de entrada principal"""
    miner = CuratedPatternMiner()
    
    # Puedes especificar repos específicos o dejar None para todos
    miner.run()


if __name__ == "__main__":
    main()
