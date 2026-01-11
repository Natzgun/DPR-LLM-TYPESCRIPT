"""
Mining Repository v2.0 - Minería Avanzada para Detección de Patrones de Diseño
==============================================================================

Mejoras sobre v1:
1. Análisis AST (Abstract Syntax Tree) del código TypeScript
2. Detección de patrones por ESTRUCTURA del código, no solo por nombre de carpeta
3. Extracción de contexto completo (múltiples archivos relacionados)
4. Heurísticas semánticas específicas para cada patrón GoF
5. Scoring de confianza para cada muestra
6. Metadatos enriquecidos para mejor entrenamiento

Autor: Mejorado para ICSE 2026 Research
"""

import os
import re
import shutil
import time
import json
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path
from github import Github
from git import Repo
from dotenv import load_dotenv
from collections import defaultdict
from abc import ABC, abstractmethod

# ============================================================================
# CONFIGURACIÓN AVANZADA
# ============================================================================

# Queries optimizadas para diversidad de fuentes
SEARCH_QUERIES = [
    # 1. Repositorios educativos explícitos (alta confianza)
    "design-patterns typescript language:TypeScript stars:>50",
    "typescript patterns GoF language:TypeScript",
    "typescript design patterns examples language:TypeScript",
    
    # 2. Frameworks conocidos por usar patrones específicos
    "nestjs modules language:TypeScript stars:>100",  # Decorator, Factory, Singleton
    "inversify language:TypeScript",                   # DI/IoC patterns
    "rxjs operators language:TypeScript",              # Observer, Iterator
    
    # 3. Arquitecturas limpias (fuerzan patrones)
    "clean-architecture typescript language:TypeScript",
    "hexagonal architecture typescript language:TypeScript",
    "domain-driven-design typescript language:TypeScript",
    
    # 4. Proyectos enterprise (implementaciones maduras)
    "typescript enterprise language:TypeScript stars:>200",
    "typescript framework language:TypeScript stars:>500",
]

# Configuración de filtrado
MIN_STARS = 10
MAX_REPOS_TO_SCAN = 200
OUTPUT_DIR = "dataset_ground_truth_v2"
TEMP_DIR = "temp_clones"

