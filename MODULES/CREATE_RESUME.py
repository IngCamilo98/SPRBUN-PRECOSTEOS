# MODULES/CREATE_RESUME.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List
import os

import pandas as pd


@dataclass(frozen=True)
class ResumeConfig:
    # Modelo Gemini (ajústalo si quieres)
    model: str = "gemini-1.5-flash"

    # Seguridad para no mandar demasiado texto
    max_unique_activities: int = 250
    max_chars: int = 18_000

    # Parseo de fecha
    dayfirst: bool = False  # si tus fechas son dd/mm/yyyy pon True

    # Exclusiones (coherente con precosteo)
    exclude_id_item: bool = True
    excluded_id_items: tuple[str, ...] = ("1.21",)  # Llenado de tanques


class CreateResume:
    """
    Genera un resumen general de actividades (entre fecha_inicio y fecha_fin) usando Gemini.

    Espera en BD:
      - FECHA
      - ACTIVIDAD
    Opcionales:
      - ZONA, UNIDAD_MEDIDA, CANTIDAD, DESCRIPCION, ID_ITEM

    Uso:
      resumer = CreateResume()
      resumen = resumer.generate_resume(bd, "11/14/2025", "11/26/2025")
    """

    def __init__(self, api_key: Optional[str] = None, config: ResumeConfig | None = None):
        self.config = config or ResumeConfig()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Falta GEMINI_API_KEY. Define la variable de entorno o pásala al constructor."
            )

        # Import aquí para que el módulo no falle si aún no instalas la librería
        from google import genai  # type: ignore
        self._client = genai.Client(api_key=self.api_key)

    # -------------------- Utilidades --------------------
    def _validate_columns(self, df: pd.DataFrame, required: List[str]) -> None:
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise KeyError(f"Faltan columnas requeridas en BD: {missing}")

    def _to_datetime_series(self, s: pd.Series) -> pd.Series:
        return pd.to_datetime(s, errors="coerce", dayfirst=self.config.dayfirst)

    @staticmethod
    def _clean_str_series(s: pd.Series) -> pd.Series:
        return s.astype(str).str.replace("\r", " ", regex=False).str.replace("\n", " ", regex=False).str.strip()

    # -------------------- Filtro por fechas --------------------
    def filter_by_date(self, bd: pd.DataFrame, fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
        """
        Filtra bd por columna FECHA entre fecha_inicio y fecha_fin.
        """
        self._validate_columns(bd, ["FECHA", "ACTIVIDAD"])

        df = bd.copy()

        df["__FECHA_DT__"] = self._to_datetime_series(df["FECHA"])

        fi = pd.to_datetime(fecha_inicio, errors="coerce", dayfirst=self.config.dayfirst)
        ff = pd.to_datetime(fecha_fin, errors="coerce", dayfirst=self.config.dayfirst)

        if pd.isna(fi) or pd.isna(ff):
            raise ValueError(
                "fecha_inicio o fecha_fin no se pudieron parsear. Usa formato YYYY-MM-DD, MM/DD/YYYY o DD/MM/YYYY."
            )

        mask = (df["__FECHA_DT__"] >= fi) & (df["__FECHA_DT__"] <= ff)
        out = df.loc[mask].drop(columns=["__FECHA_DT__"], errors="ignore")

        # Exclusión opcional por ID_ITEM (ej. 1.21 llenado de tanques)
        if self.config.exclude_id_item and "ID_ITEM" in out.columns:
            out = out[out["ID_ITEM"].astype(str).str.strip() \
                      .isin(self.config.excluded_id_items) == False]  # noqa: E712

        return out

    # -------------------- Construcción payload (ÚNICOS) --------------------
    def _build_payload_text_unique(self, df_range: pd.DataFrame) -> str:
        """
        Envía a Gemini SOLO actividades únicas.
        Opcionalmente agrega un poco de contexto (zona/unidad/cantidad) si existe,
        pero siempre deduplicando por ACTIVIDAD.
        """
        # Limpieza de ACTIVIDAD
        df_range = df_range.copy()
        df_range["ACTIVIDAD"] = self._clean_str_series(df_range["ACTIVIDAD"])
        df_range = df_range[df_range["ACTIVIDAD"].astype(str).str.strip() != ""]

        # Base: actividades únicas
        unique_acts = (
            df_range[["ACTIVIDAD"]]
            .dropna()
            .drop_duplicates()
            .reset_index(drop=True)
            .head(self.config.max_unique_activities)
        )

        # Contexto opcional: zonas únicas (no lista gigante)
        zonas_txt = ""
        if "ZONA" in df_range.columns:
            z = df_range["ZONA"].dropna()
            if not z.empty:
                z = self._clean_str_series(z)
                zonas = z.drop_duplicates().tolist()
                # limita zonas para no explotar
                zonas = zonas[:20]
                zonas_txt = ", ".join(zonas)

        # Construcción texto
        lines: List[str] = []
        if zonas_txt:
            lines.append(f"ZONAS (referencia general): {zonas_txt}")
            lines.append("")

        lines.append("ACTIVIDADES ÚNICAS:")
        for _, r in unique_acts.iterrows():
            lines.append(f"- {r['ACTIVIDAD']}")

        text = "\n".join(lines)

        # Truncado seguridad
        if len(text) > self.config.max_chars:
            text = text[: self.config.max_chars] + "\n[...TRUNCADO POR LÍMITE...]"

        return text

    # -------------------- Gemini --------------------
    def generate_resume(self, bd: pd.DataFrame, fecha_inicio: str, fecha_fin: str) -> str:
        """
        Devuelve un resumen general (texto) de las actividades en el rango.
        Usa SOLO actividades únicas para el prompt.
        """
        df_range = self.filter_by_date(bd, fecha_inicio, fecha_fin)

        if df_range.empty:
            return "No se encontraron actividades en el rango de fechas indicado."

        payload = self._build_payload_text_unique(df_range)

        prompt = f"""
Eres un asistente técnico para una empresa de mantenimiento (cubiertas e hidrosanitario).
Con base en el listado de ACTIVIDADES ÚNICAS, redacta un RESUMEN GENERAL para un informe.

Condiciones:
- 1 a 2 párrafos.
- Español, tono profesional.
- No enumerar ítems; agrupa por tipos de mantenimiento (hidrosanitario, cubiertas, sellados, limpieza, inspecciones, ajustes, correctivos/preventivos, etc.).
- Si aparecen zonas, menciónalas de forma global (no como lista larga).
- No inventar datos.
- Indicar que el resumen corresponde al periodo entre {fecha_inicio} y {fecha_fin}.

Fuente:
{payload}
""".strip()

        resp = self._client.models.generate_content(
            model=self.config.model,
            contents=prompt,
        )

        return (resp.text or "").strip()
