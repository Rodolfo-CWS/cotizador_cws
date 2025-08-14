"""
PROTECCIÓN CSRF PARA SISTEMA CWS
Implementa tokens CSRF para prevenir ataques Cross-Site Request Forgery
"""

import secrets
import hmac
import hashlib
import time
from functools import wraps
from flask import request, session, jsonify, abort
import logging

csrf_logger = logging.getLogger('CSRF_PROTECTION')

class CSRFProtection:
    """Manejador de protección CSRF"""
    
    def __init__(self, app=None, secret_key=None):
        self.app = app
        self.secret_key = secret_key
        self.token_timeout = 3600  # 1 hora
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa protección CSRF para la aplicación Flask"""
        self.app = app
        self.secret_key = app.config.get('SECRET_KEY')
        
        if not self.secret_key:
            raise ValueError("SECRET_KEY requerida para protección CSRF")
        
        # Registrar funciones template
        app.jinja_env.globals['csrf_token'] = self.generate_csrf_token
        app.jinja_env.globals['csrf_meta'] = self.csrf_meta_tag
    
    def generate_csrf_token(self):
        """Genera un token CSRF único para la sesión"""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
            session['csrf_time'] = time.time()
        
        # Verificar si el token ha expirado
        elif time.time() - session.get('csrf_time', 0) > self.token_timeout:
            session['csrf_token'] = secrets.token_urlsafe(32)
            session['csrf_time'] = time.time()
        
        return session['csrf_token']
    
    def validate_csrf_token(self, token=None):
        """Valida el token CSRF"""
        if token is None:
            # Buscar token en diferentes lugares
            token = (
                request.form.get('csrf_token') or
                request.headers.get('X-CSRF-Token') or
                request.json.get('csrf_token') if request.is_json else None
            )
        
        if not token:
            csrf_logger.warning(f"Token CSRF faltante desde {request.remote_addr}")
            return False
        
        session_token = session.get('csrf_token')
        if not session_token:
            csrf_logger.warning(f"Token CSRF no existe en sesión desde {request.remote_addr}")
            return False
        
        # Verificar expiración
        token_time = session.get('csrf_time', 0)
        if time.time() - token_time > self.token_timeout:
            csrf_logger.warning(f"Token CSRF expirado desde {request.remote_addr}")
            return False
        
        # Comparación segura contra timing attacks
        if not hmac.compare_digest(token, session_token):
            csrf_logger.warning(f"Token CSRF inválido desde {request.remote_addr}")
            return False
        
        return True
    
    def csrf_meta_tag(self):
        """Genera meta tag para el token CSRF"""
        token = self.generate_csrf_token()
        return f'<meta name="csrf-token" content="{token}">'
    
    def exempt(self, view):
        """Decorator para eximir vistas de protección CSRF"""
        if not hasattr(view, 'csrf_exempt'):
            view.csrf_exempt = True
        return view

# Decorator para proteger rutas
def csrf_protect(f):
    """Decorator que requiere token CSRF válido"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar si la vista está exenta
        if hasattr(f, 'csrf_exempt') and f.csrf_exempt:
            return f(*args, **kwargs)
        
        # Solo validar en métodos que modifican datos
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            csrf = CSRFProtection(secret_key=request.app.config.get('SECRET_KEY'))
            
            if not csrf.validate_csrf_token():
                if request.is_json:
                    return jsonify({
                        'error': 'Token CSRF inválido o faltante',
                        'codigo': 'CSRF_ERROR'
                    }), 403
                else:
                    abort(403)
        
        return f(*args, **kwargs)
    
    return decorated_function

# Implementación específica para rutas CWS
def apply_csrf_to_routes(app):
    """Aplica protección CSRF a rutas específicas del sistema CWS"""
    
    # Inicializar protección CSRF
    csrf = CSRFProtection(app)
    
    # Lista de rutas que requieren protección CSRF
    protected_routes = [
        '/',
        '/formulario',
        '/generar_pdf',
        '/admin/migrar-a-mongodb',
        '/admin/sincronizar-offline',
        '/admin/importar-pdf'
    ]
    
    # Aplicar protección a rutas específicas
    for rule in app.url_map.iter_rules():
        if rule.rule in protected_routes:
            endpoint = app.view_functions.get(rule.endpoint)
            if endpoint:
                app.view_functions[rule.endpoint] = csrf_protect(endpoint)
    
    return csrf

# JavaScript helper para el cliente
CSRF_JAVASCRIPT_HELPER = '''
<script>
// Helper para manejo de CSRF en cliente
class CSRFHelper {
    static getToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : null;
    }
    
    static addTokenToForm(form) {
        const token = this.getToken();
        if (token) {
            let input = form.querySelector('input[name="csrf_token"]');
            if (!input) {
                input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'csrf_token';
                form.appendChild(input);
            }
            input.value = token;
        }
    }
    
    static addTokenToHeaders(headers = {}) {
        const token = this.getToken();
        if (token) {
            headers['X-CSRF-Token'] = token;
        }
        return headers;
    }
    
    static addTokenToJSON(data = {}) {
        const token = this.getToken();
        if (token) {
            data.csrf_token = token;
        }
        return data;
    }
}

// Auto-agregar tokens a formularios existentes
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form[method="post"], form[method="POST"]');
    forms.forEach(form => {
        CSRFHelper.addTokenToForm(form);
    });
});

// Interceptar fetch requests para agregar token CSRF
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    if (options.method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method.toUpperCase())) {
        // Agregar token a headers
        options.headers = CSRFHelper.addTokenToHeaders(options.headers || {});
        
        // Si es JSON, agregar token al body
        if (options.headers['Content-Type'] === 'application/json' && options.body) {
            try {
                const data = JSON.parse(options.body);
                options.body = JSON.stringify(CSRFHelper.addTokenToJSON(data));
            } catch (e) {
                console.warn('No se pudo agregar CSRF token al JSON body');
            }
        }
    }
    
    return originalFetch(url, options);
};

window.CSRFHelper = CSRFHelper;
</script>
'''