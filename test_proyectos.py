#!/usr/bin/env python3
"""
Test completo del módulo de Proyectos y Órdenes de Compra

Prueba todas las funcionalidades:
- OCManager: Crear, listar, buscar OCs
- ProyectoManager: Crear gastos, aprobar, rechazar, marcar ordenado/recibido
- NotificacionesManager: Crear notificaciones, contar, marcar como leídas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from oc_manager import OCManager
from proyecto_manager import ProyectoManager
from notificaciones_manager import NotificacionesManager
import json
from datetime import datetime, date

def print_separator(title):
    """Imprime un separador visual para las secciones de test"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")

def print_result(success, message):
    """Imprime resultado de un test con formato consistente"""
    symbol = "✓" if success else "✗"
    print(f"{symbol} {message}")

def test_oc_manager():
    """Test de OCManager - Gestión de Órdenes de Compra"""
    print_separator("TEST 1: OCManager - Órdenes de Compra")

    try:
        oc_manager = OCManager()
        print_result(True, "OCManager inicializado correctamente")
    except Exception as e:
        print_result(False, f"Error inicializando OCManager: {e}")
        return False

    # Test 1: Crear una OC nueva
    print("\n1. Crear nueva Orden de Compra:")
    datos_oc = {
        'numero_oc': f'OC-TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'cliente': 'ACME Corporation TEST',
        'monto_total': 150000.00,
        'moneda': 'MXN',
        'fecha_recepcion': date.today().isoformat(),
        'fecha_inicio': date.today().isoformat(),
        'notas': 'Orden de compra de prueba para el módulo de proyectos',
        'proyecto_nombre': 'Proyecto TEST - Instalación de Racks',
        'proyecto_descripcion': 'Proyecto de prueba para validar funcionalidad'
    }

    resultado_oc = oc_manager.crear_oc(datos_oc)

    if resultado_oc.get('success'):
        oc_id = resultado_oc.get('oc_id')
        proyecto_id = resultado_oc.get('proyecto_id')
        print_result(True, f"OC creada con ID: {oc_id}")
        print_result(True, f"Proyecto automático creado con ID: {proyecto_id}")
    else:
        print_result(False, f"Error creando OC: {resultado_oc.get('message')}")
        return False

    # Test 2: Obtener OC por ID
    print("\n2. Obtener OC por ID:")
    oc_obtenida = oc_manager.obtener_oc(oc_id)

    if oc_obtenida:
        print_result(True, f"OC recuperada: {oc_obtenida.get('numero_oc')}")
        print(f"   Cliente: {oc_obtenida.get('cliente')}")
        print(f"   Monto: ${oc_obtenida.get('monto_total'):,.2f} {oc_obtenida.get('moneda')}")
    else:
        print_result(False, "No se pudo recuperar la OC")
        return False

    # Test 3: Listar OCs
    print("\n3. Listar todas las OCs:")
    lista_ocs = oc_manager.listar_ocs(limite=10)

    if lista_ocs:
        print_result(True, f"Se encontraron {len(lista_ocs)} OC(s)")
        for oc in lista_ocs[:3]:  # Mostrar solo las primeras 3
            print(f"   - {oc.get('numero_oc')} | {oc.get('cliente')} | ${oc.get('monto_total'):,.2f}")
    else:
        print_result(False, "No se encontraron OCs")

    # Test 4: Buscar OCs
    print("\n4. Buscar OC por texto:")
    resultados_busqueda = oc_manager.buscar_ocs('TEST')

    if resultados_busqueda:
        print_result(True, f"Búsqueda encontró {len(resultados_busqueda)} resultado(s)")
    else:
        print_result(False, "Búsqueda no retornó resultados")

    # Test 5: Estadísticas
    print("\n5. Obtener estadísticas:")
    stats = oc_manager.obtener_estadisticas()

    if stats:
        print_result(True, "Estadísticas obtenidas")
        print(f"   Total OCs: {stats.get('total_ocs', 0)}")
        print(f"   Activas: {stats.get('activas', 0)}")
        print(f"   Monto activo: ${stats.get('monto_activo', 0):,.2f}")
    else:
        print_result(False, "No se pudieron obtener estadísticas")

    print_result(True, "OCManager: Todas las pruebas completadas")
    return {'oc_id': oc_id, 'proyecto_id': proyecto_id}

