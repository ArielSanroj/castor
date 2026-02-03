#!/usr/bin/env python3
"""
Test E-14 OCR con análisis detallado de cada dígito.
"""
import os
import base64
import httpx
from pathlib import Path

# API key must be set via environment variable ANTHROPIC_API_KEY

def main():
    image_path = Path('/Users/arielsanroj/Desktop/Screenshot 2026-01-25 at 12.48.12.png')

    with open(image_path, 'rb') as f:
        img_base64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = """Analiza esta imagen de un formulario E-14 electoral colombiano.

ENFÓCATE en la columna "VOTACIÓN" que está a la DERECHA de cada candidato.
Cada celda de votación tiene 3 casillas pequeñas para escribir un número de 3 dígitos.

Por favor, para CADA CANDIDATO, describe:
1. El nombre del candidato
2. Los 3 dígitos que ves en su casilla de votación (describe cada dígito individualmente)
3. El número total calculado

Ejemplo de formato:
- CANDIDATO X: Dígito1=[describe], Dígito2=[describe], Dígito3=[describe] → Total=[número]

Analiza especialmente:
- RODOLFO HERNÁNDEZ (primer candidato): ¿Qué dígitos exactos ves?
- GUSTAVO PETRO: ¿Qué dígitos exactos ves?

Sé MUY ESPECÍFICO sobre cada dígito que observas."""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": os.environ['ANTHROPIC_API_KEY'],
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": "claude-opus-4-20250514",
        "max_tokens": 4000,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_base64}},
                {"type": "text", "text": prompt}
            ]
        }]
    }

    print("⏳ Analizando dígitos en detalle...")

    with httpx.Client(timeout=120) as client:
        response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
            return

    result = response.json()
    print("\n" + "=" * 60)
    print("📊 ANÁLISIS DETALLADO DE DÍGITOS:")
    print("=" * 60)
    print(result['content'][0]['text'])

if __name__ == "__main__":
    main()
