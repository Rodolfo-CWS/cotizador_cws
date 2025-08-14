from database import DatabaseManager

db = DatabaseManager()
result = db.obtener_todas_cotizaciones()
cotizaciones = result.get('cotizaciones', [])

print(f"Total quotations: {len(cotizaciones)}")
print("\nRecent quotations:")
for c in cotizaciones[-5:]:
    numero = c.get('datosGenerales', {}).get('numeroCotizacion', 'N/A')
    print(f"- {numero}")