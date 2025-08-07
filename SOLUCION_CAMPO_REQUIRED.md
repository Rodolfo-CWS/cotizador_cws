# SOLUCIÓN: Campo "numeroCotizacion es obligatorio"

## Problema Identificado
El campo "No. Cotización" seguía siendo validado como requerido por el navegador, mostrando el mensaje "El campo numeroCotizacion es obligatorio".

## Causa Raíz
- El campo tenía `readonly` pero seguía siendo incluido en la validación HTML5
- Algunos navegadores tratan campos `readonly` como validables
- Posible cache del navegador con versión anterior

## Solución Implementada

### 1. Cambio de `readonly` a `disabled`
**Antes:**
```html
<input type="text" name="numeroCotizacion" readonly>
```

**Después:**
```html
<input type="text" name="numeroCotizacion" disabled>
<input type="hidden" name="numeroCotizacionHidden">
```

### 2. JavaScript de Forzado
Agregado código que garantiza la configuración correcta:
```javascript
// FORZAR: Asegurar que el campo numeroCotizacion NO sea required
const campoNumeroCotizacion = document.querySelector('[name="numeroCotizacion"]');
if (campoNumeroCotizacion) {
    campoNumeroCotizacion.removeAttribute('required');
    campoNumeroCotizacion.setAttribute('disabled', 'disabled');
}
```

### 3. Sistema Dual de Campos
- **Campo visible**: `disabled` para mostrar al usuario
- **Campo hidden**: Para envío de datos al servidor
- **Variables auxiliares**: sessionStorage + window.variable

### 4. Actualización Robusta
```javascript
// Actualizar ambos campos después de guardar
if (numeroGenerado) {
    // Campo visible
    campoNumeroCotizacion.value = numeroGenerado;
    
    // Campo hidden
    campoHidden.value = numeroGenerado;
    
    // Variables auxiliares
    window.ultimoNumeroCotizacion = numeroGenerado;
    sessionStorage.setItem('ultimoNumeroCotizacion', numeroGenerado);
}
```

## Diferencias Clave: readonly vs disabled

### readonly
- ✅ Campo no editable por usuario
- ❌ Sigue siendo validado por HTML5
- ❌ Puede causar error "campo obligatorio"

### disabled  
- ✅ Campo no editable por usuario
- ✅ NO es validado por HTML5
- ✅ No causa errores de validación
- ❌ No se envía en formulario (por eso usamos campo hidden)

## Pasos para Probar

1. **Reinicia el servidor Flask** (importante para limpiar cache):
   ```bash
   cd C:\Users\SDS\cotizador_cws
   python app.py
   ```

2. **Abre el navegador en modo incógnito** (evita cache):
   ```
   http://127.0.0.1:5000/formulario
   ```

3. **Prueba el formulario**:
   - Llena SOLO: Cliente, Vendedor, Proyecto, Atención A, Contacto
   - NO toques el campo "No. Cotización" (debe estar gris y no editable)
   - Agrega un item con descripción
   - Llena términos y condiciones
   - Haz clic en "Guardar"

4. **Resultado esperado**:
   - ✅ NO debe mostrar error "numeroCotizacion es obligatorio"
   - ✅ Debe guardar exitosamente
   - ✅ Número debe aparecer automáticamente en el campo
   - ✅ PDF debe generarse sin problemas

## Archivos Modificados
- `templates/formulario.html`: Campo disabled + JavaScript de forzado
- `verificar_campo.html`: Archivo de prueba creado

Si el problema persiste después de reiniciar el servidor y usar modo incógnito, indica que hay un cache más profundo o algún otro factor interfiriendo.