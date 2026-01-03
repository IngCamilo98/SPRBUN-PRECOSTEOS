import pandas as pd
from MODULES.CREATE_PRECOSTEO_PDF import CreatePrecostoPDF

def main():
    codigo = "PRECOSTEO-AMC-0030-25-SPRBUN"

    resumen = (
        "Durante la inspección realizada a la caseta comedor ubicado en el muelle 10, "
        "se evidenció que la mampara perimetral se encuentra en mal estado general..."
    )

    # Lugares (ejemplo)
    df_lugares = pd.DataFrame({
        "LUGAR_EJECUCION": ["Interior Sociedad Portuaria de Buenaventura, Caseta Comedor Muelle 10"]
    })

    # BD desde Excel
    ruta = "BD/EXCEL/BD_ACTIVIDADES_HIDROSANITARIAS_CUBIERTAS.xlsx"
    bd = pd.read_excel(ruta, sheet_name="BD")

    # Rango fechas
    fecha_inicio = "11/26/2025"
    fecha_fin = "11/29/2025"

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
