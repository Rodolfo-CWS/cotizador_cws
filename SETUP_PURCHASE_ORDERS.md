# Configuración del Módulo de Órdenes de Compra

Este documento explica cómo configurar el módulo de órdenes de compra en tu entorno de producción de Render.

## 🚨 Problema Actual

Al hacer clic en "Nueva OC" aparece el error:
```json
{"codigo":500,"error":true,"mensaje":"Error interno del servidor"}
```

**Causa**: Las tablas de base de datos necesarias para el módulo de órdenes de compra no existen en Supabase.

## ✅ Solución: Inicializar Base de Datos

### Paso 1: Acceder a Supabase SQL Editor

1. Ve a tu proyecto de Supabase: https://supabase.com/dashboard
2. Selecciona tu proyecto
3. En el menú lateral, haz clic en **SQL Editor**

### Paso 2: Ejecutar Script de Inicialización

1. Abre el archivo `init_proyectos.sql` en este repositorio
2. Copia **todo** el contenido del archivo
3. Pégalo en el SQL Editor de Supabase
4. Haz clic en **Run** (o presiona `Ctrl+Enter`)

### Paso 3: Verificar Creación de Tablas

Después de ejecutar el script, verifica que las siguientes tablas se crearon correctamente:

1. Ve a **Table Editor** en Supabase
2. Deberías ver estas nuevas tablas:
   - `ordenes_compra` - Órdenes de compra recibidas
   - `proyectos` - Proyectos vinculados a OCs
   - `gastos_proyecto` - Gastos asociados a proyectos
   - `notificaciones` - Sistema de notificaciones in-app

### Paso 4: Crear Bucket de Storage para PDFs de OCs

1. En Supabase, ve a **Storage**
2. Haz clic en **Create new bucket**
3. Nombre del bucket: `ocs-pdfs`
4. Configuración:
   - **Public bucket**: Sí (activar)
   - **File size limit**: 50MB
   - **Allowed MIME types**: `application/pdf`
5. Haz clic en **Save**

### Paso 5: Reiniciar App en Render

1. Ve a tu dashboard de Render: https://dashboard.render.com/
2. Selecciona tu servicio del cotizador
3. Haz clic en **Manual Deploy** → **Deploy latest commit**
4. O simplemente espera - Render redeploy automáticamente al hacer push

## 🎉 Verificación

Una vez completados los pasos:

1. Accede a tu app: https://cotizador-cws.onrender.com/
2. Inicia sesión
3. Haz clic en el dashboard o en "Órdenes de Compra"
4. Ya no deberías ver errores 500

## 📊 Estructura de Base de Datos Creada

### Tabla `ordenes_compra`
- `id` - ID autoincremental
- `numero_oc` - Número único de OC (ej: "BMW-2024-001")
- `cliente` - Nombre del cliente
- `fecha_recepcion` - Fecha de recepción de la OC
- `monto_total` - Monto total en decimal
- `moneda` - MXN o USD
- `archivo_pdf` - URL del PDF en Supabase Storage
- `estatus` - activa, en_proceso, completada, cancelada
- `notas` - Notas adicionales

### Tabla `proyectos`
- Se crea automáticamente un proyecto por cada OC
- Vinculación 1:1 con OC
- Tracking de presupuesto y progreso

### Tabla `gastos_proyecto`
- Gastos asociados a cada proyecto
- Sistema de aprobaciones
- Control de estatus de compra

### Tabla `notificaciones`
- Notificaciones in-app para usuarios
- Sistema de lectura/no leída

## ❓ Preguntas Frecuentes

### ¿Necesito ejecutar el script cada vez que hago deploy?

**No**. El script solo necesita ejecutarse **una vez** por entorno. Las tablas persisten en Supabase independientemente de los deployments de Render.

### ¿Qué pasa si ejecuto el script dos veces?

No hay problema. El script usa `CREATE TABLE IF NOT EXISTS`, por lo que no duplicará las tablas si ya existen.

### ¿Los datos de prueba se crearán automáticamente?

No. Los datos de prueba están comentados en el script. Si quieres datos de prueba, descomenta las líneas 172-184 en `init_proyectos.sql`.

## 🔧 Troubleshooting

### Error: "relation 'ordenes_compra' does not exist"

**Solución**: Ejecuta el script `init_proyectos.sql` en Supabase SQL Editor.

### Error: "permission denied for table ordenes_compra"

**Solución**: Verifica que tu `DATABASE_URL` en Render tiene permisos de escritura en Supabase.

### Error: "Base de datos no disponible"

**Solución**:
1. Verifica que `DATABASE_URL` esté configurado correctamente en Render
2. Formato correcto: `postgresql://postgres.[REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres`

## 📝 Notas Técnicas

- Los managers (`oc_manager.py`, `proyecto_manager.py`, `notificaciones_manager.py`) ahora son resilientes a fallos de conexión
- Si la base de datos no está disponible, la app seguirá funcionando para cotizaciones
- El módulo de OCs solo estará disponible cuando las tablas existan

## 🚀 Próximos Pasos

Una vez configurado:
1. Crear tu primera orden de compra
2. El sistema creará automáticamente un proyecto vinculado
3. Podrás agregar gastos al proyecto
4. Sistema de aprobaciones funcionará automáticamente
