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
    top_margin: float = 22.0
    left_margin: float = 15.0
    right_margin: float = 15.0

    # Espacios visuales (mm)
    header_lift_after: float = 12.0

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
    footer_height: float = 12.0
    footer_width_ratio: float = 0.50
    footer_bottom_margin: float = 7.0
    footer_margin: float = 28.0  # margen de seguridad para el contenido


class CreatePrecostoPDF(FPDF):
    """
    PDF base para precosteos AMC / SPRBUN:
    - Tamaño carta
    - Header y Footer automáticos (TEMPLATES/)
    - Render del contenido tipo carta (como tu imagen)
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

        # Para recibir bd (sin usarlo aún)
        self._bd = None

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

        footer_width = page_width * self.config.footer_width_ratio
        x = (page_width - footer_width) / 2
        y = page_height - self.config.footer_bottom_margin - self.config.footer_height

        self.image(str(self.footer_img), x=x, y=y, w=footer_width)

    # ─────────────── Helpers internos ───────────────
    def new_page(self) -> None:
        self.add_page()

    def set_default_typography(self, size: int | None = None, bold: bool = False) -> None:
        fam = self.config.default_font_family
        style = "B" if bold else ""
        self.set_font(fam, style=style, size=size or self.config.default_font_size)

    @staticmethod
    def _fecha_es(dt: datetime) -> str:
        meses = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
            5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
            9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }
        return f"{dt.day} de {meses[dt.month]} de {dt.year}"

    @staticmethod
    def _infer_lugares_text(df_lugares) -> str:
        """
        Intenta armar el texto de 'Lugar de ejecución' desde un dataframe.
        - Prioriza columnas típicas
        - Si no encuentra, usa la primera columna
        """
        try:
            cols = [c.strip() for c in df_lugares.columns]
        except Exception:
            return ""

        preferidas = [
            "LUGAR_EJECUCION", "LUGAR", "LUGAR DE EJECUCIÓN", "LUGAR DE EJECUCION",
            "UBICACION", "UBICACIÓN", "DESCRIPCION_LUGAR", "DESCRIPCIÓN"
        ]

        col = None
        upper_map = {c.upper(): c for c in cols}
        for p in preferidas:
            if p.upper() in upper_map:
                col = upper_map[p.upper()]
                break

        if col is None:
            col = cols[0] if cols else None

        if not col:
            return ""

        # únicos, limpios, en orden de aparición
        seen = set()
        items = []
        for v in df_lugares[col].tolist():
            s = str(v).strip()
            if not s or s.lower() == "nan":
                continue
            key = s.lower()
            if key not in seen:
                seen.add(key)
                items.append(s)

        return ", ".join(items)

    def _write_spaced(self, mm: float) -> None:
        self.ln(mm)

    def render_precosteo(
        self,
        codigo_precosteo: str,
        resumen: str,
        df_lugares,
        bd=None,
    ) -> None:
        """
        Construye el contenido del PDF como tu imagen:
        - Código arriba a la derecha (debajo del header)
        - 'Santiago de Cali, <fecha dinámica>'
        - Bloque de destinatario fijo
        - Párrafo resumen
        - 'Lugar de ejecución:' desde df_lugares
        - Recibe 'bd' (se guarda para usar luego)
        """
        self._bd = bd

        self.new_page()

        # 1) Código (alineado a la derecha)
        self.set_default_typography(size=12, bold=True)
        self.cell(0, 6, codigo_precosteo, ln=1, align="R")

        # 2) Ciudad + fecha dinámica (ciudad fija)
        self._write_spaced(2)
        self.set_default_typography(size=12, bold=True)
        fecha = self._fecha_es(datetime.now())
        self.cell(0, 6, f"Santiago de Cali, {fecha}", ln=1, align="L")

        # 3) Señores + razón social fija
        self._write_spaced(12)
        self.set_default_typography(size=12, bold=True)
        self.cell(0, 6, "Señores:", ln=1, align="L")

        self._write_spaced(10)
        self.set_default_typography(size=12, bold=True)
        self.multi_cell(0, 6, "SOCIEDAD PORTUARIA REGIONAL DE BUENAVENTURA", align="L")

        # 4) Resumen (párrafo)
        self._write_spaced(6)
        self.set_default_typography(size=11, bold=False)
        self.multi_cell(0, 6, resumen.strip(), align="J")

        # 5) Lugar de ejecución desde df_lugares
        lugares_txt = self._infer_lugares_text(df_lugares)
        if lugares_txt:
            self._write_spaced(8)
            self.set_default_typography(size=11, bold=True)
            # etiqueta en negrilla + texto normal (simulando la foto)
            self.cell(self.get_string_width("Lugar de ejecución:") + 1, 6, "Lugar de ejecución:", ln=0)
            self.set_default_typography(size=11, bold=False)
            self.multi_cell(0, 6, f" {lugares_txt}", align="L")

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
