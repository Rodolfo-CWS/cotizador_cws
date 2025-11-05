# Análisis del Flujo de Apertura del PDF BMW

## Flujo Completo del Sistema

### 1. **Usuario hace click en "Ver PDF"**
```javascript
// templates/home.html:619-623
function verPDF(numeroCotizacion) {
    console.log(`Abriendo PDF: ${numeroCotizacion}`);
    const identificadorCodificado = encodeURIComponent(numeroCotizacion);
    window.open(`/pdf/${identificadorCodificado}`, '_blank');
}
```

**Input:** `"BMW-CWS-FM-002-R1-INSTALACIÓ"`
**Output:** Abre nueva pestaña con URL `/pdf/BMW-CWS-FM-002-R1-INSTALACI%C3%93`

---

### 2. **Servidor recibe petición en endpoint /pdf/<numero>**
```python
# app.py:2312-2345
@app.route("/pdf/<path:numero_cotizacion>")
def servir_pdf(numero_cotizacion):
    from urllib.parse import unquote
    numero_original = numero_cotizacion
    numero_cotizacion = unquote(numero_cotizacion)  # Decodifica %C3%93 → Ó

    # Intenta obtener información del PDF
    resultado = pdf_manager.obtener_pdf(numero_cotizacion)

    if not resultado["encontrado"]:
        return jsonify({"error": f"PDF '{numero_cotizacion}' no encontrado"}), 404
```

**Llama a:** `pdf_manager.obtener_pdf("BMW-CWS-FM-002-R1-INSTALACIÓ")`

---

### 3. **pdf_manager.obtener_pdf() busca el PDF**
```python
# pdf_manager.py:698-720
def obtener_pdf(self, numero_cotizacion: str) -> Dict:
    if self.db_manager.modo_offline:
        return self._obtener_pdf_offline(numero_cotizacion)

    # Búsqueda directa en Supabase Storage
    return self._obtener_pdf_offline(numero_cotizacion)  # Siempre usa offline mode
```

**Nota:** SIEMPRE llama a `_obtener_pdf_offline()` sin importar el modo

---

### 4. **_obtener_pdf_offline() busca en múltiples fuentes**
```python
# pdf_manager.py:552-697
def _obtener_pdf_offline(self, numero_cotizacion: str) -> Dict:
    # Variaciones del nombre
    variaciones_nombre = [
        numero_cotizacion,
        numero_cotizacion.replace(' ', '-'),
        numero_cotizacion.upper(),
        numero_cotizacion.lower(),
        f"Cotizacion_{variacion}",  # Con prefijo
        # etc...
    ]

    # 1. BUSCAR EN SUPABASE STORAGE (PRIORITARIO)
    if self.supabase_storage_disponible:
        for variacion in variaciones_nombre:
            supabase_pdfs = self.supabase_storage.buscar_pdfs(variacion, 20)
            for pdf_info in supabase_pdfs:
                # Verifica coincidencia
                if variacion.lower() in pdf_file_path.lower():
                    return {
                        "encontrado": True,
                        "ruta_completa": pdf_info.get('url', ''),
                        "tipo": "supabase_storage"
                    }

    # 2. BUSCAR EN GOOGLE DRIVE
    if self.drive_client.is_available():
        drive_pdfs = self.drive_client.buscar_pdfs(numero_cotizacion)
        # Busca coincidencia exacta...

    # 3. BUSCAR EN CARPETAS LOCALES
    for variacion in variaciones_nombre:
        pdf_nuevos = self.nuevas_path / f"{variacion}.pdf"
        if pdf_nuevos.exists():
            return {"encontrado": True, "ruta_completa": str(pdf_nuevos)}

    # NO ENCONTRADO
    return {"encontrado": False}
```

**Orden de búsqueda:**
1. Supabase Storage (usando `SupabaseStorageManager.buscar_pdfs()`)
2. Google Drive (si está disponible)
3. Archivos locales (carpetas nuevas/antiguas)

---

### 5. **Si se encuentra, servidor descarga y sirve el PDF**
```python
# app.py:2351-2399
if tipo_fuente in ["supabase_storage"] or ruta_completa.startswith("https://"):
    # Descargar desde Supabase Storage
    import requests
    response = requests.get(ruta_completa, timeout=30)

    if response.status_code == 200:
        if response.content.startswith(b'%PDF'):
            pdf_buffer = BytesIO(response.content)
            return send_file(pdf_buffer, mimetype='application/pdf')
        else:
            return jsonify({"error": "Archivo descargado no es un PDF válido"}), 500
    else:
        return jsonify({"error": f"Error descargando PDF (código {response.status_code})"}), 500
```

---

## Posibles Puntos de Falla

