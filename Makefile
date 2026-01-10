# CASTOR ELECCIONES - Makefile
.PHONY: help install install-dev test test-cov run run-prod lint format check security clean db-init pre-commit

# Default target
.DEFAULT_GOAL := help

help:
	@echo "CASTOR ELECCIONES - Comandos disponibles:"
	@echo ""
	@echo "  Setup:"
	@echo "    make install      - Instalar dependencias de produccion"
	@echo "    make install-dev  - Instalar dependencias de desarrollo"
	@echo "    make pre-commit   - Instalar hooks de pre-commit"
	@echo ""
	@echo "  Development:"
	@echo "    make run          - Ejecutar servidor de desarrollo"
	@echo "    make run-prod     - Ejecutar con gunicorn (produccion)"
	@echo "    make db-init      - Inicializar base de datos"
	@echo ""
	@echo "  Testing:"
	@echo "    make test         - Ejecutar tests"
	@echo "    make test-cov     - Ejecutar tests con cobertura"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make lint         - Ejecutar linter (flake8)"
	@echo "    make format       - Formatear codigo (black + isort)"
	@echo "    make check        - Verificar formato sin cambiar"
	@echo "    make security     - Ejecutar checks de seguridad"
	@echo ""
	@echo "  Cleanup:"
	@echo "    make clean        - Limpiar archivos temporales"

# Installation
install:
	pip install -r backend/requirements.txt

install-dev:
	pip install -r backend/requirements.txt
	pip install pre-commit
	pre-commit install

pre-commit:
	pip install pre-commit
	pre-commit install
	@echo "Pre-commit hooks instalados"

# Database
db-init:
	cd backend && python -c "from services.database_service import DatabaseService; db = DatabaseService(); db.init_db(); print('Database initialized')"

# Running
run:
	cd backend && python run.py

run-prod:
	cd backend && gunicorn -w 4 -b 0.0.0.0:5001 "app:create_app('production')"

# Testing
test:
	cd backend && pytest tests/ -v

test-cov:
	cd backend && pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing
	@echo "Coverage report generado en backend/htmlcov/index.html"

# Code Quality
lint:
	cd backend && flake8 . --max-line-length=100 --ignore=E501,W503 --exclude=venv,__pycache__,migrations

format:
	cd backend && black . --line-length=100
	cd backend && isort . --profile black --line-length=100
	@echo "Codigo formateado"

check:
	cd backend && black --check . --line-length=100
	cd backend && isort --check-only --profile black . --line-length=100
	@echo "Formato OK"

security:
	cd backend && bandit -r . -x ./tests/ --skip B101
	@echo "Security check completado"

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.bak" -delete 2>/dev/null || true
	find . -type f -name "*.deprecated.bak" -delete 2>/dev/null || true
	@echo "Limpieza completada"

# Docker (for future use)
docker-build:
	docker build -t castor-elecciones .

docker-run:
	docker run -p 5001:5001 --env-file .env castor-elecciones
