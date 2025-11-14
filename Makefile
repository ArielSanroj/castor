# CASTOR ELECCIONES - Makefile
.PHONY: help install test run lint format clean

help:
	@echo "CASTOR ELECCIONES - Comandos disponibles:"
	@echo "  make install    - Instalar dependencias"
	@echo "  make test       - Ejecutar tests"
	@echo "  make run        - Ejecutar servidor"
	@echo "  make lint       - Ejecutar linter"
	@echo "  make format     - Formatear código"
	@echo "  make clean      - Limpiar archivos temporales"

install:
	cd backend && pip install -r requirements.txt

test:
	cd backend && pytest tests/ -v --cov=. --cov-report=html

run:
	cd backend && python main.py

lint:
	cd backend && flake8 . --max-line-length=120 --exclude=venv,__pycache__

format:
	cd backend && black . --line-length=120

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".coverage" -exec rm -r {} +
	find . -type d -name "htmlcov" -exec rm -r {} +