def test_proyecto_manager(proyecto_id):
    """Test de ProyectoManager - Gestión de Gastos y Aprobaciones"""
    print_separator("TEST 2: ProyectoManager - Gastos y Aprobaciones")

    try:
        proyecto_manager = ProyectoManager()
        print_result(True, "ProyectoManager inicializado correctamente")
    except Exception as e:
        print_result(False, f"Error inicializando ProyectoManager: {e}")
        return False

    # Test 1: Obtener proyecto
    print("\n1. Obtener información del proyecto:")
    proyecto = proyecto_manager.obtener_proyecto(proyecto_id)

    if proyecto:
        print_result(True, f"Proyecto recuperado: {proyecto.get('nombre')}")
        print(f"   Presupuesto: ${proyecto.get('monto_presupuestado', 0):,.2f}")
        print(f"   Estado: {proyecto.get('estatus')}")
    else:
        print_result(False, "No se pudo recuperar el proyecto")
        return False

    # Test 2: Crear gastos
    print("\n2. Crear gastos en el proyecto:")
    gastos_test = [
        {
            'proyecto_id': proyecto_id,
            'concepto': 'Rack Metálico Industrial 48U',
            'proveedor': 'Racks México SA',
            'cantidad': 5.0,
            'unidad': 'pieza',
            'precio_unitario': 8500.00,
            'notas': 'Racks para centro de datos'
        },
        {
            'proyecto_id': proyecto_id,
            'concepto': 'Cableado estructurado Cat6',
            'proveedor': 'Cable Solutions',
            'cantidad': 500.0,
            'unidad': 'metro',
            'precio_unitario': 25.00,
            'notas': 'Cable certificado para red'
        }
    ]

    gastos_ids = []
    for i, datos_gasto in enumerate(gastos_test, 1):
        resultado = proyecto_manager.crear_gasto(datos_gasto)

        if resultado.get('success'):
            gasto_id = resultado.get('gasto_id')
            gastos_ids.append(gasto_id)
            print_result(True, f"Gasto {i} creado con ID: {gasto_id}")
        else:
            print_result(False, f"Error creando gasto {i}: {resultado.get('message')}")

    if not gastos_ids:
        print_result(False, "No se pudo crear ningún gasto")
        return False

    # Test 3: Listar gastos del proyecto
    print("\n3. Listar gastos del proyecto:")
    gastos = proyecto_manager.listar_gastos_proyecto(proyecto_id)

    if gastos:
        print_result(True, f"Se encontraron {len(gastos)} gasto(s)")
        for gasto in gastos:
            print(f"   - {gasto.get('concepto')} | ${gasto.get('subtotal'):,.2f} | Estado: {gasto.get('estatus_compra')}")
    else:
        print_result(False, "No se encontraron gastos")

    # Test 4: Aprobar gasto
    print("\n4. Aprobar primer gasto:")
    gasto_id = gastos_ids[0]
    resultado_aprobacion = proyecto_manager.aprobar_gasto(gasto_id, aprobador='test_user')

    if resultado_aprobacion.get('success'):
        print_result(True, "Gasto aprobado correctamente")
    else:
        print_result(False, f"Error aprobando gasto: {resultado_aprobacion.get('message')}")

    # Test 5: Rechazar segundo gasto (si existe)
    if len(gastos_ids) > 1:
        print("\n5. Rechazar segundo gasto:")
        resultado_rechazo = proyecto_manager.rechazar_gasto(
            gastos_ids[1],
            motivo='Proveedor no autorizado - solo para test'
        )

        if resultado_rechazo.get('success'):
            print_result(True, "Gasto rechazado correctamente")
        else:
            print_result(False, f"Error rechazando gasto: {resultado_rechazo.get('message')}")

    # Test 6: Marcar como ordenado
    print("\n6. Marcar gasto como ordenado:")
    resultado_ordenado = proyecto_manager.marcar_como_ordenado(
        gasto_id,
        numero_orden=f'ORD-{datetime.now().strftime("%Y%m%d%H%M")}',
        fecha_orden=date.today().isoformat()
    )

    if resultado_ordenado.get('success'):
        print_result(True, "Gasto marcado como ordenado")
    else:
        print_result(False, f"Error marcando como ordenado: {resultado_ordenado.get('message')}")

    # Test 7: Marcar como recibido
    print("\n7. Marcar gasto como recibido:")
    resultado_recibido = proyecto_manager.marcar_como_recibido(gasto_id)

    if resultado_recibido.get('success'):
        print_result(True, "Gasto marcado como recibido")
    else:
        print_result(False, f"Error marcando como recibido: {resultado_recibido.get('message')}")

    # Test 8: Obtener gastos pendientes de aprobación
    print("\n8. Obtener gastos pendientes de aprobación:")
    pendientes = proyecto_manager.obtener_gastos_pendientes_aprobacion()

    if pendientes is not None:
        print_result(True, f"Se encontraron {len(pendientes)} gasto(s) pendiente(s)")
    else:
        print_result(False, "Error obteniendo gastos pendientes")

    # Test 9: Validación de presupuesto
    print("\n9. Validar límite de presupuesto:")
    gasto_excesivo = {
        'proyecto_id': proyecto_id,
        'concepto': 'Gasto que excede presupuesto',
        'proveedor': 'Test',
        'cantidad': 1.0,
        'unidad': 'pieza',
        'precio_unitario': 999999.00,  # Monto muy alto
        'notas': 'Test de validación'
    }

    resultado_validacion = proyecto_manager.crear_gasto(gasto_excesivo)

    if not resultado_validacion.get('success') and 'presupuesto' in resultado_validacion.get('message', '').lower():
        print_result(True, "Validación de presupuesto funciona correctamente")
    else:
        print_result(False, "Validación de presupuesto no funcionó como esperado")

    print_result(True, "ProyectoManager: Todas las pruebas completadas")
    return {'gasto_id': gasto_id, 'gastos_ids': gastos_ids}