### ❌ **Falla A: PDF no existe en Supabase Storage**
- **Causa:** PDF se creó antes de configurar SERVICE_KEY O se perdió en redeploy
- **Síntoma:** `obtener_pdf()` retorna `{"encontrado": False}`
- **Error mostrado:** 404 "PDF no encontrado en Supabase Storage, Google Drive ni localmente"

### ❌ **Falla B: URL del PDF está vacía**
- **Causa:** `supabase_storage.buscar_pdfs()` retorna resultado sin URL
- **Código relevante:** `app.py:2364-2366`
- **Error mostrado:** 500 "URL del PDF no disponible"

### ❌ **Falla C: Descarga falla desde Supabase**
- **Causa:** URL existe pero descarga retorna != 200
- **Código relevante:** `app.py:2374-2395`
- **Error mostrado:** 500 "Error descargando PDF (código XXX)"

### ❌ **Falla D: Contenido descargado no es PDF**
- **Causa:** URL apunta a contenido que no es PDF válido
- **Código relevante:** `app.py:2380-2392`
- **Error mostrado:** 500 "Archivo descargado no es un PDF válido"

### ❌ **Falla E: Problema de encoding del nombre**
- **Causa:** "INSTALACIÓ" (con Ó) vs "INSTALACIO" (sin acento)
- **Mitigación:** Sistema prueba múltiples variaciones
- **Código relevante:** `pdf_manager.py:558-574`

---

## Diagnóstico Recomendado

### Paso 1: Verificar si SUPABASE_SERVICE_KEY está configurada
```bash
# En Render Shell
echo $SUPABASE_SERVICE_KEY
```

### Paso 2: Listar PDFs en Supabase Storage
```python
from supabase_storage_manager import SupabaseStorageManager
storage = SupabaseStorageManager()
resultado = storage.listar_pdfs(max_resultados=1000)
archivos = resultado.get("archivos", [])

# Buscar PDFs de BMW
bmw_pdfs = [p for p in archivos if 'BMW' in p.get('numero_cotizacion', '').upper()]
print(f"PDFs de BMW: {len(bmw_pdfs)}")
for pdf in bmw_pdfs:
    print(f"  - {pdf.get('numero_cotizacion')}: {pdf.get('url')}")
```

### Paso 3: Revisar logs de Render cuando se intenta abrir el PDF

Buscar en logs:
- `[OBTENER PDF] Buscando en Supabase Storage...`
- `[SUPABASE_STORAGE] OK PDF encontrado: ...` (si se encontró)
- `ERROR: URL vacía para PDF ...` (si URL vacía)
- `ERROR: Descarga falló con código ...` (si descarga falló)

### Paso 4: Probar variaciones del nombre manualmente

```bash
# Desde el navegador, probar:
https://cotizador-cws.onrender.com/pdf/BMW-CWS-FM-002-R1-INSTALACIÓ
https://cotizador-cws.onrender.com/pdf/BMW-CWS-FM-002-R1-INSTALACIO
https://cotizador-cws.onrender.com/pdf/Cotizacion_BMW-CWS-FM-002-R1-INSTALACIÓ
```

---

## Soluciones Propuestas

### Solución 1: Si PDF no existe (Falla A)
**Regenerar el PDF:**
1. Ir a la cotización BMW en la interfaz
2. Crear revisión R2
3. Verificar en logs que se suba a Supabase Storage exitosamente
4. Confirmar que nueva revisión se puede abrir

### Solución 2: Si URL está vacía (Falla B)
**Revisar SupabaseStorageManager.buscar_pdfs():**
```python
# supabase_storage_manager.py:454-455
"ruta_completa": pdf.get("url", ""),  # Esta línea debe retornar URL válida
"url": pdf.get("url", ""),
```

Verificar que `listar_pdfs()` esté retornando URLs correctamente.

### Solución 3: Si descarga falla (Falla C)
**Verificar permisos del bucket:**
1. Ir a Supabase Dashboard → Storage → cotizaciones-pdfs
2. Verificar que políticas RLS permitan lectura pública
3. Probar URL directamente en navegador

### Solución 4: Si problema de encoding (Falla E)
**Normalizar nombres:**
Modificar generación de PDFs para evitar acentos en nombres de archivo:
```python
nombre_archivo = numero_cotizacion.replace('Ó', 'O').replace('ó', 'o')
```

---

## Próximos Pasos

**Necesito que me proporciones:**

1. **¿Qué mensaje exacto ves cuando intentas abrir el PDF?**
   - ¿404, 500, página en blanco, error de descarga?

2. **¿Qué aparece en la consola del navegador (F12)?**
   - Logs, errores, advertencias

3. **¿Qué dicen los logs de Render cuando intentas abrir el PDF?**
   - Buscar por "BMW" o "INSTALACIÓ" en logs recientes

Con esta información podré identificar exactamente en cuál de los puntos de falla A-E está ocurriendo el problema.
