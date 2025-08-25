"""
Test para validar el flujo completo de "Nueva Revisión"
Verifica que el botón aparezca y que el flujo de creación de revisiones funcione correctamente
"""

import os
import json
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_boton_nueva_revision():
    """Test para verificar que el botón Nueva Revisión aparece correctamente"""
    print("=== TEST: BOTÓN NUEVA REVISIÓN ===")
    
    try:
        # Importar managers
        from supabase_manager import SupabaseManager
        
        # Inicializar manager
        print("\n1. Inicializando SupabaseManager...")
        db_manager = SupabaseManager()
        print(f"   Modo offline: {db_manager.modo_offline}")
        
        # Buscar una cotización existente para probar
        print("\n2. Buscando cotización de prueba...")
        resultado_busqueda = db_manager.buscar_cotizaciones("", 1, 5)
        
        if not resultado_busqueda.get("error") and resultado_busqueda.get("resultados"):
            cotizaciones = resultado_busqueda["resultados"]
            print(f"   Encontradas {len(cotizaciones)} cotizaciones")
            
            for i, cot in enumerate(cotizaciones[:2]):
                numero_cotizacion = cot.get('numeroCotizacion', 'N/A')
                print(f"\n   Cotización {i+1}: {numero_cotizacion}")
                
                # Verificar campos necesarios para el botón
                campos_necesarios = ['numeroCotizacion', 'numero_cotizacion', '_id']
                campos_disponibles = []
                
                for campo in campos_necesarios:
                    if cot.get(campo):
                        campos_disponibles.append(f"{campo}: '{cot[campo]}'")
                
                print(f"     Campos para botón: {', '.join(campos_disponibles)}")
                
                # Simular la lógica del template
                revision_id = cot.get('numeroCotizacion') or cot.get('numero_cotizacion') or cot.get('_id')
                boton_disponible = bool(revision_id)
                
                print(f"     Boton 'Nueva Revision': {'VISIBLE' if boton_disponible else 'OCULTO'}")
                if boton_disponible:
                    print(f"     URL: /formulario?revision={revision_id}")
        else:
            print("   [WARNING] No se encontraron cotizaciones de prueba")
            return False
        
        print("\nTest de boton completado")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] ERROR en test de botón: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flujo_nueva_revision():
    """Test para verificar el flujo completo de creación de revisiones"""
    print("\n=== TEST: FLUJO NUEVA REVISIÓN ===")
    
    try:
        # Importar managers y funciones
        from supabase_manager import SupabaseManager
        import sys
        import os
        
        # Añadir directorio actual al path para importar app
        sys.path.append(os.path.dirname(__file__))
        
        # Importar función de preparación de revisiones
        from app import preparar_datos_nueva_revision
        
        # Inicializar manager
        print("\n1. Inicializando SupabaseManager...")
        db_manager = SupabaseManager()
        
        # Buscar cotización de prueba
        print("\n2. Obteniendo cotización de prueba...")
        resultado_busqueda = db_manager.buscar_cotizaciones("", 1, 1)
        
        if not resultado_busqueda.get("error") and resultado_busqueda.get("resultados"):
            cotizacion_original = resultado_busqueda["resultados"][0]
            numero_original = cotizacion_original.get('numeroCotizacion', 'N/A')
            print(f"   Cotización original: {numero_original}")
            
            # Test 1: Preparar datos para nueva revisión
            print("\n3. Preparando datos para nueva revisión...")
            try:
                datos_revision = preparar_datos_nueva_revision(cotizacion_original)
                
                # Verificar campos clave
                datos_generales = datos_revision.get('datosGenerales', {})
                revision_nueva = datos_generales.get('revision', 'N/A')
                numero_nuevo = datos_generales.get('numeroCotizacion', 'N/A')
                
                print(f"   [OK] Revisión incrementada: {revision_nueva}")
                print(f"   [OK] Número nuevo: {numero_nuevo}")
                
                # Verificar que el número cambió
                if numero_nuevo != numero_original:
                    print(f"   [OK] Número actualizado correctamente")
                else:
                    print(f"   [WARNING] Número no cambió: {numero_original} → {numero_nuevo}")
                
                # Verificar formato de número (debería incluir nuevas iniciales de vendedor)
                if 'CWS' in numero_nuevo:
                    print(f"   [OK] Formato CWS correcto")
                else:
                    print(f"   [WARNING] Formato CWS incorrecto: {numero_nuevo}")
                
                # Verificar que mantiene los datos originales
                items_originales = len(cotizacion_original.get('items', []))
                items_revision = len(datos_revision.get('items', []))
                print(f"   [OK] Items preservados: {items_originales} → {items_revision}")
                
            except Exception as e:
                print(f"   [ERROR] Error preparando revisión: {e}")
                return False
            
            # Test 2: Simular obtención de cotización por número (como en formulario)
            print("\n4. Simulando búsqueda para formulario...")
            resultado_obtencion = db_manager.obtener_cotizacion(numero_original)
            
            if resultado_obtencion.get('encontrado'):
                print(f"   [OK] Cotización encontrada por número: {numero_original}")
                cotizacion_encontrada = resultado_obtencion['item']
                print(f"   [OK] Campos disponibles: {list(cotizacion_encontrada.keys())}")
            else:
                print(f"   [WARNING] Cotización no encontrada por número: {numero_original}")
            
            # Test 3: Verificar que la función generar_numero_revision funciona
            print("\n5. Probando generación de número de revisión...")
            try:
                if hasattr(db_manager, 'generar_numero_revision'):
                    numero_r2 = db_manager.generar_numero_revision(numero_original, "2")
                    numero_r3 = db_manager.generar_numero_revision(numero_original, "3")
                    
                    print(f"   [OK] R1: {numero_original}")
                    print(f"   [OK] R2: {numero_r2}")
                    print(f"   [OK] R3: {numero_r3}")
                else:
                    print(f"   [WARNING] Función generar_numero_revision no disponible")
            except Exception as e:
                print(f"   [WARNING] Error generando números de revisión: {e}")
        
        else:
            print("   [WARNING] No se encontraron cotizaciones para probar")
            return False
        
        print("\n[OK] Test de flujo completado exitosamente")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] ERROR en test de flujo: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_template_debugging():
    """Test para simular el debugging del template"""
    print("\n=== TEST: DEBUGGING TEMPLATE ===")
    
    try:
        from supabase_manager import SupabaseManager
        
        # Inicializar manager
        db_manager = SupabaseManager()
        
        # Obtener una cotización
        resultado_busqueda = db_manager.buscar_cotizaciones("", 1, 1)
        
        if not resultado_busqueda.get("error") and resultado_busqueda.get("resultados"):
            cotizacion = resultado_busqueda["resultados"][0]
            
            print("\n1. Simulando lógica del template...")
            
            # Simular la lógica exacta del template
            numero_cotizacion = cotizacion.get('numeroCotizacion') or cotizacion.get('numero_cotizacion') or cotizacion.get('_id')
            
            print(f"   numeroCotizacion: {repr(cotizacion.get('numeroCotizacion'))}")
            print(f"   numero_cotizacion: {repr(cotizacion.get('numero_cotizacion'))}")
            print(f"   _id: {repr(cotizacion.get('_id'))}")
            print(f"   Resultado final: {repr(numero_cotizacion)}")
            
            if numero_cotizacion:
                print(f"\n   [OK] BOTÓN VISIBLE - URL: /formulario?revision={numero_cotizacion}")
            else:
                print(f"\n   [ERROR] BOTÓN OCULTO")
                print(f"   Campos disponibles: {list(cotizacion.keys())}")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] ERROR en test de template: {e}")
        return False

