"""
Email Service for CASTOR ELECCIONES.
Handles sending legal documents and notifications via email.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails with attachments."""

    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        username: str = None,
        password: str = None,
        use_tls: bool = True
    ):
        """
        Initialize email service.

        Falls back to environment variables if not provided.
        """
        self.smtp_host = smtp_host or os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.username = username or os.getenv('SMTP_USERNAME', os.getenv('EMAIL_USERNAME'))
        self.password = password or os.getenv('SMTP_PASSWORD', os.getenv('EMAIL_PASSWORD'))
        self.use_tls = use_tls
        self.default_from = os.getenv('EMAIL_FROM', self.username)

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        from_addr: str = None,
        cc: Optional[List[str]] = None,
        html_body: str = None
    ) -> bool:
        """
        Send an email with optional attachments.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text body
            attachments: List of file paths to attach
            from_addr: Sender address (defaults to configured)
            cc: List of CC recipients
            html_body: Optional HTML version of body

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.username or not self.password:
            logger.error("Email credentials not configured. Set SMTP_USERNAME and SMTP_PASSWORD.")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative') if html_body else MIMEMultipart()
            msg['From'] = from_addr or self.default_from
            msg['To'] = to
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Add body
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            if html_body:
                msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            # Add attachments
            if attachments:
                for file_path in attachments:
                    path = Path(file_path)
                    if not path.exists():
                        logger.warning(f"Attachment not found: {file_path}")
                        continue

                    with open(path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())

                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{path.name}"'
                    )
                    msg.attach(part)
                    logger.info(f"Attached: {path.name}")

            # Send
            recipients = [to]
            if cc:
                recipients.extend(cc)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(
                    from_addr or self.default_from,
                    recipients,
                    msg.as_string()
                )

            logger.info(f"Email sent successfully to {to}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def send_legal_documents(
        self,
        to: str,
        document_paths: List[str],
        case_summary: str = None
    ) -> bool:
        """
        Send legal documents for electoral litigation.

        Args:
            to: Recipient email address
            document_paths: List of document file paths
            case_summary: Optional summary of the case

        Returns:
            True if sent successfully
        """
        subject = "CASTOR - Documentos Legales Electorales (CPACA)"

        body = """
Estimado/a,

Adjunto encontrará los documentos legales generados por el Sistema CASTOR de Inteligencia Electoral.

DOCUMENTOS ADJUNTOS:
"""
        for path in document_paths:
            filename = Path(path).name
            body += f"• {filename}\n"

        body += """
RESUMEN DEL CASO:
"""
        if case_summary:
            body += case_summary
        else:
            body += """
- Análisis de formularios E-14 con anomalías detectadas
- Clasificación según artículos CPACA (223-226)
- Evidencia documentada para proceso de nulidad electoral
"""

        body += """

IMPORTANTE:
- Estos documentos son generados automáticamente como apoyo probatorio
- Deben ser revisados por un abogado antes de presentación oficial
- Los plazos legales CPACA deben ser verificados según fecha de elección

Sistema CASTOR - Inteligencia Electoral
https://castor.cliocircle.com
"""

        return self.send_email(
            to=to,
            subject=subject,
            body=body,
            attachments=document_paths
        )


def send_legal_documents_cli():
    """Command-line interface for sending legal documents."""
    import argparse

    parser = argparse.ArgumentParser(description='Send legal documents via email')
    parser.add_argument('--to', required=True, help='Recipient email')
    parser.add_argument('--files', nargs='+', required=True, help='Files to attach')
    parser.add_argument('--subject', default='CASTOR - Legal Documents', help='Email subject')

    args = parser.parse_args()

    service = EmailService()
    success = service.send_legal_documents(
        to=args.to,
        document_paths=args.files
    )

    if success:
        print(f"✓ Documents sent to {args.to}")
    else:
        print("✗ Failed to send documents. Check credentials.")
        print("\nTo configure email:")
        print("  export SMTP_USERNAME=your-email@gmail.com")
        print("  export SMTP_PASSWORD=your-app-password")


if __name__ == '__main__':
    send_legal_documents_cli()
