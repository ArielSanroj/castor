#!/usr/bin/env python3
"""
Test E-14 OCR directamente con imagen PNG (sin conversión de PDF).
"""
import os
import sys
import json
import base64
import httpx
from pathlib import Path

# Set env vars
# API key must be set via environment variable ANTHROPIC_API_KEY

def main():
    # Usar la imagen screenshot directamente
    image_path = Path('/Users/arielsanroj/Desktop/Screenshot 2026-01-25 at 12.48.12.png')

    if not image_path.exists():
        print(f"❌ No se encontró: {image_path}")
        return

    print("=" * 60)
    print("🗳️  TEST OCR DIRECTO CON IMAGEN")
    print("=" * 60)
    print(f"📷 Imagen: {image_path.name}")

    # Leer y codificar imagen
    with open(image_path, 'rb') as f:
        img_data = f.read()
    img_base64 = base64.b64encode(img_data).decode('utf-8')

    # Prompt simple y directo
    prompt = """Analiza esta imagen de un formulario E-14 electoral colombiano.

TAREA: Lee los NÚMEROS DE VOTOS de cada candidato.

La tabla tiene candidatos listados de arriba hacia abajo.
A la DERECHA de cada candidato hay casillas con números escritos a mano.

Por favor lee CUIDADOSAMENTE cada número y responde con este formato:

NIVELACIÓN:
- Total Sufragantes E-11: [número]
- Total Votos Urna: [número]

CANDIDATOS (en orden de arriba a abajo):
1. [nombre candidato]: [votos]
2. [nombre candidato]: [votos]
3. [nombre candidato]: [votos]
... (continúa con todos)

VOTOS ESPECIALES:
- Votos en Blanco: [número]
- Votos Nulos: [número]
- Votos No Marcados: [número]

TOTAL VOTOS MESA: [número]

IMPORTANTE: Lee los números EXACTAMENTE como están escritos. Cada casilla tiene 3 dígitos (centenas, decenas, unidades)."""

    # Llamar a Claude
    headers = {
        "Content-Type": "application/json",
        "x-api-key": os.environ['ANTHROPIC_API_KEY'],
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": "claude-opus-4-20250514",
        "max_tokens": 4000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    print("\n⏳ Llamando a Claude Opus...")

    with httpx.Client(timeout=120) as client:
        response = client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return

    result = response.json()
    text = result['content'][0]['text']

    print("\n" + "=" * 60)
    print("📊 RESULTADO OCR:")
    print("=" * 60)
    print(text)
    print("=" * 60)

    # Guardar resultado
    output_path = Path('/Users/arielsanroj/Downloads/e14_image_ocr_result.txt')
    with open(output_path, 'w') as f:
        f.write(text)
    print(f"\n💾 Guardado en: {output_path}")

if __name__ == "__main__":
    main()
