#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regenerar PDF para la cotización BMW-CWS-CM-001-R1-GROW
"""

def regenerar_pdf_bmw():
    print("REGENERANDO PDF PARA BMW-CWS-CM-001-R1-GROW")
    print("=" * 60)
    
    try:
        # Importar módulos necesarios
        from supabase_manager import SupabaseManager
        from pdf_manager import PDFManager
        from app import generar_pdf_reportlab
        
        numero_cotizacion = "BMW-CWS-CM-001-R1-GROW"
        
        # 1. Inicializar managers
        print("1. Inicializando sistemas...")
        db_manager = SupabaseManager()
        pdf_manager = PDFManager(db_manager)
        print("OK Managers inicializados")
        
        # 2. Obtener datos de la cotización
        print(f"\n2. Obteniendo datos de cotización: {numero_cotizacion}")
        cotizacion_result = db_manager.obtener_cotizacion(numero_cotizacion)
        
        if not cotizacion_result.get("encontrado"):
            print(f"ERROR: Cotización {numero_cotizacion} no encontrada en BD")
            return False
            
        cotizacion_data = cotizacion_result.get("item", {})
        print("OK Cotización encontrada:")
        print(f"  Cliente: {cotizacion_data.get('datosGenerales', {}).get('cliente', 'N/A')}")
        print(f"  Vendedor: {cotizacion_data.get('datosGenerales', {}).get('vendedor', 'N/A')}")
        print(f"  Proyecto: {cotizacion_data.get('datosGenerales', {}).get('proyecto', 'N/A')}")
        print(f"  Items: {len(cotizacion_data.get('items', []))}")
        
        # 3. Generar PDF
        print(f"\n3. Generando PDF...")
        try:
            pdf_data = generar_pdf_reportlab(cotizacion_data)
            print(f"OK PDF generado correctamente: {len(pdf_data)} bytes")
        except Exception as pdf_error:
            print(f"ERROR generando PDF: {pdf_error}")
            import traceback
            traceback.print_exc()
            return False
        
        # 4. Almacenar PDF
        print(f"\n4. Almacenando PDF en Supabase Storage...")
        try:
            resultado_almacenamiento = pdf_manager.almacenar_pdf_nuevo(
                pdf_data, 
                cotizacion_data
            )
            
            if resultado_almacenamiento.get("success"):
                print("OK PDF almacenado exitosamente!")
                print(f"  Estado: {resultado_almacenamiento.get('estado', 'N/A')}")
                print(f"  Mensaje: {resultado_almacenamiento.get('mensaje', 'N/A')}")
                print(f"  Tamaño: {resultado_almacenamiento.get('tamaño', 0)} bytes")
                
                # Mostrar detalles de sistemas
                sistemas = resultado_almacenamiento.get('sistemas', {})
                for sistema, detalles in sistemas.items():
                    if detalles.get('success'):
                        print(f"  {sistema.upper()}: OK")
                        if 'url' in detalles:
                            print(f"    URL: {detalles['url']}")
                    else:
                        print(f"  {sistema.upper()}: FALLO - {detalles.get('error', 'Error desconocido')}")
                        
                return True
            else:
                print(f"ERROR almacenando PDF: {resultado_almacenamiento.get('error', 'Error desconocido')}")
                return False
                
        except Exception as storage_error:
            print(f"ERROR en almacenamiento: {storage_error}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()
        return False

def verificar_pdf_regenerado():
    """Verificar que el PDF se regeneró correctamente"""
    print("\n" + "=" * 60)
    print("VERIFICANDO PDF REGENERADO")
    print("=" * 60)
    
    try:
        from pdf_manager import PDFManager
        from supabase_manager import SupabaseManager
        
        db_manager = SupabaseManager()
        pdf_manager = PDFManager(db_manager)
        numero_cotizacion = "BMW-CWS-CM-001-R1-GROW"
        
        # Buscar PDF regenerado
        resultado_pdf = pdf_manager.obtener_pdf(numero_cotizacion)
        if resultado_pdf.get("encontrado"):
            print("OK PDF encontrado después de regeneración:")
            print(f"  Tipo: {resultado_pdf.get('tipo', 'N/A')}")
            print(f"  URL: {resultado_pdf.get('url_directa', 'N/A')}")
            print(f"  Fuente: {resultado_pdf.get('fuente', 'N/A')}")
            return True
        else:
            print("ERROR PDF aún no encontrado después de regeneración")
            return False
            
    except Exception as e:
        print(f"ERROR verificando PDF regenerado: {e}")
        return False

if __name__ == "__main__":
    exito = regenerar_pdf_bmw()
    if exito:
        verificar_pdf_regenerado()
        print("\nREGENERACION COMPLETADA EXITOSAMENTE")
    else:
        print("\nERROR EN REGENERACION")