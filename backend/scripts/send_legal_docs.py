#!/usr/bin/env python3
"""
Script to send legal documents via email.
Uses local sendmail or SMTP depending on configuration.
"""
import subprocess
import sys
import os
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Documents to send
DOCUMENTS = [
    PROJECT_ROOT / "output" / "legal_documents" / "MEMORIAL_PRUEBAS_CPACA.txt",
    PROJECT_ROOT / "output" / "legal_documents" / "DEMANDA_NULIDAD_20260205_1905.txt",
    PROJECT_ROOT / "output" / "legal_documents" / "INFORME_ANOMALIAS_20260205_1905.txt",
    PROJECT_ROOT / "output" / "legal_documents" / "evidencia_anomalias.json",
]


def create_email(to_addr: str, from_addr: str = "castor@electoral.ai") -> MIMEMultipart:
    """Create MIME email with legal documents attached."""

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = f"CASTOR - Documentos Legales CPACA - Anomalias Electorales {datetime.now().strftime('%Y-%m-%d')}"

    # Email body
    body = """
Estimado/a,

Adjunto encontrará los documentos legales generados por el Sistema CASTOR de Inteligencia Electoral para el proceso de nulidad electoral.

═══════════════════════════════════════════════════════════════════════════════
                         DOCUMENTOS ADJUNTOS
═══════════════════════════════════════════════════════════════════════════════

1. MEMORIAL_PRUEBAS_CPACA.txt
   - Documento principal con evidencias conforme al CPACA
   - 647 anomalías documentadas
   - 50,024 votos en disputa
   - Clasificación por artículos 223-226

2. DEMANDA_NULIDAD_20260205_1905.txt
   - Borrador de demanda de nulidad electoral
   - Formato Consejo de Estado, Sección Quinta
   - Hechos, pretensiones y fundamentos de derecho

3. INFORME_ANOMALIAS_20260205_1905.txt
   - Informe técnico detallado de anomalías
   - Métricas y estadísticas por tipo
   - Distribución geográfica

4. evidencia_anomalias.json
   - Datos estructurados de todas las anomalías
   - Formato JSON para análisis computacional
   - Incluye coordenadas de cada mesa afectada

═══════════════════════════════════════════════════════════════════════════════
                         RESUMEN EJECUTIVO
═══════════════════════════════════════════════════════════════════════════════

• Formularios E-14 analizados: 418
• Total anomalías detectadas: 647
• Anomalías CRÍTICAS: 40
• Anomalías ALTAS: 226
• Mesas afectadas: 399
• Votos en disputa: 50,024

TIPOS DE ANOMALÍAS:
• OCR_LOW_CONFIDENCE: 383 casos (Art. 223)
• IMPOSSIBLE_VALUE: 191 casos (Art. 224)
• ARITHMETIC_MISMATCH: 64 casos (Art. 225)
• GEOGRAPHIC_CLUSTER: 9 casos (Art. 223)

HALLAZGO CRÍTICO:
Mesa CAM-MAGDALENA-CHIVOLO-99-50-001 presenta discrepancia de 2,222 votos
(Esperado: 8,587 | Reportado: 10,809)

═══════════════════════════════════════════════════════════════════════════════
                         INFORMACIÓN LEGAL
═══════════════════════════════════════════════════════════════════════════════

Marco Legal Aplicable:
- Código de Procedimiento Administrativo y de lo Contencioso Administrativo (CPACA)
- Ley 1437 de 2011, Artículos 223-226

Plazos:
- Art. 223: 48 horas desde escrutinio
- Art. 225 (Reconteo): 5 días desde declaratoria
- Nulidad: 30 días desde declaratoria

ADVERTENCIA:
Estos documentos son generados automáticamente como apoyo probatorio y deben
ser revisados por un abogado calificado antes de su presentación formal.

═══════════════════════════════════════════════════════════════════════════════

Sistema CASTOR - Inteligencia Electoral v1.0
Generado: {datetime}

═══════════════════════════════════════════════════════════════════════════════
""".format(datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # Attach documents
    for doc_path in DOCUMENTS:
        if not doc_path.exists():
            print(f"⚠ Document not found: {doc_path}")
            continue

        with open(doc_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())

        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{doc_path.name}"'
        )
        msg.attach(part)
        print(f"✓ Attached: {doc_path.name} ({doc_path.stat().st_size:,} bytes)")

    return msg


def send_via_sendmail(to_addr: str) -> bool:
    """Send email using local sendmail."""
    try:
        msg = create_email(to_addr)

        # Use sendmail
        process = subprocess.Popen(
            ['/usr/sbin/sendmail', '-t', '-oi'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = process.communicate(msg.as_bytes())

        if process.returncode == 0:
            print(f"\n✓ Email sent successfully to: {to_addr}")
            return True
        else:
            print(f"\n✗ Sendmail failed: {stderr.decode()}")
            return False

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def send_via_smtp(to_addr: str, smtp_host: str = None, smtp_port: int = 587,
                  username: str = None, password: str = None) -> bool:
    """Send email via SMTP."""
    import smtplib

    smtp_host = smtp_host or os.getenv('SMTP_HOST', 'smtp.gmail.com')
    username = username or os.getenv('SMTP_USERNAME') or os.getenv('EMAIL_USERNAME')
    password = password or os.getenv('SMTP_PASSWORD') or os.getenv('EMAIL_PASSWORD')

    if not username or not password:
        print("✗ SMTP credentials not configured")
        print("\nTo configure:")
        print("  export SMTP_USERNAME=your-email@gmail.com")
        print("  export SMTP_PASSWORD=your-app-password")
        return False

    try:
        msg = create_email(to_addr, from_addr=username)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(username, [to_addr], msg.as_string())

        print(f"\n✓ Email sent via SMTP to: {to_addr}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("✗ SMTP authentication failed")
        print("\nFor Gmail, use an App Password:")
        print("  https://support.google.com/accounts/answer/185833")
        return False
    except Exception as e:
        print(f"\n✗ SMTP error: {e}")
        return False


def main():
    """Main entry point."""
    to_addr = "ariel@cliocircle.com"

    print("═" * 70)
    print("       CASTOR - Envío de Documentos Legales Electorales")
    print("═" * 70)
    print(f"\nDestinatario: {to_addr}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nPreparando documentos...")
    print("-" * 70)

    # Try SMTP first if configured
    smtp_username = os.getenv('SMTP_USERNAME') or os.getenv('EMAIL_USERNAME')
    if smtp_username:
        print("\n📧 Usando SMTP...")
        success = send_via_smtp(to_addr)
    else:
        print("\n📧 Usando sendmail local...")
        success = send_via_sendmail(to_addr)

    print("-" * 70)

    if success:
        print("\n✓ DOCUMENTOS ENVIADOS EXITOSAMENTE")
        print(f"  Destinatario: {to_addr}")
        print("  Verificar bandeja de entrada y spam")
    else:
        print("\n⚠ ENVÍO ALTERNATIVO REQUERIDO")
        print("\nOpciones:")
        print("1. Configurar SMTP:")
        print("   export SMTP_USERNAME=your-email@gmail.com")
        print("   export SMTP_PASSWORD=your-app-password")
        print("   python send_legal_docs.py")
        print("\n2. Los documentos están en:")
        for doc in DOCUMENTS:
            if doc.exists():
                print(f"   {doc}")

    print("\n" + "═" * 70)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
