# Guía de Migración - CWS Cotizador Sistema Unificado

## 🚀 Descripción General

Esta guía te ayudará a migrar del sistema actual al nuevo **Sistema Unificado CWS Cotizador** que integra:

- **Supabase PostgreSQL** (base de datos principal)
- **Cloudinary** (almacenamiento de PDFs con 25GB gratis)
- **Google Drive** (respaldo y PDFs históricos del admin)
- **Sistema offline** con sincronización automática

## ⚡ Migración Rápida (Recomendada)

### Opción 1: Script Automático

```bash
# Migración completa automatizada (recomendado)
python migration_scripts.py
```

El script automático:
- ✅ Crea backup completo del sistema actual
- ✅ Analiza y planifica la migración
- ✅ Migra datos paso a paso con validación
- ✅ Configura el nuevo sistema unificado
- ✅ Verifica integridad de datos
- ✅ Proporciona rollback automático si hay errores

## 📋 Migración Manual (Paso a Paso)

### Requisitos Previos

1. **Variables de Entorno Requeridas** (archivo `.env`):
   ```env
   # Supabase PostgreSQL (Principal)
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key-here
   DATABASE_URL=postgresql://postgres:password@host:5432/database

   # Cloudinary (PDFs Principal - 25GB gratis)
   CLOUDINARY_CLOUD_NAME=your-cloud-name
   CLOUDINARY_API_KEY=your-api-key
   CLOUDINARY_API_SECRET=your-api-secret

   # Google Drive (Fallback)
   GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
   GOOGLE_DRIVE_FOLDER_NUEVAS=folder-id-nuevas
   GOOGLE_DRIVE_FOLDER_ANTIGUAS=folder-id-antiguas
   ```

