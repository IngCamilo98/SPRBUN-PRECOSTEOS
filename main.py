import pandas as pd
from MODULES.CREATE_PRECOSTEO_PDF import CreatePrecostoPDF

def main():
    # Ejemplo df_lugares (ajústalo a tu Excel real)
    df_lugares = pd.DataFrame({
        "LUGAR_EJECUCION": ["Interior Sociedad Portuaria de Buenaventura, Caseta Comedor Muelle 10"]
    })

    resumen = (
        "Durante la inspección realizada a la caseta comedor ubicado en el muelle 10, "
        "se evidenció que la mampara perimetral se encuentra en mal estado general..."
    )

    codigo = "PRECOSTEO-AMC-0030-25-SPRBUN"

    pdf = CreatePrecostoPDF()
    pdf.render_precosteo(
        codigo_precosteo=codigo,
        resumen=resumen,
        df_lugares=df_lugares,
        bd=None,  # por ahora
    )

    out = pdf.save(cod_prec=codigo)
    print(f"✅ PDF generado: {out}")

if __name__ == "__main__":
    main()
