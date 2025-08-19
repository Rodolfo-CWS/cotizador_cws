# 🚀 Deployment Guide - Supabase Architecture

## 📋 Checklist de Deployment Completo

### ✅ Pre-Deployment

- [x] ✅ **Supabase Project**: Configurado con PostgreSQL
- [x] ✅ **Cloudinary Account**: 25GB storage configurado  
- [x] ✅ **GitHub Repository**: Código actualizado
- [x] ✅ **Render Service**: Conectado a GitHub
- [x] ✅ **Environment Variables**: Todas configuradas

### ⚙️ Environment Variables Required

```bash
# Supabase Database (Primary)
DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-1-us-east-2.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://[PROJECT_REF].supabase.co
SUPABASE_ANON_KEY=[YOUR_ANON_KEY]

# Cloudinary Storage (25GB Free)
CLOUDINARY_CLOUD_NAME=dvexwdihj
CLOUDINARY_API_KEY=685549632198419
CLOUDINARY_API_SECRET=[YOUR_SECRET]

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
APP_VERSION=2.1.0

# Google Drive (Optional Fallback)
GOOGLE_SERVICE_ACCOUNT_JSON=[SERVICE_ACCOUNT_JSON]
GOOGLE_DRIVE_FOLDER_NUEVAS=[FOLDER_ID]
GOOGLE_DRIVE_FOLDER_ANTIGUAS=[FOLDER_ID]
```

### 🛠️ Deployment Process

#### 1. **GitHub Push**
```bash
git add .
git commit -m "Deploy Supabase architecture v2.1.0"
git push origin main
```

#### 2. **Render Auto-Deploy**
- Render detecta cambios en GitHub
- Inicia build automáticamente
- Deploy toma 3-5 minutos

#### 3. **Verificación Post-Deploy**

**A. Health Check**
```bash
curl https://cotizador-cws.onrender.com/
# Debe responder con página principal
```

**B. Database Connection Test**
```bash
# En logs de Render debe aparecer:
[SUPABASE] Conectado a PostgreSQL exitosamente
# O para modo offline:
[SUPABASE] Activando modo offline
```

**C. Cloudinary Test**
```bash
# En logs debe aparecer:
OK: Cloudinary configurado correctamente
# Para indicar que Cloudinary está disponible
```

#### 4. **Test End-to-End**

**A. Crear Cotización de Prueba**
1. Ve a: https://cotizador-cws.onrender.com/formulario
2. Llena datos mínimos:
   - Cliente: TEST
   - Vendedor: DEPLOY
   - Proyecto: VERIFICATION
3. Clic en "Guardar Cotización"

**B. Verificar Resultado Esperado**
✅ **Success Response**:
```json
{
  "success": true,
  "mensaje": "Cotización guardada correctamente",
  "numeroCotizacion": "TEST-CWS-DEP-001-R1-VERIFICATION",
  "pdf_generado": true
}
```

❌ **Error Response** (si falla):
```json
{
  "success": false,
  "error": "Error details here"
}
```

## 🔍 Troubleshooting

### **HTTP 500 Errors**

**A. Check Environment Variables**
```bash
# En Render Dashboard > Environment
# Verificar que todas las variables están configuradas
# DATABASE_URL debe tener el formato correcto
```

**B. Check Logs**
```bash
# En Render Dashboard > Logs
# Buscar líneas que empiecen con:
[SUPABASE] Error conectando: ...
[CLOUDINARY] Error: ...
[FORMULARIO] ERROR CRITICO: ...
```

**C. Common Fixes**
```bash
# Password incorrecta en DATABASE_URL
# Región incorrecta (debe ser aws-1-us-east-2)  
# Protocolo incorrecto (debe ser postgresql://)
# Cloudinary API secret faltante
```

### **PDF Storage Issues**

**A. Cloudinary Not Working**
- Verificar CLOUDINARY_API_SECRET está configurado
- Ver logs para errores de autenticación
- Sistema funciona con almacenamiento local como fallback

**B. Google Drive Quota Exceeded**
- Normal en Service Accounts
- Cloudinary es el storage primario
- Local storage siempre funciona

### **Database Connection Issues**

**A. Supabase Offline**
- Sistema funciona en modo offline con JSON
- Verificar password y región en DATABASE_URL
- Modo offline es completamente funcional

**B. Migration Issues**
- Schema se crea automáticamente si no existe
- JSON data migra automáticamente cuando sea posible
- No se pierden datos

## 📊 Monitoring & Health Checks

### **System Health Endpoints**

```bash
# Basic health check
GET https://cotizador-cws.onrender.com/

# Database statistics  
GET https://cotizador-cws.onrender.com/admin/supabase/estado

# Storage statistics
GET https://cotizador-cws.onrender.com/admin/cloudinary/estado
```

### **Expected Responses**

**Healthy System:**
```json
{
  "status": "ok",
  "database": "supabase_online",
  "storage": "cloudinary_ok", 
  "total_quotations": 42,
  "storage_used": "125MB / 25GB"
}
```

**Degraded System (Still Working):**
```json
{
  "status": "degraded", 
  "database": "offline_mode",
  "storage": "local_only",
  "total_quotations": 42,
  "note": "System fully functional in offline mode"
}
```

## 🎯 Performance Optimization

### **Expected Performance**
- **Page Load**: < 2 seconds
- **Quotation Save**: < 3 seconds  
- **PDF Generation**: < 5 seconds
- **Search Results**: < 1 second

### **Optimization Tips**
```python
# Database indexing is already optimized
# Cloudinary CDN provides global performance
# Local JSON fallback ensures instant offline operations
# No additional optimization needed
```

## 🔄 Rollback Plan

### **If Deployment Fails**

1. **Immediate Rollback**
   ```bash
   # En Render Dashboard
   # Deployments > Previous Deploy > Redeploy
   ```

2. **Check Previous Working Commit**
   ```bash
   git log --oneline -10
   # Identificar último commit funcional
   git reset --hard [COMMIT_HASH]
   git push --force-with-lease
   ```

3. **Emergency Local Deployment**
   ```bash
   # Si Render falla completamente
   python app.py
   # Sistema funciona 100% en local
   ```

## 📚 Additional Resources

- **Full Architecture Guide**: `SUPABASE_ARCHITECTURE_GUIDE.md`
- **Configuration Test**: `python configure_permanent_storage.py`
- **Complete Documentation**: `CLAUDE.md`
- **Supabase Schema**: `supabase_schema.sql`

---

**Última actualización**: Agosto 19, 2025  
**Deployment Status**: ✅ Production Ready  
**Next Deploy**: Automático vía GitHub push