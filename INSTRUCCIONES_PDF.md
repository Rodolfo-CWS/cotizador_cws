# Instrucciones para habilitar la generación de PDF

## Dependencias requeridas

Para habilitar la generación de PDFs, necesitas instalar WeasyPrint:

### 1. Instalar WeasyPrint

```bash
pip install weasyprint
```

### 2. Dependencias del sistema (Windows)

Si estás en Windows, también necesitas instalar GTK3:

```bash
# Opción 1: Usando conda
conda install -c conda-forge weasyprint

# Opción 2: Usando pip con dependencias precompiladas
pip install --only-binary=all weasyprint
```

### 3. Dependencias del sistema (Linux)

```bash
# Ubuntu/Debian
sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

# CentOS/RHEL/Fedora
sudo yum install redhat-rpm-config python3-devel python3-pip python3-setuptools python3-wheel python3-cffi libffi-devel cairo-devel pango-devel gdk-pixbuf2-devel
```

### 4. Dependencias del sistema (macOS)

```bash
# Usando Homebrew
brew install cairo pango gdk-pixbuf libffi
```

### 5. Verificar instalación

Ejecuta este comando para verificar que WeasyPrint está correctamente instalado:

```python
python -c "import weasyprint; print('WeasyPrint instalado correctamente')"
```

### 6. Reiniciar la aplicación

Después de instalar WeasyPrint, reinicia el servidor Flask:

```bash
python app.py
```

## Solución de problemas

### Error: "No module named 'weasyprint'"
- Asegúrate de estar en el entorno virtual correcto
- Instala WeasyPrint usando pip install weasyprint

### Error: "Library not found" (Windows)
- Instala las dependencias GTK3 usando conda o pip con --only-binary=all

### Error de permisos (Linux/macOS)
- Usa sudo para instalar las dependencias del sistema
- O usa un entorno virtual con permisos de usuario

### PDF no se genera correctamente
- Verifica que todos los campos de la cotización estén completos
- Revisa los logs del servidor para errores específicos

## Características del PDF generado

✅ Formato oficial CWS Company  
✅ Encabezado con logo y datos de la empresa  
✅ Información completa del cliente y proyecto  
✅ Tabla detallada de items con materiales  
✅ Cálculos automáticos de subtotales, IVA y total  
✅ Términos y condiciones  
✅ Área de firma y datos del vendedor  
✅ Formato A4 optimizado para impresión  

## Uso

1. Completa y guarda una cotización en el formulario
2. Haz clic en "📄 Generar PDF"
3. El PDF se descargará automáticamente
4. El archivo tendrá el nombre: `Cotizacion_[NumeroCotizacion].pdf`