def test_notificaciones_manager():
    """Test de NotificacionesManager - Sistema de Notificaciones"""
    print_separator("TEST 3: NotificacionesManager - Notificaciones")

    try:
        notif_manager = NotificacionesManager()
        print_result(True, "NotificacionesManager inicializado correctamente")
    except Exception as e:
        print_result(False, f"Error inicializando NotificacionesManager: {e}")
        return False

    usuario_test = 'test_user'

    # Test 1: Crear notificación de gasto pendiente
    print("\n1. Crear notificación de gasto pendiente:")
    gasto_info_test = {
        'concepto': 'Rack Metálico TEST',
        'monto': 42500.00,
        'proyecto_nombre': 'Proyecto TEST'
    }

    resultado_notif = notif_manager.notificar_gasto_pendiente(
        gasto_id=999,
        gasto_info=gasto_info_test,
        aprobador=usuario_test
    )

    if resultado_notif.get('success'):
        print_result(True, "Notificación de gasto pendiente creada")
    else:
        print_result(False, f"Error creando notificación: {resultado_notif.get('message')}")

    # Test 2: Crear notificación de gasto aprobado
    print("\n2. Crear notificación de gasto aprobado:")
    resultado_aprobado = notif_manager.notificar_gasto_aprobado(
        gasto_id=999,
        gasto_info=gasto_info_test,
        aprobador='admin',
        solicitante=usuario_test
    )

    if resultado_aprobado.get('success'):
        print_result(True, "Notificación de gasto aprobado creada")
    else:
        print_result(False, f"Error creando notificación: {resultado_aprobado.get('message')}")

    # Test 3: Contar notificaciones no leídas
    print("\n3. Contar notificaciones no leídas:")
    contador = notif_manager.contar_no_leidas(usuario_test)

    if contador >= 0:
        print_result(True, f"Notificaciones no leídas: {contador}")
    else:
        print_result(False, "Error contando notificaciones")

    # Test 4: Obtener notificaciones del usuario
    print("\n4. Obtener notificaciones del usuario:")
    notificaciones = notif_manager.obtener_notificaciones_usuario(usuario_test, limite=10)

    if notificaciones:
        print_result(True, f"Se encontraron {len(notificaciones)} notificación(es)")
        for notif in notificaciones[:3]:  # Mostrar solo las primeras 3
            leida = "✓ Leída" if notif.get('leida') else "● Nueva"
            print(f"   {leida} | {notif.get('tipo')} | {notif.get('titulo')}")
    else:
        print_result(True, "No hay notificaciones (normal en primera ejecución)")

    # Test 5: Marcar notificación como leída
    if notificaciones:
        print("\n5. Marcar primera notificación como leída:")
        notif_id = notificaciones[0].get('id')
        resultado_marcar = notif_manager.marcar_como_leida(notif_id)

        if resultado_marcar.get('success'):
            print_result(True, "Notificación marcada como leída")
        else:
            print_result(False, f"Error marcando como leída: {resultado_marcar.get('message')}")

        # Test 6: Verificar contador después de marcar como leída
        print("\n6. Verificar contador después de marcar como leída:")
        nuevo_contador = notif_manager.contar_no_leidas(usuario_test)

        if nuevo_contador < contador:
            print_result(True, f"Contador actualizado correctamente: {contador} → {nuevo_contador}")
        else:
            print_result(False, "Contador no se actualizó correctamente")

    # Test 7: Marcar todas como leídas
    print("\n7. Marcar todas las notificaciones como leídas:")
    resultado_todas = notif_manager.marcar_todas_leidas(usuario_test)

    if resultado_todas.get('success'):
        print_result(True, f"Todas marcadas como leídas: {resultado_todas.get('actualizadas', 0)} notificación(es)")
    else:
        print_result(False, f"Error marcando todas como leídas: {resultado_todas.get('message')}")

    # Test 8: Verificar que el contador es 0
    print("\n8. Verificar contador después de marcar todas:")
    contador_final = notif_manager.contar_no_leidas(usuario_test)

    if contador_final == 0:
        print_result(True, "Contador en 0 como se esperaba")
    else:
        print_result(False, f"Contador debería ser 0 pero es {contador_final}")

    print_result(True, "NotificacionesManager: Todas las pruebas completadas")
    return True

