"""Render del informe HTML a PDF con WeasyPrint."""

from weasyprint import HTML


def html_to_pdf(html: str) -> bytes:
    """Convierte el HTML del informe en un PDF (bytes listos para subir/enviar)."""
    return HTML(string=html).write_pdf()
