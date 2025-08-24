#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CWS COTIZADOR - APLICACIÓN PRINCIPAL UNIFICADA
==============================================

Versión mejorada con sistema de almacenamiento unificado que integra:
- Supabase PostgreSQL (principal)
- Cloudinary (PDFs con CDN)  
- Google Drive (PDFs antiguos del admin)
- Sistema offline con sincronización automática
- Monitoreo de salud en tiempo real
- Búsqueda unificada multi-fuente
- Auto-recuperación y alta disponibilidad

Versión: 3.0.0 - Sistema Unificado
Fecha: 2025-08-19
"""

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import io
import datetime
import atexit
import os
import json
import csv
import logging
import time
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, List, Optional, Any

# Importar sistemas unificados
from unified_storage_manager import UnifiedStorageManager, get_unified_manager
from unified_search_system import UnifiedSearchSystem, SearchFilter, SearchResultType
from enhanced_sync_system import EnhancedSyncSystem
from google_drive_monitor import GoogleDriveMonitor
from health_monitoring_system import HealthMonitoringSystem

# Importar generadores de PDF
WEASYPRINT_AVAILABLE = False
REPORTLAB_AVAILABLE = False

try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
    print("✅ WeasyPrint disponible")
except ImportError:
    print("⚠️ WeasyPrint no disponible")

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.graphics.shapes import Drawing, Line
    REPORTLAB_AVAILABLE = True
    print("✅ ReportLab disponible")
except ImportError:
    print("⚠️ ReportLab no disponible")

if not WEASYPRINT_AVAILABLE and not REPORTLAB_AVAILABLE:
    print("❌ ADVERTENCIA: Ningún generador de PDF disponible")

def configurar_logging_avanzado():
    """Configurar sistema de logging avanzado"""
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Logger principal de la aplicación
    main_log = log_dir / 'app_unified.log'
    main_handler = RotatingFileHandler(
        main_log, maxBytes=10*1024*1024, backupCount=5
    )
    
    # Logger de errores críticos
    critical_log = log_dir / 'errores_criticos.log'
    critical_handler = RotatingFileHandler(
        critical_log, maxBytes=5*1024*1024, backupCount=3
    )
    
    # Logger de métricas de performance
    performance_log = log_dir / 'performance_metrics.log'
    performance_handler = RotatingFileHandler(
        performance_log, maxBytes=10*1024*1024, backupCount=3
    )
    
    # Formato de logs
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
    )
    
    # Configurar handlers
    main_handler.setFormatter(formatter)
    critical_handler.setFormatter(formatter)
    performance_handler.setFormatter(formatter)
    
    # Logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(main_handler)
    
    # Logger crítico
    critical_logger = logging.getLogger('CRITICAL')
    critical_logger.addHandler(critical_handler)
    critical_logger.setLevel(logging.ERROR)
    
    # Logger de performance
    perf_logger = logging.getLogger('PERFORMANCE')
    perf_logger.addHandler(performance_handler)
    perf_logger.setLevel(logging.INFO)
    
    print(f"✅ [LOGGING] Sistema avanzado configurado")
    print(f"   📊 Principal: {main_log}")
    print(f"   🚨 Críticos: {critical_log}")
    print(f"   ⚡ Performance: {performance_log}")
    
    return root_logger

# Configurar logging
configurar_logging_avanzado()
logger = logging.getLogger(__name__)
critical_logger = logging.getLogger('CRITICAL')
perf_logger = logging.getLogger('PERFORMANCE')

# Cargar variables de entorno
load_dotenv()

# Crear aplicación Flask
app = Flask(__name__)

# Configuración de la aplicación
app.config.update({
    'SECRET_KEY': os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
    'DEBUG': os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
    'MAX_CONTENT_LENGTH': int(os.getenv('MAX_UPLOAD_SIZE', '50')) * 1024 * 1024,  # MB a bytes
    'PERMANENT_SESSION_LIFETIME': int(os.getenv('SESSION_LIFETIME_MINUTES', '60')) * 60
})

# Variables globales para sistemas unificados
storage_manager: UnifiedStorageManager = None
search_system: UnifiedSearchSystem = None
sync_system: EnhancedSyncSystem = None
drive_monitor: GoogleDriveMonitor = None
health_system: HealthMonitoringSystem = None

# Cache de materiales
materiales_cache = []
materiales_cache_time = None

def inicializar_sistemas():
    """Inicializar todos los sistemas unificados"""
    global storage_manager, search_system, sync_system, drive_monitor, health_system
    
    try:
        logger.info("🚀 [INIT] Inicializando sistemas unificados...")
        
        # 1. Storage Manager (base de todo)
        storage_manager = get_unified_manager()
        logger.info("✅ [INIT] Storage Manager inicializado")
        
        # 2. Search System
        search_system = UnifiedSearchSystem(storage_manager)
        logger.info("✅ [INIT] Sistema de búsqueda inicializado")
        
        # 3. Sync System  
        sync_system = EnhancedSyncSystem(storage_manager)
        sync_system.start_sync_system()
        logger.info("✅ [INIT] Sistema de sincronización iniciado")
        
        # 4. Drive Monitor (para PDFs del admin)
        drive_monitor = GoogleDriveMonitor(storage_manager)
        if storage_manager.google_drive.is_available():
            drive_monitor.start_monitoring()
            logger.info("✅ [INIT] Monitor de Google Drive iniciado")
        else:
            logger.warning("⚠️ [INIT] Google Drive no disponible")
        
        # 5. Health System (monitoreo)
        health_system = HealthMonitoringSystem(storage_manager)
        health_system.start_monitoring()
        logger.info("✅ [INIT] Sistema de salud iniciado")
        
        logger.info("🎉 [INIT] Todos los sistemas inicializados correctamente")
        
    except Exception as e:
        critical_logger.error(f"❌ [INIT] Error crítico inicializando sistemas: {e}")
        raise

def cargar_lista_materiales():
    """Cargar lista de materiales desde CSV con cache"""
    global materiales_cache, materiales_cache_time
    
    # Verificar cache (válido por 1 hora)
    if (materiales_cache and materiales_cache_time and 
        (datetime.datetime.now() - materiales_cache_time).seconds < 3600):
        return materiales_cache
    
    try:
        ruta_csv = Path(__file__).parent / "Lista de materiales.csv"
        
        if not ruta_csv.exists():
            logger.warning(f"⚠️ [MATERIALES] Archivo no encontrado: {ruta_csv}")
            return []
        
        materiales = []
        with open(ruta_csv, 'r', encoding='utf-8-sig', newline='') as archivo_csv:
            reader = csv.DictReader(archivo_csv)
            
            for fila in reader:
                if fila.get('Material') and fila.get('Material').strip():
                    material = {
                        'nombre': fila.get('Material', '').strip(),
                        'precio': fila.get('Precio', '0'),
                        'unidad': fila.get('Unidad', 'unidad'),
                        'categoria': fila.get('Categoria', 'General')
                    }
                    materiales.append(material)
        
        # Actualizar cache
        materiales_cache = materiales
        materiales_cache_time = datetime.datetime.now()
        
        logger.info(f"✅ [MATERIALES] {len(materiales)} materiales cargados")
        return materiales
        
    except Exception as e:
        logger.error(f"❌ [MATERIALES] Error cargando materiales: {e}")
        return []

def generar_pdf_reportlab(datos_cotizacion):
    """Generar PDF profesional usando ReportLab"""
    if not REPORTLAB_AVAILABLE:
        raise Exception("ReportLab no disponible")
    
    logger.info(f"📄 [PDF] Generando PDF con ReportLab para: {datos_cotizacion.get('numeroCotizacion', 'Sin número')}")
    
    # Crear buffer en memoria
    buffer = io.BytesIO()
    
    # Configurar documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Centrado
    )
    
    # Construir contenido
    story = []
    
    # Título principal
    story.append(Paragraph("COTIZACIÓN CWS", title_style))
    story.append(Spacer(1, 20))
    
    # Información general
    datos_generales = datos_cotizacion.get('datosGenerales', {})
    
    info_data = [
        ['Número de Cotización:', datos_cotizacion.get('numeroCotizacion', 'N/A')],
        ['Cliente:', datos_generales.get('cliente', 'N/A')],
        ['Vendedor:', datos_generales.get('vendedor', 'N/A')],
        ['Proyecto:', datos_generales.get('proyecto', 'N/A')],
        ['Fecha:', datos_generales.get('fecha', datetime.datetime.now().strftime('%Y-%m-%d'))],
        ['Revisión:', f"R{datos_cotizacion.get('revision', 1)}"]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 30))
    
    # Tabla de items
    items = datos_cotizacion.get('items', [])
    if items:
        story.append(Paragraph("DESGLOSE DE MATERIALES", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        # Encabezados de tabla
        items_data = [['Material', 'Cantidad', 'Precio Unit.', 'Subtotal']]
        
        total = 0
        for item in items:
            cantidad = float(item.get('cantidad', 0))
            precio = float(item.get('precio', 0))
            subtotal = cantidad * precio
            total += subtotal
            
            items_data.append([
                item.get('material', 'N/A'),
                str(cantidad),
                f"${precio:,.2f}",
                f"${subtotal:,.2f}"
            ])
        
        # Agregar total
        items_data.append(['', '', 'TOTAL:', f"${total:,.2f}"])
        
        items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
        ]))
        
        story.append(items_table)
    
    # Observaciones
    observaciones = datos_cotizacion.get('observaciones', '')
    if observaciones:
        story.append(Spacer(1, 30))
        story.append(Paragraph("OBSERVACIONES", styles['Heading2']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(observaciones, styles['Normal']))
    
    # Generar PDF
    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    
    logger.info(f"✅ [PDF] PDF generado exitosamente ({len(pdf_data)} bytes)")
    return pdf_data

# Inicializar sistemas al arrancar
try:
    inicializar_sistemas()
except Exception as e:
    critical_logger.error(f"❌ Error crítico al inicializar: {e}")
    print(f"❌ Error crítico: {e}")
    print("La aplicación se iniciará en modo degradado")

# ===== RUTAS DE LA APLICACIÓN =====

@app.route('/')
def home():
    """Página principal con dashboard mejorado"""
    try:
        start_time = time.time()
        
        # Obtener estadísticas del sistema
        system_status = storage_manager.get_system_status() if storage_manager else {"error": "Sistema no inicializado"}
        health_summary = health_system.get_system_health_summary() if health_system else {"error": "Monitoreo no disponible"}
        
        # Obtener últimas cotizaciones
        recent_quotes = []
        if search_system:
            try:
                recent_result = search_system.buscar("", page=1, per_page=5)
                recent_quotes = recent_result.resultados
            except Exception as e:
                logger.error(f"Error obteniendo cotizaciones recientes: {e}")
        
        # Métricas de performance
        response_time = int((time.time() - start_time) * 1000)
        perf_logger.info(f"Home page rendered in {response_time}ms")
        
        return render_template('home_unified.html',
            system_status=system_status,
            health_summary=health_summary,
            recent_quotes=recent_quotes,
            page_load_time=response_time
        )
        
    except Exception as e:
        critical_logger.error(f"Error crítico en home: {e}")
        return render_template('error.html', error="Error cargando página principal"), 500

@app.route('/formulario')
def formulario():
    """Formulario de cotización mejorado"""
    try:
        # Cargar materiales
        materiales = cargar_lista_materiales()
        
        # Obtener estado de sistemas
        systems_status = {
            'storage': storage_manager.get_system_status() if storage_manager else {"error": "No disponible"},
            'search': search_system.get_system_stats() if search_system else {"error": "No disponible"},
            'health': health_system.get_system_health_summary() if health_system else {"error": "No disponible"}
        }
        
        return render_template('formulario_unified.html', 
            materiales=materiales,
            systems_status=systems_status
        )
        
    except Exception as e:
        logger.error(f"Error cargando formulario: {e}")
        return render_template('error.html', error="Error cargando formulario"), 500

@app.route('/cotizar', methods=['POST'])
def cotizar():
    """Procesar cotización con sistema unificado"""
    start_time = time.time()
    
    try:
        logger.info("📋 [COTIZAR] Iniciando proceso de cotización...")
        
        # Obtener datos del formulario
        datos_formulario = request.get_json()
        
        if not datos_formulario:
            return jsonify({
                "success": False,
                "error": "No se recibieron datos del formulario"
            }), 400
        
        # Validar datos obligatorios
        datos_generales = datos_formulario.get('datosGenerales', {})
        cliente = datos_generales.get('cliente', '').strip()
        vendedor = datos_generales.get('vendedor', '').strip()
        proyecto = datos_generales.get('proyecto', '').strip()
        
        if not cliente or not vendedor or not proyecto:
            return jsonify({
                "success": False,
                "error": "Campos obligatorios: Cliente, Vendedor y Proyecto"
            }), 400
        
        # Generar número automático si no existe
        if not datos_generales.get('numeroCotizacion'):
            if storage_manager and hasattr(storage_manager.supabase, 'generar_numero_automatico'):
                numero_generado = storage_manager.supabase.generar_numero_automatico(datos_generales)
                datos_formulario['numeroCotizacion'] = numero_generado
                datos_formulario['datosGenerales']['numeroCotizacion'] = numero_generado
                logger.info(f"📋 [COTIZAR] Número generado: {numero_generado}")
            else:
                # Fallback
                timestamp = int(time.time())
                numero_generado = f"CWS-{timestamp}-R1"
                datos_formulario['numeroCotizacion'] = numero_generado
                datos_formulario['datosGenerales']['numeroCotizacion'] = numero_generado
        
        # Guardar cotización usando sistema unificado
        logger.info("💾 [COTIZAR] Guardando cotización...")
        save_result = storage_manager.guardar_cotizacion(datos_formulario)
        
        if not save_result.success:
            critical_logger.error(f"Error guardando cotización: {save_result.error}")
            return jsonify({
                "success": False,
                "error": f"Error guardando cotización: {save_result.error}"
            }), 500
        
        # Generar PDF
        pdf_data = None
        pdf_result = None
        
        try:
            logger.info("📄 [COTIZAR] Generando PDF...")
            pdf_data = generar_pdf_reportlab(datos_formulario)
            
            if pdf_data:
                # Almacenar PDF usando sistema híbrido
                pdf_result = storage_manager.guardar_pdf(pdf_data, datos_formulario)
                
                if pdf_result.success:
                    logger.info("✅ [COTIZAR] PDF almacenado exitosamente")
                else:
                    logger.error(f"Error almacenando PDF: {pdf_result.error}")
                    
        except Exception as pdf_error:
            logger.error(f"Error generando/almacenando PDF: {pdf_error}")
            # No fallar la cotización por errores de PDF
        
        # Registrar métricas de performance
        response_time = int((time.time() - start_time) * 1000)
        perf_logger.info(f"Cotización procesada en {response_time}ms")
        
        # Respuesta exitosa
        response_data = {
            "success": True,
            "message": "Cotización creada exitosamente",
            "numeroCotizacion": datos_formulario.get('numeroCotizacion'),
            "storage_result": save_result.data,
            "pdf_result": pdf_result.data if pdf_result else None,
            "processing_time_ms": response_time,
            "systems_used": {
                "storage": save_result.source,
                "pdf": pdf_result.source if pdf_result else None
            }
        }
        
        logger.info(f"✅ [COTIZAR] Cotización completada: {datos_formulario.get('numeroCotizacion')}")
        return jsonify(response_data)
        
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        critical_logger.error(f"Error crítico en cotizar: {e}")
        
        return jsonify({
            "success": False,
            "error": f"Error interno del servidor: {str(e)}",
            "processing_time_ms": response_time
        }), 500

@app.route('/buscar')
def buscar():
    """Búsqueda unificada mejorada"""
    try:
        start_time = time.time()
        
        # Parámetros de búsqueda
        query = request.args.get('q', '').strip()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Filtros avanzados
        filters = SearchFilter(
            cliente=request.args.get('cliente'),
            vendedor=request.args.get('vendedor'),
            proyecto=request.args.get('proyecto'),
            tipo_resultado=SearchResultType(request.args.get('tipo')) if request.args.get('tipo') else None,
            solo_con_desglose=request.args.get('desglose') == 'true' if request.args.get('desglose') else None
        )
        
        # Realizar búsqueda
        if search_system:
            result = search_system.buscar(query, page, per_page, filters)
            
            # Métricas
            response_time = int((time.time() - start_time) * 1000)
            perf_logger.info(f"Búsqueda '{query}' completada en {response_time}ms")
            
            return jsonify({
                "success": True,
                "query": query,
                "resultados": [asdict(r) for r in result.resultados],
                "total": result.total,
                "page": result.page,
                "per_page": result.per_page,
                "total_pages": result.total_pages,
                "fuentes_consultadas": [s.value for s in result.fuentes_consultadas],
                "tiempo_busqueda_ms": result.tiempo_busqueda_ms,
                "from_cache": result.from_cache,
                "estadisticas": result.estadisticas
            })
        else:
            return jsonify({
                "success": False,
                "error": "Sistema de búsqueda no disponible"
            }), 503
            
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        return jsonify({
            "success": False,
            "error": f"Error en búsqueda: {str(e)}"
        }), 500

@app.route('/cotizacion/<numero_cotizacion>')
def ver_cotizacion(numero_cotizacion):
    """Ver cotización específica"""
    try:
        if search_system:
            # Buscar por número exacto (optimizado)
            result = search_system.buscar_por_numero_exacto(numero_cotizacion)
            
            if result:
                return render_template('ver_cotizacion_unified.html', 
                    cotizacion=asdict(result),
                    numero=numero_cotizacion
                )
            else:
                return render_template('error.html', 
                    error=f"Cotización '{numero_cotizacion}' no encontrada"
                ), 404
        else:
            return render_template('error.html', 
                error="Sistema de búsqueda no disponible"
            ), 503
            
    except Exception as e:
        logger.error(f"Error viendo cotización {numero_cotizacion}: {e}")
        return render_template('error.html', 
            error="Error cargando cotización"
        ), 500

# ===== RUTAS DE ADMINISTRACIÓN Y MONITOREO =====

@app.route('/admin/dashboard')
def admin_dashboard():
    """Dashboard administrativo con métricas en tiempo real"""
    try:
        if not storage_manager:
            return jsonify({"error": "Sistema no inicializado"}), 503
        
        dashboard_data = {
            "system_status": storage_manager.get_system_status(),
            "health_summary": health_system.get_system_health_summary() if health_system else {},
            "search_stats": search_system.get_system_stats() if search_system else {},
            "sync_status": sync_system.get_sync_status() if sync_system else {},
            "drive_monitor": drive_monitor.get_monitor_status() if drive_monitor else {},
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        logger.error(f"Error en dashboard admin: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/health/check', methods=['POST'])
def force_health_check():
    """Forzar verificación de salud"""
    try:
        if health_system:
            result = health_system.force_health_check()
            return jsonify(result)
        else:
            return jsonify({"error": "Sistema de salud no disponible"}), 503
            
    except Exception as e:
        logger.error(f"Error en verificación forzada: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/integrity/check', methods=['POST'])
def force_integrity_check():
    """Forzar verificación de integridad"""
    try:
        if health_system:
            report = health_system.force_integrity_check()
            return jsonify(asdict(report))
        else:
            return jsonify({"error": "Sistema de integridad no disponible"}), 503
            
    except Exception as e:
        logger.error(f"Error en verificación de integridad: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/sync/manual', methods=['POST'])
def manual_sync():
    """Sincronización manual"""
    try:
        if sync_system:
            result = sync_system.process_sync_queue()
            return jsonify({
                "success": True,
                "result": result,
                "timestamp": datetime.datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "Sistema de sincronización no disponible"}), 503
            
    except Exception as e:
        logger.error(f"Error en sincronización manual: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/cache/clear', methods=['POST'])
def clear_caches():
    """Limpiar todos los caches"""
    try:
        if search_system:
            search_system.clear_cache()
        
        # Limpiar cache de materiales
        global materiales_cache, materiales_cache_time
        materiales_cache = []
        materiales_cache_time = None
        
        return jsonify({
            "success": True,
            "message": "Caches limpiados",
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error limpiando caches: {e}")
        return jsonify({"error": str(e)}), 500

# ===== MANEJO DE ERRORES GLOBALES =====

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    critical_logger.error(f"Error 500: {error}")
    return render_template('error.html', error="Error interno del servidor"), 500

@app.errorhandler(503)
def service_unavailable_error(error):
    return render_template('error.html', error="Servicio temporalmente no disponible"), 503

# ===== LIMPIEZA AL CERRAR =====

def cleanup():
    """Limpiar recursos al cerrar la aplicación"""
    logger.info("🔌 [CLEANUP] Cerrando aplicación...")
    
    try:
        if health_system:
            health_system.stop_monitoring()
        
        if sync_system:
            sync_system.stop_sync_system()
            
        if drive_monitor:
            drive_monitor.stop_monitoring()
            
        if storage_manager:
            storage_manager.shutdown()
            
        logger.info("✅ [CLEANUP] Aplicación cerrada correctamente")
        
    except Exception as e:
        critical_logger.error(f"Error durante cleanup: {e}")

atexit.register(cleanup)

# ===== TEMPLATES BÁSICOS (crear si no existen) =====

def crear_templates_basicos():
    """Crear templates HTML básicos si no existen"""
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    # Template de error básico
    error_template = templates_dir / 'error.html'
    if not error_template.exists():
        error_template.write_text('''
<!DOCTYPE html>
<html>
<head>
    <title>Error - CWS Cotizador</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>Error</h1>
    <p>{{ error }}</p>
    <a href="/">Volver al inicio</a>
</body>
</html>
        '''.strip())
        logger.info("✅ Template de error creado")

# Crear templates básicos
crear_templates_basicos()

if __name__ == '__main__':
    """Ejecutar aplicación"""
    logger.info("🚀 [START] Iniciando CWS Cotizador Unificado v3.0.0...")
    
    # Configuración de servidor
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🌐 [SERVER] Servidor iniciando en {host}:{port}")
    logger.info(f"🔧 [SERVER] Modo debug: {'Habilitado' if debug else 'Deshabilitado'}")
    
    # Ejecutar aplicación
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )