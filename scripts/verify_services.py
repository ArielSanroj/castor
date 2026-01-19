#!/usr/bin/env python3
"""Verificar que los servicios se inicializan correctamente."""
import sys
from pathlib import Path

backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from config import Config
from dotenv import load_dotenv

# Load env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

print("🔍 Verificando servicios...")
print(f"   OPENAI_API_KEY: {'✅ Configurada' if Config.OPENAI_API_KEY else '❌ No configurada'}")
print(f"   OPENAI_MODEL: {Config.OPENAI_MODEL}")

try:
    from services.openai_service import OpenAIService
    svc = OpenAIService()
    print("   OpenAI Service: ✅ READY")
except Exception as e:
    print(f"   OpenAI Service: ❌ ERROR - {e}")
    sys.exit(1)

try:
    from services.twitter_service import TwitterService
    svc = TwitterService()
    print("   Twitter Service: ✅ READY")
except Exception as e:
    print(f"   Twitter Service: ⚠️  WARNING - {e}")

print("\n✅ Todos los servicios principales están listos")

