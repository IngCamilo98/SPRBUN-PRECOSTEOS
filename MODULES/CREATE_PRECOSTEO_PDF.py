# MODULES/CREATE_PRECOSTEO_PDF.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from fpdf import FPDF


@dataclass(frozen=True)
class PDFLayoutConfig:
    # Página
    orientation: str = "P"
    unit: str = "mm"
    format: str = "Letter"  # tamaño carta

    # Márgenes (mm)
    top_margin: float = 35.0
    left_margin: float = 15.0
    right_margin: float = 15.0
    footer_margin: float = 25.0

    # Espacios visuales (mm)
    header_lift_after: float = 30.0
    footer_height: float = 20.0 

    # Plantillas
    templates_dirname: str = "TEMPLATES"
    header_filename: str = "header.png"
    footer_filename: str = "footer.png"

    # Salida
    output_dirname: str = "BD/PRECOSTEOS"
    output_prefix: str = "PRECOSTEO"

    # Tipografía por defecto
    default_font_family: str = "Helvetica"
    default_font_size: int = 12
    default_line_height: float = 6.0

    # Footer (ajuste fino visual)
    footer_height: float = 12.0          # más pequeño
    footer_width_ratio: float = 0.50     # 50% del ancho de la página
    footer_bottom_margin: float = 7.0   # separación del borde inferior (mm)
    footer_margin: float = 28.0          # margen de seguridad para el contenido




class CreatePrecostoPDF(FPDF):
    """
    PDF base para precosteos AMC / SPRBUN:
    - Tamaño carta
    - Header y Footer automáticos (TEMPLATES/)
    - Configuración encapsulada (main limpio)
    """

    def __init__(self, config: PDFLayoutConfig | None = None):
        self.config = config or PDFLayoutConfig()

        super().__init__(
            orientation=self.config.orientation,
            unit=self.config.unit,
            format=self.config.format,
        )

        self._project_root = self._resolve_project_root()
        self._templates_dir = self._project_root / self.config.templates_dirname
        self._output_dir = self._project_root / self.config.output_dirname

        self.header_img = self._templates_dir / self.config.header_filename
        self.footer_img = self._templates_dir / self.config.footer_filename

        if not self.header_img.exists():
            raise FileNotFoundError(f"No se encontró header: {self.header_img}")
        if not self.footer_img.exists():
            raise FileNotFoundError(f"No se encontró footer: {self.footer_img}")

        # Layout
        self.set_margins(
            left=self.config.left_margin,
            top=self.config.top_margin,
            right=self.config.right_margin,
        )
        self.set_auto_page_break(auto=True, margin=self.config.footer_margin)

    @staticmethod
    def _resolve_project_root() -> Path:
        return Path(__file__).resolve().parents[1]

    # ─────────────── Header / Footer automáticos ───────────────
    def header(self):
        page_width = self.w
        self.image(str(self.header_img), x=0, y=0, w=page_width)
        self.ln(self.config.header_lift_after)

    def footer(self):
        page_width = self.w
        page_height = self.h

        # Ancho del footer (centrado)
        footer_width = page_width * self.config.footer_width_ratio
        x = (page_width - footer_width) / 2

        # Posición vertical: separado del borde inferior
        y = page_height - self.config.footer_bottom_margin - self.config.footer_height

        self.image(
            str(self.footer_img),
            x=x,
            y=y,
            w=footer_width
        )

    # ─────────────── Helpers internos ───────────────
    def new_page(self) -> None:
        self.add_page()

    def set_default_typography(self) -> None:
        """Define tipografía por defecto (sin que main toque fonts)."""
        self.set_font(self.config.default_font_family, size=self.config.default_font_size)

    def write_paragraph(self, text: str) -> None:
        """Escritura estándar de párrafos."""
        self.set_default_typography()
        self.multi_cell(0, self.config.default_line_height, text)

    def render_demo(self) -> None:
        """
        Demo interna: crea 1-2 páginas con texto de prueba.
        Útil para validar header/footer y márgenes.
        """
        self.new_page()
        self.write_paragraph("Prueba: PDF con header/footer automáticos desde TEMPLATES.")

    def default_output_path(self, cod_prec: str | None = None) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        code_part = (cod_prec or self.config.output_prefix).replace(" ", "_")
        filename = f"{self.config.output_prefix}_{code_part}_{date_str}.pdf"
        return self._output_dir / filename

    def save(self, path: Path | None = None, cod_prec: str | None = None) -> Path:
        out_path = path or self.default_output_path(cod_prec=cod_prec)
        self.output(str(out_path))
        return out_path
