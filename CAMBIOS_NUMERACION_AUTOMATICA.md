# Cambios Implementados: Numeración Automática de Cotizaciones

## Resumen de Cambios

Se ha implementado un sistema de generación automática de números de cotización según los requisitos especificados.

## Formato del Número de Cotización

**Estructura:** `Cliente + "CWS" + Iniciales_Vendedor + Número_Consecutivo + "R" + Revisión + Proyecto`

**Ejemplo:** `ACMECORPORCWSJP001R1TORRERESID`

Donde:
- `ACMECORPOR` = Cliente (normalizado, máximo 10 caracteres)
- `CWS` = Identificador fijo de la empresa
- `JP` = Iniciales del vendedor (Juan Pérez)
- `001` = Número consecutivo (formato 3 dígitos con ceros)
- `R1` = Revisión 1
- `TORRERESID` = Proyecto (normalizado, máximo 10 caracteres)

## Archivos Modificados

### 1. `database.py`
- **Agregadas 3 nuevas funciones:**
  - `generar_numero_cotizacion()`: Genera número completo automáticamente
  - `generar_numero_revision()`: Genera número para nuevas revisiones
  - `_obtener_siguiente_consecutivo()`: Obtiene el próximo número consecutivo
  
- **Modificada función `guardar_cotizacion()`:**
  - Genera automáticamente el número si no se proporciona
  - Actualiza automáticamente el número para nuevas revisiones
  - Valida campos obligatorios (cliente, vendedor, proyecto)

### 2. `templates/formulario.html`
- **Campo "No. Cotización":**
  - Cambiado de editable a `readonly`
  - Agregado placeholder "Se generará automáticamente"
  - Estilo visual de campo deshabilitado (gris)
  
- **Validación JavaScript:**
  - Eliminado "numeroCotizacion" de campos requeridos
  - Agregada actualización del campo tras guardado exitoso
  
- **Función `manejarRevision()`:**
  - Ya existía y funciona correctamente
  - Muestra campo de justificación para revisiones ≥ 2
  - Hace obligatorio el campo de justificación

### 3. `app.py`
- **Función `preparar_datos_nueva_revision()`:**
  - Actualizada para usar el nuevo sistema de numeración
  - Utiliza las nuevas funciones del DatabaseManager

## Funcionalidades Implementadas

### ✅ Generación Automática
- El número se genera automáticamente al guardar
- No requiere intervención del usuario
- Formato consistente y único

### ✅ Numeración Consecutiva
- Sistema de consecutivos por patrón base
- Funciona tanto en MongoDB como en modo offline
- Evita duplicados automáticamente

### ✅ Revisiones
- Nueva revisión mantiene el número base
- Solo actualiza el número de revisión (R1 → R2 → R3)
- Número idéntico excepto por la revisión

### ✅ Justificación Obligatoria
- Campo de justificación aparece automáticamente para revisión ≥ 2
- Validación tanto en frontend como backend
- Campo obligatorio para guardar revisiones

### ✅ Campo No Editable
- Usuario no puede modificar el número de cotización
- Se muestra automáticamente después de guardar
- Interfaz clara con placeholder explicativo

## Casos de Uso

### Caso 1: Nueva Cotización
1. Usuario llena: Cliente, Vendedor, Proyecto
2. Al guardar → Se genera: `CLIENTECWSXX001R1PROYECTO`
3. Campo se actualiza automáticamente en el formulario

### Caso 2: Nueva Revisión
1. Usuario crea nueva revisión de cotización existente
2. Número original: `CLIENTECWSXX001R1PROYECTO`
3. Nueva revisión: `CLIENTECWSXX001R2PROYECTO`
4. **Obligatorio:** Justificación de actualización

### Caso 3: Consecutivos
1. Primera cotización: `ACMECWSJP001R1TORRE`
2. Segunda cotización: `ACMECWSJP002R1EDIFICIO`
3. Tercera cotización: `ACMECWSJP003R1PLAZA`

## Validaciones Implementadas

- **Cliente**: Obligatorio (error si está vacío)
- **Vendedor**: Obligatorio (error si está vacío)
- **Proyecto**: Obligatorio (error si está vacío)
- **Justificación**: Obligatoria solo para revisiones ≥ 2

## Pruebas Realizadas

Ejecutar: `python test_numero_automatico.py`

- ✅ Generación básica de números
- ✅ Generación de revisiones
- ✅ Casos con nombres complejos
- ✅ Sistema de consecutivos
- ✅ Integración con base de datos

## Compatibilidad

- ✅ Funciona con MongoDB
- ✅ Funciona en modo offline (JSON)
- ✅ Mantiene compatibilidad con cotizaciones existentes
- ✅ No rompe funcionalidad existente

## Notas Técnicas

### Normalización de Datos
- Nombres se convierten a mayúsculas
- Espacios se eliminan
- Máximo 10 caracteres por campo
- Caracteres especiales se manejan correctamente

### Iniciales de Vendedor
- Se toman las primeras letras de cada palabra (máximo 2 palabras)
- Si hay una sola palabra, se toman las primeras 2 letras
- Fallback: "XX" si no se pueden obtener iniciales

### Sistema de Fallback
- Si hay error en generación, usa timestamp como backup
- Garantiza siempre un número único
- Logs detallados para debugging