# Patrones GoF con sus características estructurales
PATTERNS_CONFIG = {
    # --- CREATIONAL ---
    "Singleton": {
        "keywords": ["getInstance", "instance", "singleton"],
        "class_patterns": [r"private\s+static\s+\w*instance", r"private\s+constructor"],
        "structural_hints": ["single instance", "global access point"],
        "min_confidence": 0.6
    },
    "Factory": {
        "keywords": ["create", "factory", "make", "build"],
        "class_patterns": [r"create\w+\s*\(", r"Factory\s*(class|interface)"],
        "structural_hints": ["creates objects", "product interface"],
        "min_confidence": 0.5
    },
    "AbstractFactory": {
        "keywords": ["AbstractFactory", "createProduct", "ProductFamily"],
        "class_patterns": [r"abstract\s+class\s+\w*Factory", r"create\w+\s*\(\s*\):\s*\w+"],
        "structural_hints": ["family of products", "abstract creator"],
        "min_confidence": 0.6
    },
    "Builder": {
        "keywords": ["builder", "build", "setters", "fluent"],
        "class_patterns": [r"\.set\w+\(", r"\.build\s*\(", r"return\s+this"],
        "structural_hints": ["step by step", "fluent interface"],
        "min_confidence": 0.5
    },
    "Prototype": {
        "keywords": ["clone", "prototype", "copy"],
        "class_patterns": [r"clone\s*\(", r"Object\.assign", r"\.\.\.this"],
        "structural_hints": ["cloning", "copy mechanism"],
        "min_confidence": 0.5
    },
    
    # --- STRUCTURAL ---
    "Adapter": {
        "keywords": ["adapter", "wrapper", "adaptee", "target"],
        "class_patterns": [r"implements\s+\w+.*\{[^}]*this\.\w+\.", r"Adapter\s*(class|interface)"],
        "structural_hints": ["interface conversion", "wraps incompatible"],
        "min_confidence": 0.5
    },
    "Bridge": {
        "keywords": ["bridge", "abstraction", "implementor"],
        "class_patterns": [r"protected\s+\w+:\s*\w+Impl", r"abstract.*implementation"],
        "structural_hints": ["separate abstraction", "implementation hierarchy"],
        "min_confidence": 0.6
    },
    "Composite": {
        "keywords": ["composite", "component", "leaf", "children", "add", "remove"],
        "class_patterns": [r"children\s*:\s*\w+\[\]", r"add\s*\(\s*\w+:\s*Component"],
        "structural_hints": ["tree structure", "uniform treatment"],
        "min_confidence": 0.5
    },
    "Decorator": {
        "keywords": ["decorator", "wrapper", "wrappee", "component"],
        "class_patterns": [r"@\w+\s*\(", r"implements.*\{[^}]*this\.wrappee"],
        "structural_hints": ["adds behavior", "wraps object"],
        "min_confidence": 0.5
    },
    "Facade": {
        "keywords": ["facade", "subsystem", "simplified"],
        "class_patterns": [r"class\s+\w*Facade", r"private\s+\w+Subsystem"],
        "structural_hints": ["simplified interface", "hides complexity"],
        "min_confidence": 0.5
    },
    "Flyweight": {
        "keywords": ["flyweight", "cache", "shared", "intrinsic", "extrinsic"],
        "class_patterns": [r"Map<.*Flyweight>", r"cache\s*=\s*new\s*Map"],
        "structural_hints": ["shared state", "memory optimization"],
        "min_confidence": 0.6
    },
    "Proxy": {
        "keywords": ["proxy", "realsubject", "subject"],
        "class_patterns": [r"implements.*\{[^}]*this\.real", r"lazy\s*initialization"],
        "structural_hints": ["controls access", "surrogate"],
        "min_confidence": 0.5
    },
    
    # --- BEHAVIORAL ---
    "ChainOfResponsibility": {
        "keywords": ["handler", "chain", "next", "successor", "handle"],
        "class_patterns": [r"next\s*:\s*\w*Handler", r"setNext\s*\(", r"handleRequest"],
        "structural_hints": ["chain of handlers", "pass request"],
        "min_confidence": 0.6
    },
    "Command": {
        "keywords": ["command", "execute", "invoker", "receiver", "undo"],
        "class_patterns": [r"execute\s*\(\s*\)", r"implements\s+Command", r"undo\s*\(\s*\)"],
        "structural_hints": ["encapsulate request", "parameterize"],
        "min_confidence": 0.5
    },
    "Interpreter": {
        "keywords": ["interpret", "expression", "context", "terminal", "nonterminal"],
        "class_patterns": [r"interpret\s*\(.*Context", r"AbstractExpression"],
        "structural_hints": ["grammar", "language interpretation"],
        "min_confidence": 0.7
    },
    "Iterator": {
        "keywords": ["iterator", "next", "hasNext", "current", "aggregate"],
        "class_patterns": [r"next\s*\(\s*\)", r"hasNext\s*\(\s*\)", r"\[Symbol\.iterator\]"],
        "structural_hints": ["sequential access", "traverse"],
        "min_confidence": 0.5
    },
    "Mediator": {
        "keywords": ["mediator", "colleague", "notify", "mediate"],
        "class_patterns": [r"mediator\s*:\s*\w*Mediator", r"notify\s*\("],
        "structural_hints": ["centralized communication", "loose coupling"],
        "min_confidence": 0.6
    },
    "Memento": {
        "keywords": ["memento", "originator", "caretaker", "state", "restore"],
        "class_patterns": [r"save\s*\(\s*\).*Memento", r"restore\s*\(.*Memento"],
        "structural_hints": ["capture state", "externalize"],
        "min_confidence": 0.6
    },
    "Observer": {
        "keywords": ["observer", "subject", "subscribe", "notify", "update", "listener"],
        "class_patterns": [r"subscribe\s*\(", r"notify\s*\(", r"observers\s*:\s*\w+\[\]"],
        "structural_hints": ["one-to-many", "state change notification"],
        "min_confidence": 0.5
    },
    "State": {
        "keywords": ["state", "context", "transition", "changeState"],
        "class_patterns": [r"state\s*:\s*\w*State", r"setState\s*\(", r"class\s+\w+State"],
        "structural_hints": ["behavior varies", "state transitions"],
        "min_confidence": 0.5
    },
    "Strategy": {
        "keywords": ["strategy", "algorithm", "context", "setStrategy"],
        "class_patterns": [r"strategy\s*:\s*\w*Strategy", r"setStrategy\s*\(", r"execute\s*\("],
        "structural_hints": ["interchangeable algorithms", "family of algorithms"],
        "min_confidence": 0.5
    },
    "TemplateMethod": {
        "keywords": ["template", "hook", "abstract", "algorithm"],
        "class_patterns": [r"abstract\s+\w+\s*\(", r"protected\s+abstract"],
        "structural_hints": ["skeleton algorithm", "defer to subclasses"],
        "min_confidence": 0.6
    },
    "Visitor": {
        "keywords": ["visitor", "visit", "accept", "element"],
        "class_patterns": [r"visit\w+\s*\(", r"accept\s*\(.*Visitor"],
        "structural_hints": ["double dispatch", "separate algorithm"],
        "min_confidence": 0.6
    },
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class PatternDetection:
    """Representa una detección de patrón con metadatos enriquecidos"""
    pattern_name: str
    confidence_score: float
    source_repo: str
    file_path: str
    code_content: str
    detection_method: str  # "folder_name", "ast_analysis", "keyword_match", "structural"
    related_files: List[str]
    class_names: List[str]
    interface_names: List[str]
    method_signatures: List[str]
    imports: List[str]
    lines_of_code: int
    has_tests: bool
    file_hash: str  # Para deduplicación


@dataclass 
class ExtractionContext:
    """Contexto completo de una extracción de patrón"""
    primary_file: str
    related_files: List[str]
    combined_code: str
    pattern: str
    confidence: float


# ============================================================================
# ANALIZADOR DE CÓDIGO TYPESCRIPT
# ============================================================================

class TypeScriptAnalyzer:
    """Analiza código TypeScript para detectar estructuras de patrones"""
    
    @staticmethod
    def extract_classes(code: str) -> List[str]:
        """Extrae nombres de clases del código"""
        pattern = r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)'
        return re.findall(pattern, code)
    
    @staticmethod
    def extract_interfaces(code: str) -> List[str]:
        """Extrae nombres de interfaces del código"""
        pattern = r'(?:export\s+)?interface\s+(\w+)'
        return re.findall(pattern, code)
    
    @staticmethod
    def extract_methods(code: str) -> List[str]:
        """Extrae firmas de métodos del código"""
        # Métodos de clase
        pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::\s*[^{]+)?{'
        return re.findall(pattern, code)
    
    @staticmethod
    def extract_imports(code: str) -> List[str]:
        """Extrae declaraciones de import"""
        pattern = r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]'
        return re.findall(pattern, code)
    
    @staticmethod
    def extract_decorators(code: str) -> List[str]:
        """Extrae decoradores (TypeScript/Angular/NestJS)"""
        pattern = r'@(\w+)\s*\('
        return re.findall(pattern, code)
    
    @staticmethod
    def has_private_constructor(code: str) -> bool:
        """Detecta constructor privado (común en Singleton)"""
        return bool(re.search(r'private\s+constructor\s*\(', code))
    
    @staticmethod
    def has_static_instance(code: str) -> bool:
        """Detecta instancia estática (común en Singleton)"""
        return bool(re.search(r'private\s+static\s+\w*instance', code, re.IGNORECASE))
    
    @staticmethod
    def count_abstract_methods(code: str) -> int:
        """Cuenta métodos abstractos"""
        return len(re.findall(r'abstract\s+\w+\s*\(', code))
    
    @staticmethod
    def has_fluent_interface(code: str) -> bool:
        """Detecta interfaz fluida (return this) común en Builder"""
        return bool(re.search(r'return\s+this\s*;', code))
    
    @staticmethod
    def extract_inheritance(code: str) -> Dict[str, List[str]]:
        """Extrae relaciones de herencia e implementación"""
        extends_pattern = r'class\s+(\w+)\s+extends\s+(\w+)'
        implements_pattern = r'class\s+(\w+)(?:\s+extends\s+\w+)?\s+implements\s+([\w,\s]+)'
        
        inheritance = {"extends": [], "implements": []}
        
        for match in re.finditer(extends_pattern, code):
            inheritance["extends"].append((match.group(1), match.group(2)))
        
        for match in re.finditer(implements_pattern, code):
            interfaces = [i.strip() for i in match.group(2).split(',')]
            inheritance["implements"].append((match.group(1), interfaces))
        
        return inheritance