def test_integracion_completa():
    """Test de integración: Flujo completo desde OC hasta notificaciones"""
    print_separator("TEST 4: Integración Completa - Flujo End-to-End")

    print("""
    Este test simula el flujo completo:
    1. Cliente envía OC → Sistema crea proyecto automáticamente
    2. Se agregan gastos al proyecto
    3. Los gastos se aprueban
    4. Se marcan como ordenados
    5. Se marcan como recibidos
    6. Se envían notificaciones en cada paso
    """)

    # Ejecutar flujo completo
    resultado_oc = test_oc_manager()

    if not resultado_oc:
        print_result(False, "Flujo interrumpido: Error en OCManager")
        return False

    proyecto_id = resultado_oc.get('proyecto_id')

    resultado_proyecto = test_proyecto_manager(proyecto_id)

    if not resultado_proyecto:
        print_result(False, "Flujo interrumpido: Error en ProyectoManager")
        return False

    resultado_notif = test_notificaciones_manager()

    if not resultado_notif:
        print_result(False, "Flujo interrumpido: Error en NotificacionesManager")
        return False

    print_result(True, "Integración completa: Todos los componentes funcionan correctamente")
    return True

def main():
    """Función principal que ejecuta todos los tests"""
    print("\n" + "=" * 70)
    print("  TEST COMPLETO: MÓDULO DE PROYECTOS Y ÓRDENES DE COMPRA")
    print("=" * 70)
    print(f"\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Pruebas a ejecutar:")
    print("  1. OCManager - Gestión de Órdenes de Compra")
    print("  2. ProyectoManager - Gestión de Gastos")
    print("  3. NotificacionesManager - Sistema de Notificaciones")
    print("  4. Integración Completa - Flujo End-to-End")

    try:
        # Ejecutar test de integración completa
        exito = test_integracion_completa()

        print("\n" + "=" * 70)
        if exito:
            print("  ✓✓✓ TODOS LOS TESTS COMPLETADOS EXITOSAMENTE ✓✓✓")
        else:
            print("  ✗✗✗ ALGUNOS TESTS FALLARON ✗✗✗")
        print("=" * 70 + "\n")

        return exito

    except Exception as e:
        print_result(False, f"Error crítico durante los tests: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
