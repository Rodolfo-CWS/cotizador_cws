import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

class Config:
    """Configuración base de la aplicación"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Supabase PostgreSQL (Nueva base de datos principal)
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')  # Para operaciones admin
    DATABASE_URL = os.environ.get('DATABASE_URL')  # PostgreSQL connection string
    
    # Configuración de la aplicación
    APP_NAME = os.environ.get('APP_NAME', 'CWS Cotizaciones')
    APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')
    
    # Límites
    MAX_RESULTS_PER_PAGE = int(os.environ.get('MAX_RESULTS_PER_PAGE', '50'))
    DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE', '20'))

class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    TESTING = False
    
    # Configuración Supabase para producción
    def validate_supabase_config(self):
        """Valida que las variables de Supabase estén configuradas"""
        missing = []
        
        if not self.SUPABASE_URL:
            missing.append('SUPABASE_URL')
        if not self.DATABASE_URL:
            missing.append('DATABASE_URL')
        if not self.SUPABASE_ANON_KEY:
            missing.append('SUPABASE_ANON_KEY')
        
        if missing:
            print(f"⚠️  Variables Supabase faltantes: {', '.join(missing)}")
            print("   Sistema funcionará en modo offline con JSON")
            return False
        
        print("✅ Configuración Supabase completa")
        return True

class TestingConfig(Config):
    """Configuración para testing"""
    TESTING = True
    DEBUG = True

# Selector de configuración basado en entorno
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Obtiene la configuración basada en la variable FLASK_ENV"""
    env = os.environ.get('FLASK_ENV', 'default')
    return config_by_name.get(env, DevelopmentConfig)