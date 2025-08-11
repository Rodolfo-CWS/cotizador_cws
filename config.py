import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

class Config:
    """Configuración base de la aplicación"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # MongoDB
    MONGO_USERNAME = os.environ.get('MONGO_USERNAME', 'admin')
    MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD', 'ADMIN123')
    MONGO_CLUSTER = os.environ.get('MONGO_CLUSTER', 'cluster0.t4e0tp8.mongodb.net')
    MONGO_DATABASE = os.environ.get('MONGO_DATABASE', 'cotizaciones')
    
    @property
    def MONGO_URI(self):
        """Construye la URI de MongoDB con las variables de entorno"""
        import urllib.parse
        usuario = urllib.parse.quote_plus(self.MONGO_USERNAME)
        contraseña = urllib.parse.quote_plus(self.MONGO_PASSWORD)
        return f"mongodb+srv://{usuario}:{contraseña}@{self.MONGO_CLUSTER}/{self.MONGO_DATABASE}?retryWrites=true&w=majority&appName=Cluster0"
    
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
    
    # En producción, preferir MONGODB_URI si está disponible, sino usar componentes
    @property
    def MONGO_URI(self):
        # Prioridad 1: Variable completa para Render/producción
        uri_completa = os.environ.get('MONGODB_URI')
        if uri_completa:
            print("Usando MONGODB_URI completa para producción")
            return uri_completa
        
        # Prioridad 2: Variable alternativa específica de producción
        uri_prod = os.environ.get('MONGO_URI_PROD')
        if uri_prod:
            print("Usando MONGO_URI_PROD para producción")
            return uri_prod
        
        # Prioridad 3: Construir desde componentes (fallback para desarrollo)
        print("Construyendo URI desde componentes para producción")
        import urllib.parse
        usuario = urllib.parse.quote_plus(self.MONGO_USERNAME)
        contraseña = urllib.parse.quote_plus(self.MONGO_PASSWORD)
        return f"mongodb+srv://{usuario}:{contraseña}@{self.MONGO_CLUSTER}/{self.MONGO_DATABASE}?retryWrites=true&w=majority&appName=Cluster0"

class TestingConfig(Config):
    """Configuración para testing"""
    TESTING = True
    DEBUG = True
    MONGO_DATABASE = 'cotizaciones_test'

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