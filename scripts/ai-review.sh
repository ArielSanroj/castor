#!/bin/bash
# ============================================
# 🔍 AI CODE REVIEW - Quality Gates
# ============================================
# Propósito: Revisión automatizada pre-commit
# Atributo de Calidad: Detectabilidad + Prevención
# ============================================

set -e

echo "🔍 ======================================"
echo "   AI CODE REVIEW - Quality Gates"
echo "========================================"

# 1. Verificar sintaxis
echo -e "\n📋 [1/6] Verificando sintaxis Python..."
syntax_errors=0
while IFS= read -r -d '' file; do
    if ! python -m py_compile "$file" 2>/dev/null; then
        echo "  ❌ Error de sintaxis: $file"
        ((syntax_errors++))
    fi
done < <(find . -name "*.py" ! -path "*/.venv/*" ! -path "*/node_modules/*" -print0 2>/dev/null)

if [ "$syntax_errors" -eq 0 ]; then
    echo "  ✅ Sintaxis correcta en todos los archivos"
fi

# 2. Buscar dependencias circulares
echo -e "\n🔄 [2/6] Buscando dependencias circulares..."
python3 << 'EOF'
import ast, os
from collections import defaultdict

imports = defaultdict(set)
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in ["node_modules", ".venv", "__pycache__", ".git", "env"]]
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            try:
                with open(path) as file:
                    tree = ast.parse(file.read())
                    module = path.replace("/", ".").replace(".py", "").lstrip(".")
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom) and node.module:
                            imports[module].add(node.module)
            except: pass

found = False
for mod, deps in imports.items():
    for dep in deps:
        if dep in imports and mod in imports[dep]:
            print(f"  ⚠️  CIRCULAR: {mod} <-> {dep}")
            found = True
if not found:
    print("  ✅ No se encontraron dependencias circulares")
EOF

# 3. Revisar archivos grandes (>300 líneas)
echo -e "\n📏 [3/6] Verificando tamaño de archivos..."
big_files=0
while IFS= read -r file; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file")
        if [ "$lines" -gt 300 ]; then
            echo "  ⚠️  $file tiene $lines líneas (máximo: 300)"
            ((big_files++))
        fi
    fi
done < <(find . -name "*.py" ! -path "*/.venv/*" ! -path "*/node_modules/*" 2>/dev/null)

if [ "$big_files" -eq 0 ]; then
    echo "  ✅ Todos los archivos están bajo 300 líneas"
fi

# 4. Buscar funciones muy largas
echo -e "\n📐 [4/6] Buscando funciones largas (>30 líneas)..."
python3 << 'EOF'
import ast, os

found = False
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in ["node_modules", ".venv", "__pycache__", ".git", "env"]]
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            try:
                with open(path) as file:
                    content = file.read()
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if hasattr(node, 'end_lineno'):
                                func_lines = node.end_lineno - node.lineno
                                if func_lines > 30:
                                    print(f"  ⚠️  {path}:{node.lineno} - {node.name}() = {func_lines} líneas")
                                    found = True
            except: pass
if not found:
    print("  ✅ Todas las funciones están bajo 30 líneas")
EOF

# 5. Verificar que existen tests
echo -e "\n🧪 [5/6] Verificando cobertura de tests..."
src_count=$(find . -path "*/src/*.py" ! -name "__init__.py" 2>/dev/null | wc -l || echo "0")
test_count=$(find . -path "*/tests/*.py" -name "test_*.py" 2>/dev/null | wc -l || echo "0")
echo "  📊 Archivos fuente: $src_count | Tests: $test_count"

if [ "$src_count" -gt 0 ] && [ "$test_count" -eq 0 ]; then
    echo "  ⚠️  No hay tests. Considera agregar tests unitarios."
fi

# 6. Revisar TODOs críticos
echo -e "\n📝 [6/6] TODOs y FIXMEs pendientes..."
todos=$(grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.py" . 2>/dev/null | head -10)
if [ -n "$todos" ]; then
    echo "$todos" | while read -r line; do
        echo "  📌 $line"
    done
else
    echo "  ✅ No hay TODOs pendientes"
fi

echo -e "\n✅ ======================================"
echo "   Revisión completada"
echo "========================================"
