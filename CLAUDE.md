# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CWS Cotizador** - Professional quotation system for CWS Company with automated PDF generation, hybrid database architecture, and production deployment on Render.

**Production URL**: https://cotizador-cws.onrender.com/

## Quick Start Commands

### Development (Local)
```bash
# Quick start (recommended)
EJECUTAR_RAPIDO.bat

# Manual start
cd C:\Users\SDS\cotizador_cws
env\Scripts\activate
python app.py
```

### First Time Setup
```bash
# Automatic installation
INSTALAR_AUTOMATICO.bat
```

### Testing and Validation
```bash
# Complete system test
python test_completo.py

# PDF generation test  
python test_pdf_completo.py

# Server connectivity test
python test_servidor.py

# Verify PDF libraries
python -c "import weasyprint; print('WeasyPrint OK')"
python -c "import reportlab; print('ReportLab OK')"
```

## Production Deployment (Render)

### Current Deployment
- **Live URL**: https://cotizador-cws.onrender.com/
- **Platform**: Render.com
- **Server**: Gunicorn (configured in `Procfile`)
- **Python Version**: Specified in `runtime.txt`

### Deployment Process
```bash
# See detailed instructions in:
# - DEPLOY_RENDER.md (comprehensive guide)
# - RENDER_UPLOAD_DIRECTO.md (direct upload method)
```

### Production Environment Variables
- `MONGODB_URI` - Complete MongoDB connection string for production
- `FLASK_ENV=production` - Production mode configuration
- Other environment variables configured in Render dashboard

## Core Architecture

### Application Stack
- **Frontend**: HTML/CSS/JavaScript with Jinja2 templates
- **Backend**: Python Flask web framework
- **Database**: Hybrid MongoDB (primary) + JSON offline (fallback)
- **PDF Generation**: ReportLab (primary) + WeasyPrint (fallback)
- **File Storage**: Google Drive integration + local folders

### Key Technical Patterns
- **Fallback Systems**: If MongoDB fails → JSON offline, if ReportLab fails → WeasyPrint
- **Automatic Numbering**: `Cliente-CWS-VendedorIniciales-###-R#-Proyecto`
- **Revision Control**: Automatic versioning (R1, R2, R3...) with mandatory justification for R2+
- **Professional PDF**: Corporate CWS design with logo, colors, and structured layout

### File Structure
```
cotizador_cws/
├── app.py                    # Main Flask application with routes
├── database.py               # Hybrid database manager (MongoDB/JSON)
├── pdf_manager.py            # PDF generation and Google Drive storage  
├── config.py                 # Environment-based configuration
├── google_drive_client.py    # Google Drive API integration
├── requirements.txt          # Python dependencies
├── Procfile                  # Render deployment configuration
├── runtime.txt               # Python version for Render
└── templates/                # Jinja2 HTML templates
    ├── home.html            # Main landing page
    ├── formulario.html      # Quotation form
    ├── formato_pdf_cws.html # PDF template
    └── ver_cotizacion.html  # Quotation viewer
```

## Database Architecture

### MongoDB (Primary)
- **Connection**: Environment variable `MONGODB_URI` (production) or component variables (development)
- **Collections**: `cotizaciones`, `pdf_files` 
- **Features**: Automatic indexing, search capabilities, revision tracking

### JSON Offline (Fallback)
- **File**: `cotizaciones_offline.json`
- **Purpose**: Ensures system works without internet/MongoDB connection
- **Sync**: Automatic bidirectional synchronization when MongoDB available

## PDF Generation System

### ReportLab (Primary Engine)
- **Professional format** with CWS corporate design
- **Features**: Logo, colors, structured tables, financial summaries
- **Automatic storage** in Google Drive and local folders

### WeasyPrint (Fallback Engine)
- **HTML to PDF** conversion using `formato_pdf_cws.html`
- **Installation**: May require system dependencies (see `INSTRUCCIONES_PDF.md`)

### PDF Storage
- **Google Drive**: `G:\Mi unidad\CWS\CWS_Cotizaciones_PDF\nuevas\`
- **Local Backup**: Project-relative folders
- **MongoDB Index**: Searchable metadata for all PDFs

## Quotation System Features

### Automatic Numbering
- **Format**: `CLIENTE-CWS-VendedorIniciales-###-R#-PROYECTO`
- **Sequential**: Auto-incremented per vendor and client
- **Immutable**: Field disabled in frontend to prevent manual editing

### Revision System  
- **Automatic versioning**: R1 → R2 → R3...
- **Mandatory justification**: Required for revisions ≥ R2
- **Data preservation**: Original data maintained through revision history

### Dynamic Form
- **Real-time calculations**: Subtotals, taxes, totals update automatically
- **Dynamic items**: Add/remove quotation items with materials
- **Validation**: Comprehensive client and server-side validation

## Windows Integration

### Batch Files for Different Scenarios
- `EJECUTAR_RAPIDO.bat` - Quick local development
- `EJECUTAR_EN_RED.bat` - Network accessible mode
- `CONFIGURAR_ACCESO_MOVIL.bat` - Mobile device access setup
- `DIAGNOSTICAR_RED.bat` - Network troubleshooting
- `INSTALAR_AUTOMATICO.bat` - Complete setup automation

### Desktop Integration
- `crear_accesos_directos.bat` - Create desktop shortcuts
- `INSTALAR_APP_ESCRITORIO.bat` - Desktop app installation
- `auto_inicio_windows.bat` - Windows startup configuration

## Development Workflow

### Making Changes
1. Activate environment: `env\Scripts\activate`
2. Run tests: `python test_completo.py`
3. Test locally: `python app.py`
4. Verify PDF generation: `python test_pdf_completo.py`
5. Deploy to Render: Follow `DEPLOY_RENDER.md`

### Common Tasks
- **Add new quotation fields**: Modify `templates/formulario.html` and `app.py` routes
- **Update PDF format**: Edit `pdf_manager.py` (ReportLab) or `templates/formato_pdf_cws.html` (WeasyPrint)
- **Database changes**: Update `database.py` with proper fallback handling
- **New integrations**: Follow existing fallback patterns

## Environment Configuration

### Local Development
```env
FLASK_DEBUG=True
MONGO_USERNAME=admin
MONGO_PASSWORD=ADMIN123
MONGO_CLUSTER=cluster0.t4e0tp8.mongodb.net
MONGO_DATABASE=cotizaciones
```

### Production (Render)
```env
FLASK_ENV=production
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database
```

## Important Notes

- **Always test PDF generation** after changes - it's a core feature
- **Maintain fallback systems** - users expect offline functionality
- **Preserve numbering system** - critical for CWS business process
- **Test on Windows** - primary deployment environment for local users
- **Monitor Render logs** - production deployment requires monitoring

## Troubleshooting

### PDF Generation Issues
- Verify libraries: Check both ReportLab and WeasyPrint installation
- Check file paths: Ensure Google Drive path is accessible
- Test locally: Use `test_pdf_completo.py`

### Database Connection Problems  
- MongoDB connection: Verify `MONGODB_URI` or component variables
- Offline mode: System automatically falls back to JSON storage
- Sync issues: Check `database.py` logs for synchronization status

### Render Deployment Issues
- Check `Procfile` configuration
- Verify `requirements.txt` has all dependencies
- Monitor Render build logs
- Ensure environment variables are set correctly