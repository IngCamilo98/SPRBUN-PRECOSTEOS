import pandas as pd

from dotenv import load_dotenv

from MODULES.CREATE_PRECOSTEO_PDF import CreatePrecostoPDF
from MODULES.CREATE_RESUME import CREATE_RESUME

def main():
    load_dotenv()
    codigo = "PRECOSTEO-AMC-0030-25-SPRBUN"

    # Rango fechas
    fecha_inicio = "11/26/2025"
    fecha_fin = "12/18/2025"

    resumen = (
        "Las actividades ejecutadas se orientaron al mantenimiento integral de cubiertas "
        "y sistemas hidrosanitarios, incluyendo revisiones técnicas y labores necesarias "
        "para garantizar su correcto funcionamiento.\n\n"
        "Se realizaron trabajos de mantenimiento preventivo y correctivo en cubiertas por "
        "filtraciones de aguas lluvias, abarcando la limpieza de canales y la ejecución de "
        "labores en altura con los equipos de seguridad requeridos.\n\n"
        "Adicionalmente, se llevaron a cabo revisiones hidrosanitarias, destapes sencillos "
        "y especializados de aparatos sanitarios, instalación y reparación de accesorios y "
        "aparatos sanitarios, así como reparaciones puntuales en tuberías, tanques y equipos "
        "como motobombas, asegurando la continuidad, higiene y adecuada operación de las "
        "instalaciones intervenidas."
    )

    # BD desde Excel
    ruta = "BD/EXCEL/BD_ACTIVIDADES_HIDROSANITARIAS_CUBIERTAS.xlsx"
    bd = pd.read_excel(ruta, sheet_name="BD")
    """
    resumenador = CREATE_RESUME(
        bd=bd,
        fecha_inicial=fecha_inicio,  # MM/DD/YYYY
        fecha_final=fecha_fin     # MM/DD/YYYY
    )

    resumen = resumenador.generate_text()
    print(resumen)
    """
    # df_lugares a partir de ZONA (solo valores únicos y válidos)
    df_lugares = (
        bd[["ZONA"]]
        .dropna()
        .assign(ZONA=lambda d: d["ZONA"].astype(str).str.strip())
        .drop_duplicates()
        .reset_index(drop=True)
        )



    pdf = CreatePrecostoPDF()
    pdf.render_precosteo(
        codigo_precosteo=codigo,
        resumen=resumen,
        df_lugares=df_lugares,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        bd=bd,
    )

    out = pdf.save(cod_prec=codigo)
    print(f"✅ PDF generado: {out}")

if __name__ == "__main__":
    main()
