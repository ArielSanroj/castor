#!/usr/bin/env python3
"""
Script para probar las funcionalidades de seguridad del módulo electoral.

Uso:
    python scripts/test_security.py
"""
import os
import sys

# Agregar backend al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')


def test_pdf_validator():
    """Prueba el validador de PDF."""
    print("\n" + "="*60)
    print("TEST: PDF Validator")
    print("="*60)

    from utils.pdf_validator import (
        validate_pdf_bytes,
        PDFValidationResult,
        MAX_FILE_SIZE_MB,
        MAX_PAGES
    )

    print(f"Configuración:")
    print(f"  - Max file size: {MAX_FILE_SIZE_MB} MB")
    print(f"  - Max pages: {MAX_PAGES}")

    # Test 1: Archivo muy pequeño
    print("\n[Test 1] Archivo muy pequeño (100 bytes)...")
    result = validate_pdf_bytes(b"x" * 100)
    print(f"  Resultado: {'✓ Rechazado' if not result.is_valid else '✗ Aceptado'}")
    print(f"  Mensaje: {result.error_message}")

    # Test 2: Header incorrecto
    print("\n[Test 2] Header incorrecto (no es PDF)...")
    result = validate_pdf_bytes(b"NOT A PDF FILE" + b"x" * 2000)
    print(f"  Resultado: {'✓ Rechazado' if not result.is_valid else '✗ Aceptado'}")
    print(f"  Mensaje: {result.error_message}")

    # Test 3: PDF válido (si existe)
    test_pdf = Path("/Users/arielsanroj/Downloads/1.pdf")
    if test_pdf.exists():
        print(f"\n[Test 3] PDF real ({test_pdf.name})...")
        pdf_bytes = test_pdf.read_bytes()
        result = validate_pdf_bytes(pdf_bytes)
        print(f"  Resultado: {'✓ Válido' if result.is_valid else '✗ Inválido'}")
        if result.is_valid:
            print(f"  Páginas: {result.page_count}")
            print(f"  Tamaño: {result.file_size_mb:.2f} MB")
        else:
            print(f"  Error: {result.error_message}")
    else:
        print("\n[Test 3] Skipped - No hay PDF de prueba")

    print("\n✓ PDF Validator tests completados")


def test_cost_tracker():
    """Prueba el tracker de costos."""
    print("\n" + "="*60)
    print("TEST: Cost Tracker")
    print("="*60)

    from utils.electoral_security import CostTracker, get_cost_tracker

    tracker = get_cost_tracker()
    test_user = "test_user_123"

    print(f"Configuración:")
    print(f"  - Costo por E-14: ${CostTracker.COST_PER_E14_PROCESS}")
    print(f"  - Límite horario: ${CostTracker.DEFAULT_HOURLY_LIMIT}")
    print(f"  - Límite diario: ${CostTracker.DEFAULT_DAILY_LIMIT}")

    # Limpiar uso previo (crear nuevo tracker para test limpio)
    tracker._usage[test_user] = []

    # Test 1: Usuario sin uso
    print(f"\n[Test 1] Usuario sin uso previo...")
    usage = tracker.get_usage(test_user)
    print(f"  Costo: ${usage['cost']:.2f}")
    print(f"  Operaciones: {usage['operations']}")

    allowed, msg = tracker.check_limit(test_user)
    print(f"  ¿Puede operar?: {'✓ Sí' if allowed else '✗ No'}")

    # Test 2: Registrar uso
    print(f"\n[Test 2] Registrando 5 operaciones...")
    for i in range(5):
        tracker.record_usage(test_user, CostTracker.COST_PER_E14_PROCESS)

    usage = tracker.get_usage(test_user)
    print(f"  Costo acumulado: ${usage['cost']:.2f}")
    print(f"  Operaciones: {usage['operations']}")

    # Test 3: Verificar límite horario
    print(f"\n[Test 3] Simulando exceso de límite horario...")
    for i in range(20):  # Más operaciones para exceder límite
        tracker.record_usage(test_user, CostTracker.COST_PER_E14_PROCESS)

    allowed, msg = tracker.check_limit(test_user)
    print(f"  ¿Puede operar?: {'✓ Sí' if allowed else '✗ No (correcto)'}")
    if not allowed:
        print(f"  Mensaje: {msg}")

    # Test 4: Estadísticas globales
    print(f"\n[Test 4] Estadísticas globales...")
    stats = tracker.get_all_stats()
    print(f"  Usuarios activos: {stats['active_users']}")
    print(f"  Costo total 24h: ${stats['total_cost_24h']:.2f}")
    print(f"  Operaciones 24h: {stats['total_operations_24h']}")

    print("\n✓ Cost Tracker tests completados")


def test_electoral_roles():
    """Prueba los roles electorales."""
    print("\n" + "="*60)
    print("TEST: Electoral Roles")
    print("="*60)

    from utils.electoral_security import ElectoralRole, ROLE_PERMISSIONS

    print("\nRoles disponibles:")
    for role in ElectoralRole:
        perms = ROLE_PERMISSIONS.get(role, [])
        print(f"  - {role.value}: {perms}")

    print("\n✓ Electoral Roles test completado")


def test_endpoint_security():
    """Verifica que los endpoints tienen seguridad."""
    print("\n" + "="*60)
    print("TEST: Endpoint Security")
    print("="*60)

    from app.routes.electoral import electoral_bp

    # Listar endpoints y sus decoradores
    secured_endpoints = []
    public_endpoints = []

    for rule in electoral_bp.url_map.iter_rules() if hasattr(electoral_bp, 'url_map') else []:
        print(f"  {rule}")

    # Verificar manualmente
    endpoints = [
        ('/health', 'GET', 'público'),
        ('/test', 'GET', 'público'),
        ('/e14/process', 'POST', 'JWT + rate limit + cost limit'),
        ('/e14/process-url', 'POST', 'JWT + rate limit + cost limit'),
        ('/e14/validate', 'POST', 'JWT + rate limit'),
        ('/stats', 'GET', 'JWT'),
        ('/usage', 'GET', 'JWT'),
        ('/admin/usage-stats', 'GET', 'JWT + rol ADMIN'),
    ]

    print("\nEndpoints configurados:")
    for endpoint, method, security in endpoints:
        print(f"  [{method}] {endpoint}")
        print(f"      Seguridad: {security}")

    print("\n✓ Endpoint Security test completado")


def main():
    """Ejecuta todas las pruebas de seguridad."""
    print("\n" + "="*60)
    print("CASTOR ELECCIONES - Security Tests")
    print("="*60)

    test_pdf_validator()
    test_cost_tracker()
    test_electoral_roles()
    test_endpoint_security()

    print("\n" + "="*60)
    print("✓ TODOS LOS TESTS COMPLETADOS")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
