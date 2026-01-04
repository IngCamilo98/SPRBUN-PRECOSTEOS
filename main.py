import pandas as pd
from MODULES.CREATE_PRECOSTEO_PDF import CreatePrecostoPDF
from MODULES.CREATE_RESUME import CreateResume

def main():
    codigo = "PRECOSTEO-AMC-0030-25-SPRBUN"

    # Rango fechas
    fecha_inicio = "11/26/2025"
    fecha_fin = "12/18/2025"

    
    resumen = (
        "Durante la inspección realizada a la caseta comedor ubicado en el muelle 10, "
        "se evidenció que la mampara perimetral se encuentra en mal estado general..."
    )

    # BD desde Excel
    ruta = "BD/EXCEL/BD_ACTIVIDADES_HIDROSANITARIAS_CUBIERTAS.xlsx"
    bd = pd.read_excel(ruta, sheet_name="BD")
    """
    resumer = CreateResume()
    resumen = resumer.generate_resume(bd, fecha_inicio, fecha_fin)
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
