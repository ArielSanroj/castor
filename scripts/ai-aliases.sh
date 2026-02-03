# ============================================
# 🤖 AI ALIASES - Comandos Rápidos para Desarrollo
# ============================================
# Instalación: Agregar a ~/.bashrc o ~/.zshrc
#   source ~/path/to/ai-aliases.sh
# ============================================

# ============================================
# 🔍 ANÁLISIS Y REVISIÓN
# ============================================

# Revisión completa del proyecto
alias ai-review='bash scripts/ai-review.sh'

# Verificar CTO Rules
alias ai-cto='bash scripts/cto-check.sh'

# Detectar código extraíble
alias ai-extract='bash scripts/ai-extract.sh'

# Ver estructura del proyecto
alias ai-tree='tree -I "node_modules|.venv|__pycache__|.git|env" -L 3'

# Buscar dependencias circulares rápido
alias ai-circular='python3 -c "
import ast, os
from collections import defaultdict
imports = defaultdict(set)
for root, dirs, files in os.walk(\".\"):
    dirs[:] = [d for d in dirs if d not in [\"node_modules\", \".venv\", \"__pycache__\", \".git\"]]
    for f in files:
        if f.endswith(\".py\"):
            try:
                with open(os.path.join(root, f)) as file:
                    tree = ast.parse(file.read())
                    module = os.path.join(root, f).replace(\"/\", \".\").replace(\".py\", \"\").lstrip(\".\")
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom) and node.module:
                            imports[module].add(node.module)
            except: pass
for mod, deps in imports.items():
    for dep in deps:
        if dep in imports and mod in imports[dep]:
            print(f\"⚠️  {mod} <-> {dep}\")
"'

# ============================================
# 📏 MÉTRICAS RÁPIDAS
# ============================================

# Contar líneas de código
alias ai-loc='find . -name "*.py" ! -path "*/.venv/*" ! -path "*/node_modules/*" -exec cat {} \; | wc -l'

# Archivos más grandes
alias ai-big='find . -name "*.py" ! -path "*/.venv/*" ! -path "*/node_modules/*" -exec wc -l {} \; | sort -rn | head -10'

# TODOs pendientes
alias ai-todos='grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.py" . 2>/dev/null | head -20'

# Complejidad (archivos con más de 5 clases/funciones)
alias ai-complex='python3 -c "
import ast, os
for root, dirs, files in os.walk(\".\"):
    dirs[:] = [d for d in dirs if d not in [\"node_modules\", \".venv\", \"__pycache__\", \".git\"]]
    for f in files:
        if f.endswith(\".py\"):
            path = os.path.join(root, f)
            try:
                with open(path) as file:
                    tree = ast.parse(file.read())
                    funcs = len([n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))])
                    classes = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
                    if funcs + classes > 10:
                        print(f\"⚠️  {path}: {funcs} funciones, {classes} clases\")
            except: pass
"'

# ============================================
# 🛠️ SCAFFOLDING
# ============================================

# Crear módulo con estructura Clean Architecture
ai-module() {
    if [ -z "$1" ]; then
        echo "Uso: ai-module <nombre_modulo>"
        return 1
    fi
    mkdir -p "src/$1/"{domain/entities,domain/repositories,application/use_cases,infrastructure/persistence}
    touch "src/$1/__init__.py"
    touch "src/$1/domain/__init__.py"
    touch "src/$1/domain/entities/__init__.py"
    touch "src/$1/domain/repositories/__init__.py"
    touch "src/$1/application/__init__.py"
    touch "src/$1/application/use_cases/__init__.py"
    touch "src/$1/infrastructure/__init__.py"
    touch "src/$1/infrastructure/persistence/__init__.py"
    echo "✅ Módulo '$1' creado con estructura Clean Architecture"
}

# Crear test template
ai-test() {
    if [ -z "$1" ]; then
        echo "Uso: ai-test <nombre_modulo>"
        return 1
    fi
    mkdir -p tests
    cat > "tests/test_$1.py" << EOF
import pytest
from unittest.mock import Mock, patch


class Test${1^}:
    """Tests for $1 module."""
    
    def setup_method(self):
        """Setup test fixtures."""
        pass
    
    def test_should_succeed_when_valid_input(self):
        """Test happy path."""
        # Arrange
        expected = None
        
        # Act
        result = None
        
        # Assert
        assert result == expected
    
    def test_should_fail_when_invalid_input(self):
        """Test error handling."""
        # Arrange
        
        # Act & Assert
        with pytest.raises(ValueError):
            pass
EOF
    echo "✅ Test template creado: tests/test_$1.py"
}

# ============================================
# 🚀 GIT HELPERS
# ============================================

# Pre-commit check rápido
alias ai-precommit='ai-review && echo "✅ Listo para commit"'

# Ver cambios staged
alias ai-staged='git diff --cached --stat'

# Verificar antes de push
alias ai-prepush='ai-cto && echo "✅ Listo para push"'

# ============================================
# 📊 REPORTES
# ============================================

# Reporte rápido del proyecto
ai-report() {
    echo "📊 PROJECT REPORT"
    echo "================="
    echo ""
    echo "📏 Líneas de código:"
    find . -name "*.py" ! -path "*/.venv/*" ! -path "*/node_modules/*" -exec cat {} \; 2>/dev/null | wc -l
    echo ""
    echo "📁 Archivos Python:"
    find . -name "*.py" ! -path "*/.venv/*" ! -path "*/node_modules/*" 2>/dev/null | wc -l
    echo ""
    echo "🧪 Archivos de test:"
    find . -name "test_*.py" 2>/dev/null | wc -l
    echo ""
    echo "📝 TODOs pendientes:"
    grep -rn "TODO\|FIXME" --include="*.py" . 2>/dev/null | wc -l
}

echo "✅ AI Aliases cargados. Usa 'ai-review', 'ai-cto', 'ai-extract', etc."
