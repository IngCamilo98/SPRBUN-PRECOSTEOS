import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from google import genai


class CREATE_RESUME:
    def __init__(
        self,
        bd: pd.DataFrame,
        fecha_inicial: str,
        fecha_final: str,
        model_name: str = "gemini-2.0-flash",
        max_unique_activities: int = 250,
    ):
        self.bd = bd.copy()
        self.fecha_inicial = self._format_date_mmddyyyy(fecha_inicial)
        self.fecha_final = self._format_date_mmddyyyy(fecha_final)
        self.model_name = model_name
        self.max_unique_activities = max_unique_activities

        self._validar_dataframe()
        self.actividades_unicas = self._obtener_actividades_unicas()
        self._configurar_gemini()

    @staticmethod
    def _format_date_mmddyyyy(fecha: str) -> str:
        fecha = str(fecha).strip()
        for fmt in ("%m/%d/%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(fecha, fmt).strftime("%m/%d/%Y")
            except ValueError:
                continue
        raise ValueError(f"❌ Formato de fecha inválido: {fecha}. Use MM/DD/YYYY.")

    def _validar_dataframe(self):
        if "ACTIVIDAD" not in self.bd.columns:
            raise ValueError("❌ El DataFrame no contiene la columna 'ACTIVIDAD'")

    def _obtener_actividades_unicas(self) -> list[str]:
        serie = (
            self.bd["ACTIVIDAD"]
            .dropna()
            .astype(str)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )
        serie = serie[serie != ""]
        unicas = pd.unique(serie).tolist()
        return unicas[: self.max_unique_activities]

    def _configurar_gemini(self):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ No se encontró GEMINI_API_KEY en tu .env")
        self.client = genai.Client(api_key=api_key)

    def _build_prompt(self) -> str:
        actividades_bullets = "\n- " + "\n- ".join(self.actividades_unicas)
        return f"""
Eres un ingeniero encargado de elaborar informes técnicos de mantenimiento.

Con base en las actividades (únicas) realizadas entre {self.fecha_inicial} y {self.fecha_final},
redacta un resumen general:

REQUISITOS:
- Un solo párrafo (máximo 6-8 líneas).
- Español profesional, tono técnico.
- Tercera persona.
- No enumerar actividades una por una.
- No inventar datos numéricos.

ACTIVIDADES ÚNICAS:
{actividades_bullets}
""".strip()

    def generate_text(self) -> str:
        if not self.actividades_unicas:
            return "No se encontraron actividades para generar el resumen."

        prompt = self._build_prompt()

        try:
            resp = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = getattr(resp, "text", None)
            return (text or "").strip() or "No se pudo obtener texto desde Gemini (respuesta vacía)."
        except Exception as e:
            raise RuntimeError(f"❌ Error al generar resumen con Gemini: {e}")