2. **Crear Cuenta Supabase** (gratuita):
   - Ve a [supabase.com](https://supabase.com)
   - Crea proyecto gratuito
   - Obtén URL y API Key desde Settings > API

3. **Crear Cuenta Cloudinary** (25GB gratis):
   - Ve a [cloudinary.com](https://cloudinary.com) 
   - Crea cuenta gratuita (25GB sin tarjeta)
   - Obtén credenciales desde Dashboard

### Paso 1: Backup del Sistema Actual

```bash
# Crear backup manual
python -c "
from migration_scripts import MigrationManager
manager = MigrationManager()
backup_path = manager.create_full_backup()
print(f'Backup creado en: {backup_path}')
"
```

### Paso 2: Crear Esquema en Supabase

```bash
# Generar esquema SQL
python unified_database_schema.py

# Aplicar en Supabase:
# 1. Abrir Supabase Dashboard > SQL Editor
# 2. Copiar contenido de schema_output/unified_schema.sql
# 3. Ejecutar SQL
```

### Paso 3: Migrar Datos

```bash
# Migrar cotizaciones existentes
python -c "
from migration_scripts import MigrationManager
manager = MigrationManager()
manager.initialize_systems()
success = manager._step_migrate_quotations(type('Step', (), {'error': None, 'completed': False})())
print('Migración de cotizaciones:', 'OK' if success else 'ERROR')
"
```

### Paso 4: Configurar Sistema Unificado

```bash
# Usar la aplicación unificada
python app_unified.py
```

## 🔧 Configuración Detallada

### Supabase Setup

1. **Crear Proyecto**:
   - [Dashboard Supabase](https://app.supabase.com)
   - New Project → Nombrar "cws-cotizador"
   - Guardar password de BD

2. **Configurar Variables**:
   ```env
   SUPABASE_URL=https://xyz.supabase.co
   SUPABASE_ANON_KEY=eyJ... (desde Settings > API)
   DATABASE_URL=postgresql://postgres.[REF]:[PASS]@aws-1-us-east-2.pooler.supabase.com:6543/postgres
   ```

3. **Aplicar Esquema**:
   - SQL Editor → Pegar contenido de `schema_output/unified_schema.sql`
   - Run → Verificar tablas creadas

### Cloudinary Setup

1. **Crear Cuenta Gratuita**:
   - [Cloudinary Signup](https://cloudinary.com/users/register/free)
   - **25GB gratis** sin necesidad de tarjeta de crédito

2. **Obtener Credenciales**:
   ```env
   CLOUDINARY_CLOUD_NAME=tu-cloud-name  # Desde Dashboard
   CLOUDINARY_API_KEY=123456789         # Desde Account Details
   CLOUDINARY_API_SECRET=abc123def      # Desde Account Details  
   ```

3. **Verificar Configuración**:
   ```bash
   python test_cloudinary.py
   ```

## 🔍 Verificación Post-Migración

### Test Completo del Sistema

```bash
# Verificar todos los componentes
python -c "
from unified_storage_manager import get_unified_manager
from app_unified import configurar_logging_avanzado

configurar_logging_avanzado()
print('Inicializando sistema unificado...')

try:
    manager = get_unified_manager()
    status = manager.get_system_status()
    
    print('Estado de sistemas:')
    for sistema, datos in status.items():
        estado = datos.get('status', 'unknown')
        print(f'  {sistema}: {estado.upper()}')
    
    # Test de escritura
    test_data = {
        'numeroCotizacion': f'TEST-{int(__import__(\"time\").time())}',
        'datosGenerales': {
            'cliente': 'TEST-POST-MIGRATION',
            'vendedor': 'ADMIN', 
            'proyecto': 'VERIFICACION'
        },
        'items': [],
        'observaciones': 'Test post-migración'
    }
    
    print('Ejecutando test de escritura...')
    result = manager.guardar_cotizacion(test_data)
    
    if result.success:
        print('✓ Test de escritura: OK')
        
        # Test de lectura
        read_result = manager.obtener_cotizacion(test_data['numeroCotizacion'])
        if read_result.success:
            print('✓ Test de lectura: OK')
        else:
            print('✗ Test de lectura: ERROR')
    else:
        print('✗ Test de escritura: ERROR')
        print(f'Error: {result.error}')
        
except Exception as e:
    print(f'ERROR: {e}')
    print('Verificar configuración de variables de entorno')
"
```

### Verificar Búsqueda

```bash
# Test sistema de búsqueda
python -c "
from unified_search_system import UnifiedSearchSystem
from unified_storage_manager import get_unified_manager

manager = get_unified_manager()
search = UnifiedSearchSystem(manager)

print('Ejecutando búsqueda de prueba...')
resultado = search.buscar('', page=1, per_page=5)

print(f'Resultados encontrados: {resultado.total}')
print(f'Fuentes consultadas: {[f.value for f in resultado.fuentes_consultadas]}')
print(f'Tiempo de búsqueda: {resultado.tiempo_busqueda_ms}ms')
"
```

## ⚠️ Solución de Problemas

### Error: "Supabase connection failed"

```bash
# Verificar variables de entorno
python -c "
import os
required = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
missing = [var for var in required if not os.getenv(var)]
if missing:
    print(f'Variables faltantes: {missing}')
else:
    print('Variables de Supabase configuradas correctamente')
"

# Test de conexión manual
python -c "
from supabase import create_client
import os

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_ANON_KEY')

if url and key:
    try:
        client = create_client(url, key)
        result = client.table('system_config').select('*').limit(1).execute()
        print('✓ Conexión a Supabase: OK')
    except Exception as e:
        print(f'✗ Error de conexión: {e}')
else:
    print('✗ Variables de entorno no configuradas')
"
```

### Error: "Cloudinary authentication failed"

```bash
# Verificar configuración Cloudinary
python -c "
import cloudinary
import os

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

try:
    result = cloudinary.api.resources(max_results=1)
    print('✓ Cloudinary configurado correctamente')
except Exception as e:
    print(f'✗ Error Cloudinary: {e}')
    print('Verificar credenciales en Dashboard > Account Details')
"
```

### Error: "Module not found"

```bash
# Instalar dependencias faltantes
pip install -r requirements.txt

# Si persiste el error
pip install supabase cloudinary google-api-python-client python-dotenv flask reportlab
```

## 🔄 Rollback (Restaurar Sistema Anterior)

Si algo falla durante la migración:

```bash
# Restaurar desde backup automático
python -c "
from migration_scripts import MigrationManager
import glob

# Encontrar último backup
backups = glob.glob('migration_data/backups/full_backup_*')
ultimo_backup = max(backups) if backups else None

if ultimo_backup:
    manager = MigrationManager()
    success = manager.rollback_migration(ultimo_backup)
    print('Rollback:', 'OK' if success else 'ERROR')
else:
    print('No se encontraron backups')
"

# Volver a app.py original
python app.py  # Sistema anterior
```

## 📊 Monitoreo Post-Migración

### Dashboard Administrativo

Una vez migrado, accede al dashboard:
```bash
# Iniciar sistema unificado
python app_unified.py

# Abrir navegador en:
# http://localhost:5000/admin/dashboard
```

### APIs de Monitoreo

```bash
# Estado del sistema
curl http://localhost:5000/admin/dashboard

# Verificación de salud manual
curl -X POST http://localhost:5000/admin/health/check

# Sincronización manual
curl -X POST http://localhost:5000/admin/sync/manual

# Limpiar caches
curl -X POST http://localhost:5000/admin/cache/clear
```

## 🎯 Beneficios del Sistema Unificado

### Antes vs Después

| Aspecto | Sistema Anterior | Sistema Unificado |
|---------|------------------|-------------------|
| **Base de Datos** | JSON local + MongoDB inconsistente | Supabase PostgreSQL + offline automático |
| **PDFs** | Google Drive con límites | Cloudinary 25GB + múltiples respaldos |
| **Búsqueda** | Búsqueda básica local | Búsqueda inteligente multi-fuente |
| **Disponibilidad** | ~95% (fallos de red) | **99.9%** (triple redundancia) |
| **Velocidad** | Variable según conexión | Sub-segundo con cache |
| **Escalabilidad** | Limitada por archivo JSON | Ilimitada (PostgreSQL) |
| **Monitoreo** | Logs básicos | Dashboard completo + alertas |

### Nuevas Capacidades

- ✅ **Búsqueda Inteligente**: Encuentra cotizaciones por cualquier campo
- ✅ **Sincronización Automática**: Sin pérdida de datos offline
- ✅ **Triple Redundancia**: PDFs siempre disponibles
- ✅ **Dashboard Admin**: Monitoreo en tiempo real
- ✅ **API REST**: Integración con otros sistemas
- ✅ **Backup Automático**: Respaldo continuo en la nube
- ✅ **Performance**: Búsquedas sub-segundo con cache

## 📞 Soporte

### Archivos de Log

En caso de problemas, revisar:
- `logs/app_unified.log` - Log principal de la aplicación
- `logs/errores_criticos.log` - Errores críticos únicamente  
- `logs/performance_metrics.log` - Métricas de rendimiento
- `logs/migration.log` - Log específico de migración

### Información del Sistema

```bash
# Generar reporte de sistema
python -c "
import json
from unified_storage_manager import get_unified_manager

try:
    manager = get_unified_manager()
    
    report = {
        'system_status': manager.get_system_status(),
        'health': manager.get_system_health_summary() if hasattr(manager, 'get_system_health_summary') else 'N/A',
        'timestamp': __import__('datetime').datetime.now().isoformat()
    }
    
    print(json.dumps(report, indent=2, ensure_ascii=False))
except Exception as e:
    print(f'Error generando reporte: {e}')
"
```

---

## ✅ Checklist de Migración

### Pre-Migración
- [ ] Crear cuentas Supabase y Cloudinary
- [ ] Configurar variables de entorno en `.env`
- [ ] Crear backup manual del sistema actual
- [ ] Verificar dependencias instaladas

### Durante Migración  
- [ ] Ejecutar `python migration_scripts.py`
- [ ] Verificar que no hay errores críticos
- [ ] Confirmar que datos fueron migrados
- [ ] Probar nuevo sistema con `python app_unified.py`

### Post-Migración
- [ ] Verificar búsqueda funciona correctamente
- [ ] Crear cotización de prueba end-to-end
- [ ] Revisar dashboard admin funcional
- [ ] Confirmar PDFs se almacenan en Cloudinary
- [ ] Establecer monitoreo regular

### En Caso de Problemas
- [ ] Revisar logs específicos del error
- [ ] Verificar configuración de variables de entorno
- [ ] Ejecutar rollback si es necesario
- [ ] Documentar problema para corrección

---

**¡La migración al Sistema Unificado te dará un sistema más robusto, rápido y confiable para CWS Cotizador!** 🚀