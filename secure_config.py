"""
CONFIGURACIÓN DE SEGURIDAD REFORZADA PARA CWS
Reemplaza config.py con medidas de seguridad mejoradas
"""

import os
import secrets
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class SecureConfig:
    """Configuración base con seguridad reforzada"""
    
    # Generar SECRET_KEY segura si no existe
    @staticmethod
    def generate_secure_key():
        """Genera una clave secreta criptográficamente segura"""
        return secrets.token_urlsafe(32)
    
    # Flask - Configuración segura
    SECRET_KEY = os.environ.get('SECRET_KEY') or generate_secure_key()
    DEBUG = False  # Por defecto siempre False en producción
    
    # Configuración de seguridad Flask
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora
    
    # Validar que SECRET_KEY no sea la por defecto
    if SECRET_KEY == 'dev-secret-key-change-in-production':
        logging.critical("USANDO SECRET_KEY POR DEFECTO - CAMBIE INMEDIATAMENTE")
        raise ValueError("SECRET_KEY insegura detectada")
    
    # MongoDB - Configuración segura
    MONGO_USERNAME = os.environ.get('MONGO_USERNAME')
    MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD')
    MONGO_CLUSTER = os.environ.get('MONGO_CLUSTER')
    MONGO_DATABASE = os.environ.get('MONGO_DATABASE', 'cotizaciones')
    
    # Validar credenciales MongoDB
    if not all([MONGO_USERNAME, MONGO_PASSWORD, MONGO_CLUSTER]):
        logging.warning("Credenciales MongoDB no configuradas completamente")
    
    @property
    def MONGO_URI(self):
        """Construye URI MongoDB con validación de seguridad"""
        if not all([self.MONGO_USERNAME, self.MONGO_PASSWORD, self.MONGO_CLUSTER]):
            return None
            
        import urllib.parse
        usuario = urllib.parse.quote_plus(self.MONGO_USERNAME)
        contraseña = urllib.parse.quote_plus(self.MONGO_PASSWORD)
        
        # Opciones de seguridad para MongoDB
        opciones = (
            "retryWrites=true&w=majority&"
            "ssl=true&authSource=admin&"
            "connectTimeoutMS=5000&"
            "socketTimeoutMS=5000"
        )
        
        return (f"mongodb+srv://{usuario}:{contraseña}@{self.MONGO_CLUSTER}/"
                f"{self.MONGO_DATABASE}?{opciones}")
    
    # Configuración de aplicación
    APP_NAME = os.environ.get('APP_NAME', 'CWS Cotizaciones')
    APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')
    
    # Límites de seguridad
    MAX_RESULTS_PER_PAGE = 25  # Reducido para prevenir DoS
    DEFAULT_PAGE_SIZE = 10     # Reducido para mejor rendimiento
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB máximo para uploads
    
    # Configuración de logging segura
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING')
    LOG_SENSITIVE_DATA = False  # Nunca loggear datos sensibles en producción
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # Token válido por 1 hora
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "100 per hour"  # Límite por defecto
    
    # Headers de seguridad
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
    }

class DevelopmentConfig(SecureConfig):
    """Configuración para desarrollo con seguridad básica"""
    DEBUG = True
    TESTING = False
    
    # Relajar algunas restricciones para desarrollo
    SESSION_COOKIE_SECURE = False
    LOG_SENSITIVE_DATA = True  # Permitir logs detallados en desarrollo
    
    # CSP más permisivo para desarrollo
    SECURITY_HEADERS = {
        **SecureConfig.SECURITY_HEADERS,
        'Content-Security-Policy': (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com"
        )
    }

class ProductionConfig(SecureConfig):
    """Configuración para producción con máxima seguridad"""
    DEBUG = False
    TESTING = False
    
    # Forzar HTTPS en producción
    PREFERRED_URL_SCHEME = 'https'
    
    # Logging restringido
    LOG_LEVEL = 'ERROR'
    LOG_SENSITIVE_DATA = False
    
    # Rate limiting más estricto
    RATELIMIT_DEFAULT = "50 per hour"
    
    @property
    def MONGO_URI(self):
        """URI MongoDB para producción con prioridad a variable completa"""
        # Prioridad 1: Variable completa para servicios cloud
        uri_completa = os.environ.get('MONGODB_URI')
        if uri_completa:
            # Validar que la URI sea segura
            if 'ssl=true' not in uri_completa:
                logging.warning("MongoDB URI sin SSL detectada")
            return uri_completa
        
        # Prioridad 2: Construir desde componentes
        return super().MONGO_URI

class TestingConfig(SecureConfig):
    """Configuración para testing"""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False  # Deshabilitar CSRF para tests
    MONGO_DATABASE = 'cotizaciones_test'

# Validación de entorno
def validate_environment():
    """Valida configuración de seguridad del entorno"""
    issues = []
    
    # Verificar SECRET_KEY
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        issues.append("SECRET_KEY no configurada")
    elif secret_key == 'dev-secret-key-change-in-production':
        issues.append("SECRET_KEY usando valor por defecto inseguro")
    elif len(secret_key) < 32:
        issues.append("SECRET_KEY demasiado corta (mínimo 32 caracteres)")
    
    # Verificar MongoDB
    if not os.environ.get('MONGODB_URI'):
        required_mongo_vars = ['MONGO_USERNAME', 'MONGO_PASSWORD', 'MONGO_CLUSTER']
        missing_vars = [var for var in required_mongo_vars if not os.environ.get(var)]
        if missing_vars:
            issues.append(f"Variables MongoDB faltantes: {missing_vars}")
    
    # Verificar entorno de producción
    if os.environ.get('FLASK_ENV') == 'production':
        if os.environ.get('FLASK_DEBUG', '').lower() == 'true':
            issues.append("DEBUG habilitado en producción")
    
    return issues

# Selector de configuración
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_secure_config():
    """Obtiene configuración segura basada en entorno"""
    env = os.environ.get('FLASK_ENV', 'default')
    
    # Validar entorno antes de retornar configuración
    issues = validate_environment()
    if issues:
        for issue in issues:
            logging.warning(f"Problema de seguridad: {issue}")
    
    config_class = config_by_name.get(env, DevelopmentConfig)
    
    # Log de configuración (sin datos sensibles)
    logging.info(f"Configuración cargada: {config_class.__name__}")
    
    return config_class

# Middleware de seguridad
def apply_security_headers(app):
    """Aplica headers de seguridad a la aplicación Flask"""
    config = get_secure_config()
    
    @app.after_request
    def set_security_headers(response):
        for header, value in config.SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
    
    return app