# ============================================================================
# DETECTORES DE PATRONES
# ============================================================================

class PatternDetector(ABC):
    """Clase base para detectores de patrones específicos"""
    
    @abstractmethod
    def detect(self, code: str, file_path: str) -> Tuple[bool, float, str]:
        """
        Detecta si el código contiene el patrón
        Returns: (detected: bool, confidence: float, method: str)
        """
        pass
    
    @property
    @abstractmethod
    def pattern_name(self) -> str:
        pass


class SingletonDetector(PatternDetector):
    """Detector especializado para Singleton"""
    
    @property
    def pattern_name(self) -> str:
        return "Singleton"
    
    def detect(self, code: str, file_path: str) -> Tuple[bool, float, str]:
        score = 0.0
        
        # Criterio 1: Constructor privado (fuerte indicador)
        if TypeScriptAnalyzer.has_private_constructor(code):
            score += 0.4
        
        # Criterio 2: Instancia estática
        if TypeScriptAnalyzer.has_static_instance(code):
            score += 0.3
        
        # Criterio 3: Método getInstance
        if re.search(r'getInstance\s*\(', code):
            score += 0.2
        
        # Criterio 4: Nombre de archivo/clase
        if "singleton" in file_path.lower() or "singleton" in code.lower():
            score += 0.1
        
        return score >= 0.5, min(score, 1.0), "structural_analysis"


