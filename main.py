from MODULES.CREATE_PRECOSTEO_PDF import CreatePrecostoPDF

def main():

    pdf = CreatePrecostoPDF()
    pdf.render_demo()  # main no define fonts ni escribe texto
    out = pdf.save(cod_prec="PRECOSTEO-AMC-TEST")
    print(f"✅ PDF generado: {out}")

if __name__ == "__main__":
    main()
