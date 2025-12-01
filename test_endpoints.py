#!/usr/bin/env python3
"""
Wrapper script para ejecutar test_endpoints.py desde la raíz del proyecto.
"""
import sys
import os
from pathlib import Path

# Cambiar al directorio backend
backend_dir = Path(__file__).parent / "backend"
os.chdir(backend_dir)

# Ejecutar el script con los argumentos pasados
sys.path.insert(0, str(backend_dir))
from test_endpoints import main

if __name__ == "__main__":
    main()

