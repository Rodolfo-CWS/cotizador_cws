# Solución al Problema de Cache de Logo

## 🎯 Problema

Los logos no se actualizan en Render después del deploy, incluso después de cambiar los archivos.

## 🔍 Causa

Los navegadores cachean archivos estáticos (imágenes, CSS, JS) de forma agresiva para mejorar el rendimiento. Cuando subes un nuevo logo con el mismo nombre (`logo.png`), el navegador sigue mostrando la versión antigua en cache.

## ✅ Soluciones

### Solución 1: Cache Busting con Parámetro de Versión (Recomendado)

Agregar un parámetro de versión a las URLs de los logos fuerza al navegador a recargar la imagen.

**Implementación Automática con Variable de Entorno**:

1. En Render, agrega una nueva variable de entorno:
   - Nombre: `STATIC_VERSION`
   - Valor: `1` (incrementa cada vez que cambies assets estáticos)

2. En `app.py`, agrega esta configuración:

```python
import os
from datetime import datetime

# Agregar después de la inicialización de Flask app
@app.context_processor
def inject_static_version():
    """Inyectar versión de assets estáticos para cache busting"""
    static_version = os.getenv('STATIC_VERSION', str(int(datetime.now().timestamp())))
    return dict(static_version=static_version)
```

3. Actualiza los templates para usar la versión:

```html
<!-- Antes -->
<img src="/static/logo.png" alt="CWS Company">

<!-- Después -->
<img src="/static/logo.png?v={{ static_version }}" alt="CWS Company">
```

**Ventaja**: Control total sobre cuándo invalidar el cache.

### Solución 2: Usar Hash del Archivo (Avanzado)

Genera un hash del contenido del archivo y úsalo como versión:

```python
import hashlib

def get_file_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()[:8]

@app.context_processor
def inject_static_hashes():
    return dict(
        logo_hash=get_file_hash('static/logo.png')
    )
```

```html
<img src="/static/logo.png?v={{ logo_hash }}" alt="CWS Company">
```

**Ventaja**: Cambio automático de versión cuando cambia el archivo.

### Solución 3: Renombrar el Archivo (Rápido pero no escalable)

Cambiar el nombre del archivo cada vez que lo actualices:

```
logo.png → logo-v2.png → logo-v3.png
```

**Desventaja**: Requiere actualizar todos los templates.

### Solución 4: Configurar Headers de Cache en Flask (Complementario)

```python
@app.after_request
def add_cache_control(response):
    """Configurar cache para archivos estáticos"""
    if request.path.startswith('/static/'):
        # Cache corto para desarrollo, largo para producción
        if app.config.get('ENV') == 'production':
            response.cache_control.max_age = 31536000  # 1 año
        else:
            response.cache_control.max_age = 0
            response.cache_control.no_cache = True
    return response
```

## 🚀 Implementación Recomendada

La mejor práctica es combinar **Solución 1** (versioning) con **Solución 4** (headers):

1. Cache largo para assets versionados (performance)
2. Versión cambia cuando actualizas archivos (control)
3. Navegadores siempre obtienen la última versión

## 🧪 Cómo Probar

Después de implementar la solución:

1. Haz deploy en Render
2. Abre la app en modo incógnito (Ctrl+Shift+N en Chrome)
3. Verifica que el nuevo logo se muestra
4. O fuerza reload: Ctrl+Shift+R (Windows) / Cmd+Shift+R (Mac)

## 📝 Para Este Proyecto

Te recomiendo implementar la **Solución 1** porque:
- Fácil de implementar
- Control manual sobre versión
- No requiere cambios complejos
- Compatible con todos los navegadores

## ⚡ Fix Rápido Sin Código (Temporal)

Si necesitas que los usuarios vean el logo actualizado **inmediatamente**:

1. Pídeles que limpien cache del navegador:
   - Chrome: Ctrl+Shift+Delete → Seleccionar "Imágenes y archivos en caché"
   - Firefox: Ctrl+Shift+Delete → Seleccionar "Caché"

2. O que usen modo incógnito/privado temporalmente

**Nota**: Esto no es una solución permanente, solo un workaround temporal.
