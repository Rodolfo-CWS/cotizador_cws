# 🚀 GUÍA SETUP SUPABASE PARA CWS COTIZADOR

## 📋 PASO A PASO

### 1. CREAR PROYECTO SUPABASE (5 minutos)

1. **Ve a [supabase.com](https://supabase.com)**
2. **Crea cuenta gratuita** (GitHub/Google/Email)
3. **Crear nuevo proyecto:**
   - Nombre: `cws-cotizador`
   - Región: `US East (Virginia)` ← Mejor latencia con Render
   - Password: Elige una fuerte (guárdala bien)

### 2. CONFIGURAR BASE DE DATOS (5 minutos)

1. **Ve a SQL Editor** en el dashboard
2. **Ejecuta el schema de base de datos:**

   **OPCIÓN A (Recomendada): Schema completo con búsqueda optimizada**
   - Copia todo el contenido de `supabase_schema.sql`
   - Pégalo en el SQL Editor
   - Ejecuta (RUN)
   
   **OPCIÓN B: Si hay errores con índices GIN**
   - Usa `supabase_schema_simple.sql` en su lugar
   - Mismo funcionamiento, índices más básicos
   - Ejecuta (RUN)

### 3. OBTENER CREDENCIALES (2 minutos)

**Ve a Settings → API y copia:**
```env
SUPABASE_URL=https://tu-proyecto-id.supabase.co
SUPABASE_ANON_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Ve a Settings → Database y copia:**
```env
DATABASE_URL=postgresql://postgres.tu-proyecto:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

### 4. CONFIGURAR VARIABLES DE ENTORNO

#### **Para Desarrollo Local (.env)**
```env
# Supabase Configuration
SUPABASE_URL=https://tu-proyecto-id.supabase.co
SUPABASE_ANON_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
DATABASE_URL=postgresql://postgres.tu-proyecto:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres

# Mantener configuraciones existentes
CLOUDINARY_CLOUD_NAME=dvexwdihj
CLOUDINARY_API_KEY=685549632198419
CLOUDINARY_API_SECRET=h1ZiyNA6M7POz6-Fwy10acGVt2U

# Google Drive (fallback)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
GOOGLE_DRIVE_FOLDER_NUEVAS=1h4DF0bdInRU5GUh9n7g8aXgZA4Kyt2Nf
GOOGLE_DRIVE_FOLDER_ANTIGUAS=1GqM9yfwUKd9n8nN97IUiBSUrWUZ1Vida
```

#### **Para Render (Variables de Entorno)**
```env
SUPABASE_URL=https://tu-proyecto-id.supabase.co
SUPABASE_ANON_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
DATABASE_URL=postgresql://postgres.tu-proyecto:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
FLASK_ENV=production
```

## 🔄 MIGRACIÓN DE DATOS

### 1. INSTALAR DEPENDENCIAS
```bash
cd cotizador_cws
pip install -r requirements.txt
```

### 2. PREVIEW DE MIGRACIÓN (sin cambios)
```bash
python migrate_to_supabase.py --preview
```

### 3. EJECUTAR MIGRACIÓN
```bash
python migrate_to_supabase.py --migrate
```

### 4. VALIDAR MIGRACIÓN
```bash
python migrate_to_supabase.py --validate
```

## ✅ TESTING LOCAL

### 1. PROBAR CONEXIÓN
```bash
python -c "
from supabase_manager import SupabaseManager
sm = SupabaseManager()
stats = sm.obtener_estadisticas()
print('Estadísticas:', stats)
"
```

### 2. PROBAR BÚSQUEDA
```bash
python -c "
from supabase_manager import SupabaseManager
sm = SupabaseManager()
result = sm.buscar_cotizaciones('test', 1, 10)
print('Resultados:', result.get('total', 0))
"
```

### 3. EJECUTAR APP LOCAL
```bash
python app.py
# O usar: EJECUTAR_RAPIDO.bat
```

## 🚀 DEPLOY A RENDER

### 1. CONFIGURAR VARIABLES EN RENDER
- Ve a tu Web Service en Render
- Settings → Environment
- Agregar todas las variables de Supabase

### 2. COMANDOS RENDER
```
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
```

### 3. DEPLOY Y VALIDAR
- Trigger deploy manual
- Verificar logs que no hay errores
- Probar funcionalidad en la URL de producción

## 🎯 RESULTADO ESPERADO

### **Antes (MongoDB)**
- ❌ SSL handshake failures
- ❌ Timeouts de conexión
- ❌ Problemas de compatibilidad Render

### **Después (Supabase)**
- ✅ Conectividad perfecta
- ✅ Búsquedas 10x más rápidas
- ✅ APIs automáticas incluidas
- ✅ Almacenamiento PDFs en BD
- ✅ Dashboard admin web
- ✅ Real-time capabilities

## 🆘 TROUBLESHOOTING

### Si no conecta en desarrollo:
1. Verificar que las variables estén en `.env`
2. Revisar que el schema esté creado en Supabase
3. Confirmar que la password del proyecto sea correcta

### Si no funciona en Render:
1. Verificar variables de entorno en Render Dashboard
2. Revisar logs de deploy para errores específicos
3. Confirmar que Render tenga acceso a internet para conectar a Supabase

### Si la migración falla:
1. Verificar que `cotizaciones_offline.json` exista
2. Confirmar que el schema esté creado en Supabase
3. Revisar permisos de la base de datos

## 📞 COMANDOS ÚTILES

```bash
# Ver logs de Supabase en tiempo real (desarrollo)
python -c "from supabase_manager import SupabaseManager; sm = SupabaseManager(); print(sm.obtener_estadisticas())"

# Forzar modo offline (para testing)
export DATABASE_URL=""
python app.py

# Verificar que todas las dependencias estén instaladas
pip list | grep -E "(supabase|psycopg2)"
```

---

**🎉 Una vez completada la migración tendrás:**
- Base de datos PostgreSQL estable y rápida
- 0 problemas de conectividad SSL
- APIs automáticas para futuras integraciones
- Dashboard web para administración
- Búsquedas optimizadas con índices
- Almacenamiento de PDFs integrado
- Compatibilidad perfecta con Render