class ObserverDetector(PatternDetector):
    """Detector especializado para Observer"""
    
    @property
    def pattern_name(self) -> str:
        return "Observer"
    
    def detect(self, code: str, file_path: str) -> Tuple[bool, float, str]:
        score = 0.0
        
        # Criterio 1: Array de observers/subscribers
        if re.search(r'(observers|subscribers|listeners)\s*:\s*\w+\[\]', code, re.IGNORECASE):
            score += 0.3
        
        # Criterio 2: Métodos subscribe/unsubscribe
        if re.search(r'(subscribe|attach|addObserver)\s*\(', code):
            score += 0.25
        if re.search(r'(unsubscribe|detach|removeObserver)\s*\(', code):
            score += 0.15
        
        # Criterio 3: Método notify/update
        if re.search(r'(notify|notifyAll|update)\s*\(', code):
            score += 0.2
        
        # Criterio 4: Interfaz Observer
        if re.search(r'interface\s+\w*Observer', code):
            score += 0.1
        
        return score >= 0.5, min(score, 1.0), "structural_analysis"


class FactoryDetector(PatternDetector):
    """Detector especializado para Factory Method"""
    
    @property
    def pattern_name(self) -> str:
        return "Factory"
    
    def detect(self, code: str, file_path: str) -> Tuple[bool, float, str]:
        score = 0.0
        
        # Criterio 1: Método create que retorna objetos
        if re.search(r'create\w*\s*\([^)]*\)\s*:\s*\w+', code):
            score += 0.3
        
        # Criterio 2: Clase/interfaz con "Factory" en el nombre
        if re.search(r'(class|interface)\s+\w*Factory', code):
            score += 0.25
        
        # Criterio 3: Switch/if para crear diferentes tipos
        if re.search(r'switch\s*\([^)]+\)\s*\{', code) or re.search(r'if\s*\([^)]*type', code):
            score += 0.15
        
        # Criterio 4: Retorna new de diferentes clases
        new_count = len(re.findall(r'return\s+new\s+\w+', code))
        if new_count >= 2:
            score += 0.2
        
        # Criterio 5: Nombre del archivo
        if "factory" in file_path.lower():
            score += 0.1
        
        return score >= 0.5, min(score, 1.0), "structural_analysis"


