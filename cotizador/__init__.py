"""
CWS Cotizador - Aplicación Flask modularizada.
Factory pattern para inicializar la app con todos sus componentes.
"""
import os
import sys
import datetime
import atexit
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from flask import Flask, jsonify

# Compatibilidad de librerías PDF
from cotizador._compat import REPORTLAB_AVAILABLE, WEASYPRINT_AVAILABLE

# Utilidades compartidas
from cotizador.utilities import (
    safe_float, safe_int, validate_material_data,
    wrap_description_text, is_json_request,
    handle_error_response, handle_not_found_response
)
from cotizador.pdf_generator import generar_pdf_reportlab, generar_desglose_pdf_reportlab


def configurar_logging(app_instance=None):
    """Configura logging detallado para la aplicación."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    log_dir = os.path.join(base_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'cotizador_fallos_criticos.log')

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    critical_logger = logging.getLogger('FALLOS_CRITICOS')
    critical_handler = RotatingFileHandler(
        os.path.join(log_dir, 'fallos_silenciosos_detectados.log'),
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )
    critical_handler.setFormatter(formatter)
    critical_logger.addHandler(critical_handler)
    critical_logger.setLevel(logging.ERROR)

    print(f"Logging configurado: {log_file}")
    return logger


def cargar_materiales_csv():
    """Carga la lista de materiales desde el archivo CSV."""
    import csv

    materiales = []
    es_render = os.getenv('RENDER') or os.getenv('RENDER_SERVICE_NAME')
    print(f"[MATERIALES] Entorno Render detectado: {bool(es_render)}")

    base_dir = os.path.dirname(os.path.dirname(__file__))

    try:
        rutas_posibles = [
            os.path.join(base_dir, 'Lista de materiales.csv'),
            os.path.join(os.getcwd(), 'Lista de materiales.csv'),
            './Lista de materiales.csv',
            'Lista de materiales.csv'
        ]

        archivo_encontrado = None
        for ruta_csv in rutas_posibles:
            if os.path.exists(ruta_csv):
                archivo_encontrado = ruta_csv
                print(f"[MATERIALES] Archivo CSV encontrado en: {ruta_csv}")
                break

        if not archivo_encontrado:
            raise FileNotFoundError("No se encontró el archivo 'Lista de materiales.csv'")

        with open(archivo_encontrado, 'r', encoding='utf-8-sig') as archivo:
            reader = csv.DictReader(archivo)
            headers = reader.fieldnames

            for i, fila in enumerate(reader):
                try:
                    headers_limpios = {k.strip() if k else f'col_{i}': v for k, v in fila.items()}
                    descripcion = (
                        headers_limpios.get('Tipo de material') or
                        headers_limpios.get('tipo_material') or
                        headers_limpios.get('material') or
                        headers_limpios.get('descripcion') or
                        f'Material {i+1}'
                    )
                    peso_str = (
                        headers_limpios.get('Peso') or
                        headers_limpios.get('peso') or
                        headers_limpios.get('weight') or
                        '1.0'
                    )
                    uom = (
                        headers_limpios.get('Ref de Peso') or
                        headers_limpios.get('uom') or
                        headers_limpios.get('unidad') or
                        'kg/m2'
                    )
                    try:
                        peso = float(str(peso_str).replace(',', '.'))
                    except (ValueError, TypeError):
                        peso = 1.0

                    material = {
                        'descripcion': str(descripcion).strip(),
                        'peso': peso,
                        'uom': str(uom).strip()
                    }
                    materiales.append(material)
                except Exception as fila_error:
                    print(f"[MATERIALES] Error procesando fila {i+1}: {fila_error}")
                    continue

        print(f"[MATERIALES] Cargados {len(materiales)} materiales desde CSV")
        if materiales:
            print(f"[MATERIALES] Ejemplos cargados:")
            for i, mat in enumerate(materiales[:3]):
                print(f"  {i+1}. {mat['descripcion']} - {mat['peso']} {mat['uom']}")

    except Exception as e:
        print(f"[MATERIALES] Error cargando materiales: {e}")
        materiales = [
            {'descripcion': 'Acero estructural', 'peso': 7850.0, 'uom': 'kg/m3'},
            {'descripcion': 'Concreto armado', 'peso': 2400.0, 'uom': 'kg/m3'},
            {'descripcion': 'Lamina galvanizada', 'peso': 7.85, 'uom': 'kg/m2'},
            {'descripcion': 'Perfil IPR', 'peso': 1.0, 'uom': 'kg/ml'},
            {'descripcion': 'Tubo estructural', 'peso': 1.0, 'uom': 'kg/ml'},
            {'descripcion': 'Material personalizado', 'peso': 1.0, 'uom': 'Especificar'}
        ]
        print(f"[MATERIALES] Usando {len(materiales)} materiales por defecto")

    return materiales


def create_app():
    """Factory: crea y configura la aplicación Flask."""
    load_dotenv()

    # Configurar logging
    configurar_logging()

    # Determinar paths para templates y static
    base_dir = os.path.dirname(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')

    # Crear app Flask
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # ── Inicializar DatabaseManager ──
    print("Inicializando DatabaseManager (SupabaseManager)...")
    from supabase_manager import SupabaseManager as DatabaseManager
    db_manager = DatabaseManager()

    print(f"Estado de conexión:")
    print(f"   Modo offline: {db_manager.modo_offline}")
    if not db_manager.modo_offline:
        print(f"   Supabase conectado: {db_manager.supabase_url}")
        print(f"   Base de datos: PostgreSQL")
    else:
        print(f"   Modo offline activo - usando JSON local")

    # Estadísticas iniciales
    try:
        stats = db_manager.obtener_estadisticas()
        print(f"Estadísticas iniciales:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")

    # ── Inicializar PDFManager ──
    try:
        from pdf_manager import PDFManager
        pdf_manager = PDFManager(db_manager)
        print("PDFManager inicializado exitosamente")
    except Exception as e:
        print(f"Error inicializando PDFManager: {e}")
        pdf_manager = None

    # ── Inicializar SyncScheduler ──
    try:
        from sync_scheduler import SyncScheduler
        sync_scheduler = SyncScheduler(db_manager)
        print("SyncScheduler inicializado exitosamente")
        if sync_scheduler.auto_sync_enabled and sync_scheduler.is_available():
            sync_scheduler.iniciar()
    except Exception as e:
        print(f"Error inicializando SyncScheduler: {e}")
        sync_scheduler = None

    # ── Cargar materiales ──
    LISTA_MATERIALES = cargar_materiales_csv()
    print(f"[OK] Cargados {len(LISTA_MATERIALES)} materiales desde CSV")

    # ── Guardar en extensions/config para acceso desde blueprints ──
    app.extensions['db_manager'] = db_manager
    app.extensions['pdf_manager'] = pdf_manager
    app.extensions['sync_scheduler'] = sync_scheduler
    app.config['LISTA_MATERIALES'] = LISTA_MATERIALES
    # Backward compat: también expuestos como config
    app.config['DB_MANAGER'] = db_manager
    app.config['PDF_MANAGER'] = pdf_manager
    app.config['SYNC_SCHEDULER'] = sync_scheduler

    # ── Template filter ──
    @app.template_filter('timestamp_to_date')
    def timestamp_to_date(timestamp):
        try:
            if isinstance(timestamp, str):
                return datetime.datetime.fromisoformat(
                    timestamp.replace('Z', '+00:00')
                ).strftime('%d/%m/%Y %H:%M')
            elif isinstance(timestamp, (int, float)):
                return datetime.datetime.fromtimestamp(
                    timestamp / 1000
                ).strftime('%d/%m/%Y %H:%M')
            else:
                return 'N/A'
        except Exception:
            return 'N/A'

    # ── Registrar blueprints ──
    from cotizador.blueprints.auth_bp import auth_bp
    app.register_blueprint(auth_bp)

    from cotizador.blueprints.company_bp import company_bp
    app.register_blueprint(company_bp)

    # ── Inicializar middleware multi-tenant ──
    from cotizador.middleware import init_middleware
    init_middleware(app, db_manager)

    # ── Error handlers ──
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Ruta no encontrada"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Error interno del servidor"}), 500

    # ── Health check ──
    @app.route("/health")
    def health():
        stats = db_manager.obtener_estadisticas()
        return jsonify({
            "status": "ok",
            "app": os.getenv('APP_NAME', 'CWS Cotizaciones'),
            "version": os.getenv('APP_VERSION', '1.0.0'),
            "modo": "offline" if db_manager.modo_offline else "online",
            **stats
        })

    return app
