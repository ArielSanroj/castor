#!/bin/bash
# ============================================
# 🔄 AI EXTRACT - Detección de Código Duplicado
# ============================================
# Propósito: Identificar código candidato a extracción
# Principio: DRY (Don't Repeat Yourself)
# Atributo de Calidad: Mantenibilidad + Reusabilidad
# ============================================

echo "🔄 ======================================"
echo "   AI EXTRACT - Código Candidato"
echo "========================================"

# 1. Funciones muy largas (candidatas a split)
echo -e "\n📏 [1/5] Funciones con más de 30 líneas (dividir)..."
python3 << 'EOF'
import ast, os

found = []
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
                                    found.append((func_lines, path, node.lineno, node.name))
            except: pass

for lines, path, lineno, name in sorted(found, reverse=True)[:10]:
    print(f"  📐 {lines:3d} líneas: {path}:{lineno} → {name}()")

if not found:
    print("  ✅ Todas las funciones son compactas")
EOF

# 2. Imports repetidos (candidatos a utils)
echo -e "\n📦 [2/5] Imports más comunes (crear módulo utils)..."
echo "  Top 10 imports repetidos:"
grep -rh "^from\|^import" --include="*.py" . 2>/dev/null | \
    grep -v "__pycache__\|\.venv\|node_modules" | \
    sort | uniq -c | sort -rn | head -10 | \
    while read count import; do
        if [ "$count" -gt 3 ]; then
            echo "    ${count}x → $import"
        fi
    done

# 3. Patrones de código similares
echo -e "\n🔍 [3/5] Patrones de validación repetidos..."
echo "  Buscando validaciones duplicadas:"
grep -rn "if.*not.*:" --include="*.py" . 2>/dev/null | \
    grep -v "__pycache__\|\.venv\|node_modules" | \
    sed 's/.*if/if/' | sort | uniq -c | sort -rn | head -5 | \
    while read count pattern; do
        if [ "$count" -gt 2 ]; then
            echo "    ${count}x → ${pattern:0:60}..."
        fi
    done

# 4. Clases con muchos métodos
echo -e "\n🏗️  [4/5] Clases con más de 10 métodos (dividir responsabilidades)..."
python3 << 'EOF'
import ast, os

found = []
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in ["node_modules", ".venv", "__pycache__", ".git", "env"]]
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            try:
                with open(path) as file:
                    tree = ast.parse(file.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                            if len(methods) > 10:
                                found.append((len(methods), path, node.lineno, node.name))
            except: pass

for count, path, lineno, name in sorted(found, reverse=True)[:5]:
    print(f"  🏛️  {count:2d} métodos: {path}:{lineno} → class {name}")

if not found:
    print("  ✅ Todas las clases tienen responsabilidades acotadas")
EOF

# 5. Strings/constantes repetidas
echo -e "\n📝 [5/5] Strings literales repetidos (extraer a constantes)..."
grep -roh "['\"][A-Za-z_][A-Za-z0-9_ ]\{10,\}['\"]" --include="*.py" . 2>/dev/null | \
    grep -v "__pycache__\|\.venv\|node_modules" | \
    sort | uniq -c | sort -rn | head -5 | \
    while read count string; do
        if [ "$count" -gt 2 ]; then
            echo "    ${count}x → ${string:0:50}"
        fi
    done

echo -e "\n========================================"
echo "💡 RECOMENDACIONES DE REFACTORING"
echo "========================================"
cat << 'TIPS'

1. FUNCIONES LARGAS → Extraer sub-funciones
   def proceso_largo():        →  def proceso_largo():
       # 50 líneas                    validar_entrada()
                                      procesar_datos()
                                      formatear_salida()

2. IMPORTS REPETIDOS → Crear módulo de utilidades
   # En cada archivo:          →  # utils/common.py
   from typing import List         from typing import List, Dict, Optional
   from typing import Dict         
   from typing import Optional     # En cada archivo:
                                   from utils.common import *

3. VALIDACIONES DUPLICADAS → Crear decoradores/validators
   if not user:                →  @require_user
       raise Error                def mi_funcion(user): ...

4. CLASES GRANDES → Aplicar Single Responsibility
   class UserManager:          →  class UserCreator: ...
       create(), delete(),        class UserDeleter: ...
       validate(), export()       class UserValidator: ...

TIPS

echo "========================================"