class BuilderDetector(PatternDetector):
    """Detector especializado para Builder"""
    
    @property
    def pattern_name(self) -> str:
        return "Builder"
    
    def detect(self, code: str, file_path: str) -> Tuple[bool, float, str]:
        score = 0.0
        
        # Criterio 1: Interfaz fluida (return this)
        if TypeScriptAnalyzer.has_fluent_interface(code):
            score += 0.35
        
        # Criterio 2: Método build()
        if re.search(r'build\s*\(\s*\)\s*:', code):
            score += 0.25
        
        # Criterio 3: Múltiples setters
        setter_count = len(re.findall(r'(set\w+|with\w+)\s*\([^)]+\)', code))
        if setter_count >= 3:
            score += 0.2
        
        # Criterio 4: Nombre Builder
        if re.search(r'(class|interface)\s+\w*Builder', code):
            score += 0.15
        
        # Criterio 5: Nombre del archivo
        if "builder" in file_path.lower():
            score += 0.05
        
        return score >= 0.5, min(score, 1.0), "structural_analysis"


class StrategyDetector(PatternDetector):
    """Detector especializado para Strategy"""
    
    @property
    def pattern_name(self) -> str:
        return "Strategy"
    
    def detect(self, code: str, file_path: str) -> Tuple[bool, float, str]:
        score = 0.0
        
        # Criterio 1: Interfaz Strategy con método execute/algorithm
        if re.search(r'interface\s+\w*Strategy', code):
            score += 0.25
        
        # Criterio 2: Campo strategy en contexto
        if re.search(r'(private|protected)\s+strategy\s*:', code):
            score += 0.25
        
        # Criterio 3: Método setStrategy
        if re.search(r'setStrategy\s*\(', code):
            score += 0.2
        
        # Criterio 4: Múltiples clases implementando misma interfaz
        implements = re.findall(r'class\s+\w+\s+implements\s+(\w+Strategy)', code)
        if len(implements) >= 2:
            score += 0.2
        
        # Criterio 5: Nombre del archivo
        if "strategy" in file_path.lower():
            score += 0.1
        
        return score >= 0.5, min(score, 1.0), "structural_analysis"


class DecoratorDetector(PatternDetector):
    """Detector especializado para Decorator"""
    
    @property
    def pattern_name(self) -> str:
        return "Decorator"
    
    def detect(self, code: str, file_path: str) -> Tuple[bool, float, str]:
        score = 0.0
        
        # Criterio 1: Decoradores TypeScript (@)
        decorators = TypeScriptAnalyzer.extract_decorators(code)
        if decorators:
            score += 0.3
        
        # Criterio 2: Wrapper pattern
        if re.search(r'(wrappee|wrapped|component)\s*:', code):
            score += 0.25
        
        # Criterio 3: Clase que implementa misma interfaz y tiene referencia
        if re.search(r'implements\s+\w+.*\{[^}]*this\.(wrappee|wrapped|component)', code, re.DOTALL):
            score += 0.25
        
        # Criterio 4: Nombre Decorator
        if re.search(r'(class|interface)\s+\w*Decorator', code):
            score += 0.15
        
        # Criterio 5: Nombre del archivo
        if "decorator" in file_path.lower():
            score += 0.05
        
        return score >= 0.5, min(score, 1.0), "structural_analysis"


class CommandDetector(PatternDetector):
    """Detector especializado para Command"""
    
    @property
    def pattern_name(self) -> str:
        return "Command"
    
    def detect(self, code: str, file_path: str) -> Tuple[bool, float, str]:
        score = 0.0
        
        # Criterio 1: Interfaz Command con execute
        if re.search(r'interface\s+\w*Command.*execute\s*\(', code, re.DOTALL):
            score += 0.3
        
        # Criterio 2: Método execute sin parámetros
        if re.search(r'execute\s*\(\s*\)\s*:', code):
            score += 0.2
        
        # Criterio 3: Método undo
        if re.search(r'undo\s*\(\s*\)', code):
            score += 0.2
        
        # Criterio 4: Invoker con lista de comandos
        if re.search(r'commands\s*:\s*\w*Command\[\]', code):
            score += 0.2
        
        # Criterio 5: Nombre del archivo
        if "command" in file_path.lower():
            score += 0.1
        
        return score >= 0.5, min(score, 1.0), "structural_analysis"


# Registro de detectores especializados
SPECIALIZED_DETECTORS = {
    "Singleton": SingletonDetector(),
    "Observer": ObserverDetector(),
    "Factory": FactoryDetector(),
    "Builder": BuilderDetector(),
    "Strategy": StrategyDetector(),
    "Decorator": DecoratorDetector(),
    "Command": CommandDetector(),
}


