# 🔧 INSTRUCCIONES: Reparar Supabase DB

## **Problema**
La aplicación funcionaba bien antes, pero ahora **solo guarda en JSON offline**, no en Supabase DB. Supabase Storage sigue funcionando perfectamente para PDFs.

## **Causa Raíz Identificada**
Las **tablas no existen** en tu instancia de Supabase PostgreSQL. El código intenta insertar en tablas que faltan:
- ❌ Tabla `cotizaciones` 
- ❌ Tabla `cotizacion_counters`
- ❌ Columna `condiciones` en cotizaciones

## **Solución Paso a Paso**

### **Paso 1: Ejecutar Script SQL en Supabase Dashboard** ⭐ **CRÍTICO**

1. **Abrir Supabase Dashboard:**
   - Ve a: https://supabase.com/dashboard
   - Selecciona tu proyecto CWS

2. **Ejecutar el Script Completo:**
   - Clic en **"SQL Editor"** en la barra lateral
   - Clic en **"New query"**
   - **Copiar TODO** el contenido de `fix_supabase_schema.sql` 
   - **Pegar** en el editor SQL
   - Clic en **"Run"** (o Ctrl+Enter)

3. **Verificar Ejecución:**
   - Deberías ver mensajes como "CREATE TABLE", "CREATE INDEX", etc.
   - Al final debe mostrar una tabla con: `cotizaciones`, `cotizacion_counters`, `pdf_storage`
   - Si hay errores, reportar exactamente el mensaje de error

### **Paso 2: Verificar Creación de Tablas**

**En el mismo SQL Editor de Supabase, ejecutar:**
```sql
-- Verificar que las tablas existen
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('cotizaciones', 'cotizacion_counters', 'pdf_storage');

-- Verificar estructura de cotizaciones (debe incluir 'condiciones')
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'cotizaciones' AND table_schema = 'public'
ORDER BY ordinal_position;
```

**Resultado Esperado:**
- 3 tablas: `cotizaciones`, `cotizacion_counters`, `pdf_storage`
- Columnas de cotizaciones deben incluir: `condiciones` (tipo `jsonb`)

### **Paso 3: Probar Localmente** 🧪

**Ejecutar el test completo:**
```bash
cd C:\Users\SDS\cotizador_cws
python test_schema_fix.py
```

**Resultado Esperado:**
```
✅ TEST 1: Conexión a Supabase - ÉXITO
✅ TEST 2: Verificar tablas - ÉXITO  
✅ TEST 3: Estructura cotizaciones - ÉXITO
✅ TEST 4: Inserción completa - ÉXITO
✅ TEST 5: Contadores atómicos - ÉXITO
✅ TEST 6: Estadísticas sistema - ÉXITO

🎉 ✅ TODOS LOS TESTS PASARON
```

Si algún test falla, el script te dirá exactamente qué falta.

### **Paso 4: Probar la Aplicación** 🚀

**Iniciar la aplicación:**
```bash
python app.py
```

**O usar el script rápido:**
```bash
EJECUTAR_RAPIDO.bat
```

**Verificar en logs de inicio:**
Deberías ver:
```
[SUPABASE] Conectado a PostgreSQL exitosamente
[SUPABASE] Tablas disponibles: ['cotizaciones', 'cotizacion_counters', 'pdf_storage']
```

En lugar de:
```
[SUPABASE] Error conectando: ...
[SUPABASE] Activando modo offline
```

### **Paso 5: Crear una Cotización de Prueba** 

1. **Ir a:** http://localhost:5000/formulario
2. **Llenar datos básicos:**
   - Cliente: "TEST-REPARACION"
   - Vendedor: "TU_NOMBRE"  
   - Proyecto: "PRUEBA-DB-FIX"
3. **Agregar un item cualquiera**
4. **Enviar formulario**