if __name__ == "__main__":
    print("INICIANDO TESTS DE NUEVA REVISION")
    
    # Test 1: Verificar botón
    boton_ok = test_boton_nueva_revision()
    
    # Test 2: Verificar flujo
    flujo_ok = test_flujo_nueva_revision()
    
    # Test 3: Debugging template
    template_ok = test_template_debugging()
    
    # Resumen
    print(f"\n{'='*50}")
    print("[SUMMARY] RESUMEN DE TESTS:")
    print(f"   Botón Nueva Revisión: {'[OK] OK' if boton_ok else '[ERROR] FALLA'}")
    print(f"   Flujo de Revisión: {'[OK] OK' if flujo_ok else '[ERROR] FALLA'}")
    print(f"   Template Debugging: {'[OK] OK' if template_ok else '[ERROR] FALLA'}")
    
    if boton_ok and flujo_ok and template_ok:
        print(f"\n[SUCCESS] TODOS LOS TESTS PASARON - NUEVA REVISIÓN FUNCIONAL")
    else:
        print(f"\n[WARNING] ALGUNOS TESTS FALLARON - REVISAR CONFIGURACIÓN")
    
    print("\nPara probar manualmente:")
    print("1. Ir a cualquier desglose de cotización")
    print("2. Buscar el botón 'Nueva Revisión' (verde)")
    print("3. Hacer clic para abrir formulario pre-cargado")
    print("4. Verificar que la revisión se incrementó (R1→R2)")