# ============================================================================
# DETECTOR GENÉRICO (para patrones sin detector especializado)
# ============================================================================

class GenericPatternDetector:
    """Detector genérico basado en configuración"""
    
    @staticmethod
    def detect(code: str, file_path: str, pattern_name: str) -> Tuple[bool, float, str]:
        config = PATTERNS_CONFIG.get(pattern_name, {})
        score = 0.0
        
        # 1. Coincidencia por keywords
        keywords = config.get("keywords", [])
        keyword_matches = sum(1 for kw in keywords if kw.lower() in code.lower())
        if keyword_matches > 0:
            score += min(keyword_matches * 0.1, 0.3)
        
        # 2. Coincidencia por patrones de código
        class_patterns = config.get("class_patterns", [])
        for pattern in class_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                score += 0.2
                break
        
        # 3. Coincidencia por nombre de carpeta/archivo
        path_lower = file_path.lower()
        if pattern_name.lower() in path_lower:
            score += 0.3
        
        min_confidence = config.get("min_confidence", 0.5)
        return score >= min_confidence, min(score, 1.0), "generic_analysis"


# ============================================================================
# EXTRACTOR PRINCIPAL
# ============================================================================

class AdvancedPatternMiner:
    """Minero avanzado de patrones de diseño"""
    
    def __init__(self, github_token: str):
        self.github = Github(github_token)
        self.processed_repos: Set[str] = set()
        self.extracted_hashes: Set[str] = set()  # Para deduplicación
        self.detections: List[PatternDetection] = []
        self.stats = defaultdict(int)
        
    def setup_directories(self):
        """Configura directorios de salida"""
        if os.path.exists(OUTPUT_DIR):
            print(f"⚠️  La carpeta {OUTPUT_DIR} ya existe. Se agregarán nuevos datos.")
        else:
            os.makedirs(OUTPUT_DIR)
        
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR)
        
        for pattern in PATTERNS_CONFIG.keys():
            os.makedirs(os.path.join(OUTPUT_DIR, pattern), exist_ok=True)
    
    def is_valid_source_code(self, file_path: str) -> bool:
        """Valida que el archivo sea código fuente válido"""
        filename_lower = os.path.basename(file_path).lower()
        
        # Excluir tests y specs
        if any(x in filename_lower for x in ["test", "spec", ".d.ts", "mock"]):
            return False
        
        try:
            if os.path.getsize(file_path) > 500_000:  # 500KB max
                return False
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                if not lines:
                    return False
                
                # Detectar código minificado
                if max(len(line) for line in lines) > 500:
                    return False
                
                content = "".join(lines)
                
                # Debe tener estructura de clase/interfaz
                if not any(kw in content for kw in ['class ', 'interface ', 'abstract ']):
                    return False
                
                # Mínimo de líneas significativas
                meaningful_lines = [l for l in lines if l.strip() and not l.strip().startswith('//')]
                if len(meaningful_lines) < 10:
                    return False
                
                return True
        except Exception:
            return False
    
    def compute_file_hash(self, content: str) -> str:
        """Calcula hash del contenido para deduplicación"""
        # Normalizar antes de hash (eliminar espacios y comentarios)
        normalized = re.sub(r'//.*|/\*.*?\*/', '', content, flags=re.DOTALL)
        normalized = re.sub(r'\s+', '', normalized)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def find_related_files(self, file_path: str, root_dir: str) -> List[str]:
        """Encuentra archivos relacionados (imports, mismo directorio)"""
        related = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            imports = TypeScriptAnalyzer.extract_imports(content)
            current_dir = os.path.dirname(file_path)
            
            # Buscar archivos importados
            for imp in imports:
                if imp.startswith('.'):
                    imp_path = os.path.normpath(os.path.join(current_dir, imp))
                    for ext in ['.ts', '.tsx', '/index.ts']:
                        full_path = imp_path + ext if not imp_path.endswith(ext) else imp_path
                        if os.path.exists(full_path):
                            related.append(full_path)
                            break
            
            # Incluir archivos del mismo directorio
            for f in os.listdir(current_dir):
                if f.endswith('.ts') and not f.endswith('.d.ts'):
                    full_path = os.path.join(current_dir, f)
                    if full_path != file_path and full_path not in related:
                        related.append(full_path)
        except Exception:
            pass
        
        return related[:10]  # Limitar a 10 archivos relacionados
    
    def detect_pattern_in_file(self, file_path: str, code: str) -> List[Tuple[str, float, str]]:
        """Detecta todos los patrones posibles en un archivo"""
        detections = []
        
        for pattern_name in PATTERNS_CONFIG.keys():
            # Usar detector especializado si existe
            if pattern_name in SPECIALIZED_DETECTORS:
                detector = SPECIALIZED_DETECTORS[pattern_name]
                detected, confidence, method = detector.detect(code, file_path)
            else:
                detected, confidence, method = GenericPatternDetector.detect(code, file_path, pattern_name)
            
            if detected:
                detections.append((pattern_name, confidence, method))
        
        # Ordenar por confianza descendente
        detections.sort(key=lambda x: x[1], reverse=True)
        return detections
    
    def extract_pattern(self, file_path: str, repo_name: str, local_path: str) -> List[PatternDetection]:
        """Extrae patrones detectados de un archivo"""
        detections = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            
            # Verificar duplicados
            file_hash = self.compute_file_hash(code)
            if file_hash in self.extracted_hashes:
                return []
            
            # Detectar patrones
            pattern_detections = self.detect_pattern_in_file(file_path, code)
            
            if not pattern_detections:
                return []
            
            # Extraer metadata
            classes = TypeScriptAnalyzer.extract_classes(code)
            interfaces = TypeScriptAnalyzer.extract_interfaces(code)
            methods = TypeScriptAnalyzer.extract_methods(code)
            imports = TypeScriptAnalyzer.extract_imports(code)
            related_files = self.find_related_files(file_path, local_path)
            lines = len(code.split('\n'))
            
            # Crear detección para el patrón con mayor confianza
            best_pattern, confidence, method = pattern_detections[0]
            
            # Solo aceptar si la confianza es suficiente
            min_conf = PATTERNS_CONFIG[best_pattern].get("min_confidence", 0.5)
            if confidence < min_conf:
                return []
            
            self.extracted_hashes.add(file_hash)
            
            detection = PatternDetection(
                pattern_name=best_pattern,
                confidence_score=confidence,
                source_repo=repo_name,
                file_path=file_path.replace(TEMP_DIR, ""),
                code_content=code,
                detection_method=method,
                related_files=[f.replace(TEMP_DIR, "") for f in related_files],
                class_names=classes,
                interface_names=interfaces,
                method_signatures=methods[:20],  # Limitar
                imports=imports,
                lines_of_code=lines,
                has_tests=any("test" in f.lower() or "spec" in f.lower() for f in related_files),
                file_hash=file_hash
            )
            
            detections.append(detection)
            
        except Exception as e:
            print(f"⚠️ Error procesando {file_path}: {e}")
        
        return detections
    
    def analyze_repository(self, repo_name: str, local_path: str) -> List[PatternDetection]:
        """Analiza un repositorio completo"""
        print(f"   🔍 Analizando: {repo_name}...")
        all_detections = []
        
        for root, dirs, files in os.walk(local_path):
            # Ignorar node_modules, dist, etc.
            dirs[:] = [d for d in dirs if d not in ['node_modules', 'dist', 'build', '.git', 'coverage']]
            
            for file in files:
                if file.endswith('.ts') and not file.endswith('.d.ts'):
                    file_path = os.path.join(root, file)
                    
                    if self.is_valid_source_code(file_path):
                        detections = self.extract_pattern(file_path, repo_name, local_path)
                        all_detections.extend(detections)
        
        return all_detections
    
    def save_detection(self, detection: PatternDetection):
        """Guarda un archivo detectado en el dataset"""
        safe_repo_name = detection.source_repo.replace("/", "_")
        original_filename = os.path.basename(detection.file_path)
        new_filename = f"{safe_repo_name}__{original_filename}"
        
        dest_dir = os.path.join(OUTPUT_DIR, detection.pattern_name)
        dest_file = os.path.join(dest_dir, new_filename)
        
        # Evitar sobrescribir
        counter = 1
        while os.path.exists(dest_file):
            name, ext = os.path.splitext(new_filename)
            dest_file = os.path.join(dest_dir, f"{name}_{counter}{ext}")
            counter += 1
        
        with open(dest_file, 'w', encoding='utf-8') as f:
            f.write(detection.code_content)
        
        self.stats[detection.pattern_name] += 1
    
    def run(self):
        """Ejecuta la minería completa"""
        self.setup_directories()
        
        print("🚀 Iniciando minería avanzada de patrones de diseño...")
        print(f"🎯 Objetivo: Dataset TypeScript Ground Truth v2.0")
        print(f"📊 Patrones a detectar: {len(PATTERNS_CONFIG)}")
        
        repo_count = 0
        
        try:
            for query in SEARCH_QUERIES:
                if repo_count >= MAX_REPOS_TO_SCAN:
                    break
                
                print(f"\n🔎 Ejecutando consulta: '{query}'")
                repos = self.github.search_repositories(query=query, sort="stars", order="desc")
                
                for repo in repos:
                    if repo_count >= MAX_REPOS_TO_SCAN:
                        break
                    if repo.full_name in self.processed_repos:
                        continue
                    if repo.stargazers_count < MIN_STARS:
                        continue
                    
                    print(f"\n[{repo_count+1}/{MAX_REPOS_TO_SCAN}] Clonando: {repo.full_name} (⭐ {repo.stargazers_count})")
                    
                    repo_dir = os.path.join(TEMP_DIR, repo.name)
                    
                    try:
                        Repo.clone_from(repo.clone_url, repo_dir, depth=1)
                        
                        detections = self.analyze_repository(repo.full_name, repo_dir)
                        
                        for detection in detections:
                            self.save_detection(detection)
                            self.detections.append(detection)
                        
                        if detections:
                            print(f"   ✅ Encontrados: {len(detections)} patrones")
                        
                        self.processed_repos.add(repo.full_name)
                        repo_count += 1
                        
                    except Exception as e:
                        print(f"⚠️ Error procesando {repo.full_name}: {e}")
                    
                    finally:
                        if os.path.exists(repo_dir):
                            time.sleep(0.5)
                            try:
                                shutil.rmtree(repo_dir, ignore_errors=True)
                            except:
                                pass
                    
                    # Rate limiting
                    time.sleep(0.5)
        
        except Exception as e:
            print(f"\n❌ Error crítico: {e}")
        
        # Guardar metadatos enriquecidos
        self.save_metadata()
        self.print_summary()
    
    def save_metadata(self):
        """Guarda metadatos completos del dataset"""
        metadata = {
            "version": "2.0",
            "total_samples": len(self.detections),
            "repos_processed": len(self.processed_repos),
            "pattern_distribution": dict(self.stats),
            "samples": [asdict(d) for d in self.detections]
        }
        
        # Remover code_content del metadata para no duplicar
        for sample in metadata["samples"]:
            sample.pop("code_content", None)
        
        with open(os.path.join(OUTPUT_DIR, "dataset_metadata_v2.json"), 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def print_summary(self):
        """Imprime resumen de la minería"""
        print("\n" + "=" * 60)
        print("✅ MINERÍA COMPLETADA - RESUMEN")
        print("=" * 60)
        print(f"📂 Dataset generado en: {os.path.abspath(OUTPUT_DIR)}")
        print(f"📊 Total de muestras: {len(self.detections)}")
        print(f"🔗 Repositorios procesados: {len(self.processed_repos)}")
        print("\n📈 Distribución por patrón:")
        
        for pattern, count in sorted(self.stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {pattern}: {count}")
        
        # Advertencias de desbalance
        if self.stats:
            avg = sum(self.stats.values()) / len(self.stats)
            underrepresented = [p for p, c in self.stats.items() if c < avg * 0.3]
            if underrepresented:
                print(f"\n⚠️ Patrones sub-representados: {', '.join(underrepresented)}")
                print("   Considera agregar repositorios específicos para estos patrones.")
        
        print("=" * 60)


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

def main():
    load_dotenv()
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    
    if not GITHUB_TOKEN:
        print("❌ Error: Necesitas un GitHub Token válido en el archivo .env")
        return
    
    miner = AdvancedPatternMiner(GITHUB_TOKEN)
    miner.run()


if __name__ == "__main__":
    main()