**Verificar en logs:**
```
[SUPABASE] Cotizacion guardada: ID=123
[OK] FORMULARIO: Guardado exitoso - Numero: TEST-REPARACION-CWS-XX-001-R1-PRUEBA-DB-FIX
```

### **Paso 6: Despliegue Automático** 🌐

**El fix se aplicará automáticamente en Render porque:**
- Render usa la misma `DATABASE_URL` que tu local
- Las tablas creadas en Supabase están disponibles para ambos
- No necesitas hacer nada especial en Render

**Para confirmar en producción:**
1. Esperar ~2 minutos después del deploy
2. Ir a: https://cotizador-cws.onrender.com/info
3. Verificar que muestre `"modo": "online"` en lugar de `"offline"`

## **Archivos Creados/Modificados**

### ✅ **Archivos Nuevos:**
- `fix_supabase_schema.sql` - Script SQL completo para ejecutar
- `test_schema_fix.py` - Test de validación  
- `INSTRUCCIONES_REPARAR_SUPABASE.md` - Este archivo

### ✅ **Archivos Modificados:**
- `supabase_schema_simple.sql` - Agregada columna `condiciones`

### ✅ **Archivos Existentes (sin cambios):**
- `crear_tabla_contadores.py` - Ya estaba correcto
- `supabase_manager.py` - Ya estaba preparado para las tablas

## **Troubleshooting**

### **Si test_schema_fix.py falla:**

**❌ "Conexión falló":**
```bash
# Verificar variables de entorno
python -c "import os; print('SUPABASE_URL:', bool(os.getenv('SUPABASE_URL'))); print('DATABASE_URL:', bool(os.getenv('DATABASE_URL')))"
```

**❌ "Tabla no existe":**
- Verificar que ejecutaste `fix_supabase_schema.sql` COMPLETO
- Revisar en Supabase Dashboard > Table Editor que las tablas aparezcan

**❌ "Error de sintaxis SQL":**
- Copiar y pegar TODO el archivo `fix_supabase_schema.sql`
- No copiar solo partes del archivo

### **Si la aplicación sigue en modo offline:**

**Verificar en logs de app.py:**
```bash
python app.py
# Buscar líneas:
# [SUPABASE] Error conectando: [AQUÍ APARECERÁ EL ERROR ESPECÍFICO]
```

**Errores comunes:**
- `relation "cotizaciones" does not exist` → Ejecutar fix_supabase_schema.sql
- `column "condiciones" does not exist` → Ejecutar fix_supabase_schema.sql completo
- `SSL connection` → Verificar DATABASE_URL formato

## **Resultado Final Esperado**

### ✅ **Después del Fix:**
- **Supabase DB**: ✅ Funciona (modo online)
- **Supabase Storage**: ✅ Sigue funcionando (PDFs)  
- **Google Drive**: ✅ Sigue como fallback
- **JSON Offline**: ✅ Sigue como backup local

### 📊 **Flujo de Datos Restaurado:**
1. **Formulario** → Datos enviados
2. **supabase_manager.py** → Modo ONLINE (no offline)
3. **PostgreSQL** → Cotización guardada en tabla `cotizaciones`
4. **JSON local** → También guardada como backup
5. **PDF** → Generado y guardado en Supabase Storage

## **Confirmación Visual**

**En http://localhost:5000/info deberías ver:**
```json
{
  "database": {
    "tipo": "supabase_postgresql", 
    "modo": "online",           ← ESTO ES CLAVE
    "registros": 1
  }
}
```

En lugar de:
```json
{
  "database": {
    "tipo": "json_offline",     ← ESTO INDICA PROBLEMA
    "modo": "offline"
  }
}
```

---

## **¿Necesitas Ayuda?**

Si algún paso falla:

1. **Ejecutar:** `python test_schema_fix.py`
2. **Copiar** el output completo del test que falla
3. **Reportar** el error específico

El script de test te dirá exactamente qué está mal y cómo arreglarlo.