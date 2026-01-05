from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Tuple

from fpdf import FPDF


@dataclass(frozen=True)
class PDFLayoutConfig:
    # Página
    orientation: str = "P"
    unit: str = "mm"
    format: str = "Letter"

    # Márgenes (mm)
    top_margin: float = 24.0
    left_margin: float = 15.0
    right_margin: float = 15.0

    # Espacios visuales (mm)
    header_lift_after: float = 12.0

    # Plantillas
    templates_dirname: str = "TEMPLATES"
    header_filename: str = "header.png"
    footer_filename: str = "footer.png"

    signature_filename: str = "firma.png"
    signature_width_ratio: float = 0.60   # ajusta (0.55–0.70 suele quedar bien)
    signature_gap_before: float = 10.0     # espacio (mm) después de la tabla

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
    - Contenido tipo carta + tabla de actividades desde dataframe BD
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

        self.signature_img = self._templates_dir / self.config.signature_filename
        if not self.signature_img.exists():
            raise FileNotFoundError(f"No se encontró firma: {self.signature_img}")

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

        self._bd = None  # se guarda por si luego lo usas en otras secciones

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

    # ─────────────── Tipografía / helpers ───────────────
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
    def _money_cop(value) -> str:
        """Formatea en estilo COP: 60.000,00"""
        try:
            v = float(value)
        except Exception:
            return str(value)
        # miles con punto y decimales con coma
        s = f"{v:,.2f}"            # 60,000.00
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # 60.000,00
        return s
    
    def _nb_lines(self, w: float, txt: str, line_h: float) -> int:
        """
        Calcula cuántas líneas usará multi_cell() para un texto dado
        con el ancho 'w' y altura de línea 'line_h', usando el ancho real
        de la fuente actual (get_string_width).
        """
        if txt is None:
            return 1
        s = str(txt).replace("\r", "")
        if not s:
            return 1

        # Maneja saltos de línea explícitos
        parts = s.split("\n")
        total = 0
        for part in parts:
            if part == "":
                total += 1
                continue

            words = part.split(" ")
            line = ""
            lines = 1
            for wd in words:
                test = (line + " " + wd).strip()
                if self.get_string_width(test) <= (w - 2):  # 2mm de margen de seguridad
                    line = test
                else:
                    lines += 1
                    line = wd
            total += lines
        return max(1, total)

    @staticmethod
    def _safe_upper(s: str) -> str:
        return (s or "").strip().upper()

    # ─────────────── Lugares ───────────────
    @staticmethod
    def _infer_lugares_text(df_lugares) -> str:
        try:
            cols = list(df_lugares.columns)
        except Exception:
            return ""

        preferidas = [
            "LUGAR_EJECUCION", "LUGAR", "LUGAR DE EJECUCIÓN", "LUGAR DE EJECUCION",
            "UBICACION", "UBICACIÓN", "DESCRIPCION_LUGAR", "DESCRIPCIÓN", "DESCRIPCION"
        ]

        col = None
        upper_map = {str(c).strip().upper(): c for c in cols}
        for p in preferidas:
            if p.upper() in upper_map:
                col = upper_map[p.upper()]
                break
        if col is None and cols:
            col = cols[0]
        if col is None:
            return ""

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

    # ─────────────── Fechas / filtro BD ───────────────
    @staticmethod
    def _to_date(x) -> Optional[date]:
        """Convierte a date; acepta datetime/date/strings comunes (dd/mm/yyyy, yyyy-mm-dd, etc.)."""
        if x is None:
            return None
        if isinstance(x, datetime):
            return x.date()
        if isinstance(x, date):
            return x
        s = str(x).strip()
        if not s or s.lower() == "nan":
            return None

        # intentos típicos
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass

        # último intento: solo números separados
        try:
            parts = [p for p in s.replace(".", "/").replace("-", "/").split("/") if p]
            if len(parts) == 3:
                a, b, c = parts
                # heurística dayfirst
                if len(c) == 4:
                    # a/b/c
                    da = int(a); db = int(b); dc = int(c)
                    # si a > 12 => dayfirst
                    if da > 12:
                        return date(dc, db, da)
                    # si b > 12 => monthfirst
                    if db > 12:
                        return date(dc, da, db)
                    # por defecto dayfirst
                    return date(dc, db, da)
        except Exception:
            return None

        return None

    @staticmethod
    def _detect_date_columns(df) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Devuelve (col_fecha_unica, col_inicio, col_fin)
        - Si existe una sola columna fecha -> col_fecha_unica
        - Si existe par inicio/fin -> col_inicio y col_fin
        """
        cols = [str(c).strip() for c in df.columns]
        U = {c.upper(): c for c in cols}

        # candidatos
        fecha_unica = None
        inicio = None
        fin = None

        # una sola fecha
        for key in ["FECHA", "FECHA_ACTIVIDAD", "FECHA_EJECUCION", "FECHA EJECUCION", "DATE"]:
            if key in U:
                fecha_unica = U[key]
                break

        # rango
        for key in ["FECHA_INICIO", "INICIO", "FECHA INICIO", "START", "DESDE"]:
            if key in U:
                inicio = U[key]
                break

        for key in ["FECHA_FIN", "FIN", "FECHA FIN", "END", "HASTA"]:
            if key in U:
                fin = U[key]
                break

        # Si hay rango, priorizar rango
        if inicio and fin:
            return (None, inicio, fin)

        return (fecha_unica, None, None)

    def filter_bd_by_range(self, bd_df, fecha_inicio, fecha_fin):
        """
        Filtra el dataframe BD por fechas:
        - Si existe columna FECHA: inicio <= FECHA <= fin
        - Si existe INICIO/FIN en BD: intersección de rangos con [inicio, fin]
        - Si no hay columnas fecha detectables: retorna BD completo
        """
        if bd_df is None:
            return None

        ini = self._to_date(fecha_inicio)
        fin = self._to_date(fecha_fin)
        if ini is None or fin is None:
            return bd_df

        col_fecha, col_ini, col_fin = self._detect_date_columns(bd_df)

        # Copia liviana
        df = bd_df.copy()

        if col_fecha:
            df["_FECHA_"] = df[col_fecha].apply(self._to_date)
            df = df[df["_FECHA_"].notna()]
            df = df[(df["_FECHA_"] >= ini) & (df["_FECHA_"] <= fin)]
            df = df.drop(columns=["_FECHA_"], errors="ignore")
            return df

        if col_ini and col_fin:
            df["_INI_"] = df[col_ini].apply(self._to_date)
            df["_FIN_"] = df[col_fin].apply(self._to_date)
            df = df[df["_INI_"].notna() & df["_FIN_"].notna()]
            # intersección: (ini <= FIN_BD) y (fin >= INI_BD)
            df = df[(ini <= df["_FIN_"]) & (fin >= df["_INI_"])]
            df = df.drop(columns=["_INI_", "_FIN_"], errors="ignore")
            return df

        return df

    # ─────────────── Tabla ───────────────
    @staticmethod
    def _detect_table_columns(df) -> dict:
        cols = [str(c).strip() for c in df.columns]
        U = {c.upper(): c for c in cols}

        def pick(*candidates):
            for k in candidates:
                kk = k.upper()
                if kk in U:
                    return U[kk]
            return None

        return {
            "item": pick("ID_ITEM", "ID ÍTEM", "ID_ITEM ", "ITEM", "ÍTEM", "COD_ITEM"),
            "descripcion": pick("ACTIVIDAD", "DESCRIPCION", "DESCRIPCIÓN", "DESCRIPCION_ACTIVIDAD"),
            "unidad": pick("UNIDAD_MEDIDA", "UNIDAD", "UND"),
            "cantidad": pick("CANTIDAD", "CANT"),
            "v_unit": pick("VALOR_UNITARIO", "VR_UNITARIO", "VLR_UNITARIO", "PRECIO_UNITARIO"),
            "v_total": pick("VALOR_TOTAL", "VR_TOTAL", "VLR_TOTAL", "TOTAL"),
        }

    def _write_section_table(
        self,
        lugar_titulo: str,
        codigo_precosteo: str,
        bd_filtrado,
    ) -> None:
        """
        Dibuja la sección de tabla como la imagen.
        - Repite encabezado (franjas + header columnas) en cada página.
        - Salto de página manual por fila (evita páginas cortadas).
        - Total corregido (no se desborda).
        """
        if bd_filtrado is None or len(bd_filtrado) == 0:
            return

        # Título
        self.ln(8)
        self.set_default_typography(size=12, bold=True)
        self.cell(0, 7, "ACTIVIDADES APLICABLES SEGÚN CONTRATO", ln=1, align="L")

        # Dimensiones
        usable_w = self.w - self.l_margin - self.r_margin

        # Columnas (ajústalas si quieres)
        w_item = 12
        w_desc = 78
        w_und = 16
        w_cant = 20
        w_vu = 34
        w_vt = usable_w - (w_item + w_desc + w_und + w_cant + w_vu)

        headers = [
            ("Ítem", w_item),
            ("Descripción", w_desc),
            ("Unidad", w_und),
            ("Cantidad", w_cant),
            ("Valor Unitario", w_vu),
            ("Valor Total", w_vt),
        ]

        # Encabezado repetible (franjas + header columnas)
        def _draw_table_header():
            # Bordes visibles
            self.set_draw_color(0, 0, 0)
            self.set_line_width(0.4)
            self.set_text_color(0, 0, 0)

            # Franja amarilla (lugar)
            self.set_fill_color(255, 192, 0)
            self.set_default_typography(size=11, bold=True)
            self.cell(usable_w, 8, self._safe_upper(lugar_titulo), ln=1, align="C", fill=True, border=1)

            # Franja azul (código)
            self.set_fill_color(0, 176, 240)
            self.set_default_typography(size=11, bold=True)
            self.cell(usable_w, 8, codigo_precosteo, ln=1, align="C", fill=True, border=1)

            # Header tabla
            self.set_fill_color(189, 215, 238)
            self.set_default_typography(size=10, bold=True)
            for text, ww in headers:
                self.cell(ww, 8, text, border=1, align="C", fill=True)
            self.ln(8)

            # Fuente para filas
            self.set_default_typography(size=10, bold=False)

        # Dibujar encabezado inicial
        _draw_table_header()

        # Detectar columnas del df
        colmap = self._detect_table_columns(bd_filtrado)

        # Render filas
        total_general = 0.0

        # Parámetros consistentes
        line_h = 5.5
        pad = 1

        # Desactivar auto page break durante la tabla (lo manejamos manual)
        old_apb = self.auto_page_break
        old_bm = self.b_margin
        self.set_auto_page_break(auto=False, margin=self.b_margin)

        try:
            for _, row in bd_filtrado.iterrows():
                item = str(row[colmap["item"]]).strip() if colmap["item"] else ""
                desc = str(row[colmap["descripcion"]]).strip() if colmap["descripcion"] else ""
                und  = str(row[colmap["unidad"]]).strip() if colmap["unidad"] else ""
                cant = row[colmap["cantidad"]] if colmap["cantidad"] else ""
                vunit = row[colmap["v_unit"]] if colmap["v_unit"] else ""
                vtotal = row[colmap["v_total"]] if colmap["v_total"] else ""

                # Total general (robusto)
                try:
                    if hasattr(self, "_parse_number"):
                        total_general += float(self._parse_number(vtotal))
                    else:
                        total_general += float(vtotal)
                except Exception:
                    pass

                # Calcular altura real de la fila según descripción
                self.set_default_typography(size=10, bold=False)  # importante antes de medir
                lines = self._nb_lines(w_desc - 2 * pad, desc, line_h)
                row_h = (line_h * lines) + (2 * pad)

                # --- salto de página MANUAL antes de dibujar la fila ---
                bottom_limit = self.h - self.b_margin
                if self.get_y() + row_h > bottom_limit:
                    self.add_page()
                    _draw_table_header()

                x = self.l_margin
                y = self.get_y()

                # 1) Ítem
                self.set_xy(x, y)
                self.cell(w_item, row_h, item, border=1, align="C")

                # 2) Descripción (rect + multi_cell con padding)
                self.set_xy(x + w_item, y)
                self.rect(x + w_item, y, w_desc, row_h)  # borde exacto
                self.set_xy(x + w_item + pad, y + pad)
                self.multi_cell(w_desc - 2 * pad, line_h, desc, border=0, align="L")

                # 3) Unidad
                self.set_xy(x + w_item + w_desc, y)
                self.cell(w_und, row_h, und, border=1, align="C")

                # 4) Cantidad
                self.set_xy(x + w_item + w_desc + w_und, y)
                self.cell(w_cant, row_h, str(cant), border=1, align="C")

                # 5) Valor Unitario
                self.set_xy(x + w_item + w_desc + w_und + w_cant, y)
                self.cell(w_vu, row_h, f"$  {self._money_cop(vunit)}", border=1, align="R")

                # 6) Valor Total
                self.set_xy(x + w_item + w_desc + w_und + w_cant + w_vu, y)
                self.cell(w_vt, row_h, f"$  {self._money_cop(vtotal)}", border=1, align="R")

                # Bajar al final de la fila
                self.set_y(y + row_h)

            # --- Antes de imprimir TOTAL, verificar espacio ---
            total_h = 8
            bottom_limit = self.h - self.b_margin
            if self.get_y() + total_h > bottom_limit:
                self.add_page()
                _draw_table_header()

            # Fila Total (verde) — CORREGIDA (no se desborda)
            self.set_fill_color(146, 208, 80)
            self.set_default_typography(size=10, bold=True)

            # Vacío hasta Cantidad
            self.cell(w_item + w_desc + w_und + w_cant, 8, "", border=1, fill=False)

            # "Total" en la columna Valor Unitario
            self.cell(w_vu, 8, "Total", border=1, align="C", fill=True)

            # Valor del total en la columna Valor Total (solo w_vt)
            self.set_default_typography(size=9, bold=True)  # baja un poco la fuente para números grandes
            self.cell(w_vt, 8, f"$  {self._money_cop(total_general)}", border=1, align="R", fill=True)

            # Volver a fuente normal
            self.set_default_typography(size=10, bold=False)
            self.ln(8)

        finally:
            # Restaurar auto page break
            self.set_auto_page_break(auto=old_apb, margin=old_bm)

        # Reset colores
        self.set_text_color(0, 0, 0)


    def _write_precosteo_status_and_signature(self, estado: str = "EN APROBACIÓN") -> None:
        """
        Dibuja:
        - ESTADO PRECOSTEO: ● EN APROBACIÓN
        - Cordialmente,
        - firma.png centrada (como tu ejemplo)
        """
        # Espacio después de la tabla
        self.ln(self.config.signature_gap_before)

      
        # 3) Firma (imagen)
        page_width = self.w
        usable_w = page_width - self.l_margin - self.r_margin
        sig_w = usable_w * self.config.signature_width_ratio
        x_img = self.l_margin  # alineada al margen izquierdo, como tu ejemplo
        # si la quieres centrada: x_img = self.l_margin + (usable_w - sig_w) / 2

        # Si no cabe, saltar de página antes de ponerla (para no chocar con footer)
        # Estimación de alto: en fpdf no sabemos el alto exacto sin leer imagen,
        # así que dejamos un margen razonable.
        needed_space = 55  # mm aprox para firma + texto (ajusta si tu firma es más alta)
        if self.get_y() + needed_space > (self.h - self.b_margin):
            self.add_page()

        self.image(str(self.signature_img), x=x_img, y=self.get_y(), w=sig_w)
        self.ln(45)  # avance vertical después de la imagen (ajusta según tu firma.png)


    # ─────────────── Render principal ───────────────
    def render_precosteo(
        self,
        codigo_precosteo: str,
        resumen: str,
        df_lugares,
        fecha_inicio,
        fecha_fin,
        bd,
    ) -> None:
        """
        Construye el PDF:
        - Código arriba a la derecha
        - Fecha dinámica (Santiago de Cali, ...)
        - Señores + razón social fija
        - Resumen
        - Lugar de ejecución (desde df_lugares)
        - Tabla de actividades filtradas por [fecha_inicio, fecha_fin] desde bd
        """
        self._bd = bd

        self.new_page()

        # Código (derecha)
        self.set_default_typography(size=12, bold=True)
        self.cell(0, 6, codigo_precosteo, ln=1, align="R")

        # Ciudad + fecha
        self.ln(2)
        self.set_default_typography(size=12, bold=True)
        self.cell(0, 6, f"Santiago de Cali, {self._fecha_es(datetime.now())}", ln=1, align="L")

        # Señores
        self.ln(6)
        self.set_default_typography(size=12, bold=True)
        self.cell(0, 6, "Señores:", ln=1, align="L")

        self.ln(4)
        self.set_default_typography(size=12, bold=True)
        self.multi_cell(0, 6, "SOCIEDAD PORTUARIA REGIONAL DE BUENAVENTURA", align="L")

        # Resumen
        self.ln(3)
        self.set_default_typography(size=11, bold=False)
        self.multi_cell(0, 6, resumen.strip(), align="J")

        # Lugar ejecución
        lugares_txt = self._infer_lugares_text(df_lugares)
        if lugares_txt:
            self.ln(4)
            self.set_default_typography(size=11, bold=True)
            self.cell(self.get_string_width("Lugar de ejecución:") + 1, 6, "Lugar de ejecución:", ln=0)
            self.set_default_typography(size=11, bold=False)
            self.multi_cell(0, 6, f" {lugares_txt}", align="L")

        # Tabla actividades (filtrada por fechas)
        bd_filtrado = self.filter_bd_by_range(bd, fecha_inicio, fecha_fin)

        # Excluir actividades por ID_ITEM (ej: 1.21 = "Llenado de tanques")
        if bd_filtrado is not None and "ID_ITEM" in bd_filtrado.columns:
            bd_filtrado = bd_filtrado[bd_filtrado["ID_ITEM"].astype(str).str.strip() != "1.21"]

        # Para el título amarillo usamos un "título corto" del lugar:
        lugar_titulo = ""
        if lugares_txt:
            # si viene largo, usa la primera parte como título
            lugar_titulo = lugares_txt.split(",")[0].strip()[:60]
        self._write_section_table(lugar_titulo=lugar_titulo or "LUGAR DE EJECUCIÓN", codigo_precosteo=codigo_precosteo, bd_filtrado=bd_filtrado)
        # 👉 ESTADO + FIRMA (ESTO FALTABA)
        self._write_precosteo_status_and_signature("EN APROBACIÓN")


    # ─────────────── Guardado ───────────────
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
