# 🔧 Cloudinary Troubleshooting Guide

## Overview

Comprehensive guide for diagnosing and resolving Cloudinary API issues in the hybrid system.

## 🚨 Common Issues and Solutions

### Issue 1: "Error 401 - api_secret mismatch"

**Symptoms:**
- Cloudinary operations fail with authentication errors
- Test scripts show "api_secret mismatch"
- PDFs fall back to Google Drive/Local storage

**Root Causes:**
1. **New Account Propagation** (Most Common)
   - API credentials need 15-30 minutes to propagate globally
   - Account created recently may have temporary authentication delays

2. **Incorrect Credentials**
   - Typos in API key or secret
   - Wrong cloud name
   - Copy-paste errors with hidden characters

3. **Environment Variable Issues**
   - Variables not loaded properly
   - Cached old values
   - Different values between local and production

**Solutions:**

#### A. Wait for Propagation (Recommended First Step)
```bash
# If account created within last 24 hours, wait and retry
# New Cloudinary accounts typically need 15-30 minutes for full activation
```

#### B. Verify Credentials
```bash
# 1. Check credentials format
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Cloud Name:', os.getenv('CLOUDINARY_CLOUD_NAME'))
print('API Key:', os.getenv('CLOUDINARY_API_KEY'))
print('API Secret:', os.getenv('CLOUDINARY_API_SECRET')[:8] + '...')
print('Lengths:', len(os.getenv('CLOUDINARY_CLOUD_NAME', '')), len(os.getenv('CLOUDINARY_API_KEY', '')), len(os.getenv('CLOUDINARY_API_SECRET', '')))
"
```

#### C. Test Direct API Access
```bash
# Test with cURL to bypass Python SDK
curl -X GET \
  "https://api.cloudinary.com/v1_1/YOUR_CLOUD_NAME/resources/raw" \
  -u "YOUR_API_KEY:YOUR_API_SECRET"
```

#### D. Regenerate API Credentials
1. Go to Cloudinary dashboard: https://cloudinary.com/console
2. Settings → API Keys
3. Click "Generate New API Key"
4. Update environment variables with new credentials

### Issue 2: Rate Limiting or Quota Exceeded

**Symptoms:**
- "Rate limit exceeded" errors
- "Quota exceeded" messages
- Intermittent failures during testing

**Solutions:**

#### A. Check Account Usage
```bash
python -c "
from cloudinary_manager import CloudinaryManager
manager = CloudinaryManager()
if manager.is_available():
    stats = manager.obtener_estadisticas()
    print('Usage:', stats)
"
```

#### B. Implement Retry Logic (Already Implemented)
The hybrid system includes automatic retry with exponential backoff:
- 3 retry attempts
- 2-second base delay with exponential increase
- Only retries network-related errors

#### C. Monitor Usage
- Free tier: 25GB storage, 25 credits/month
- Monitor via `/admin/cloudinary/estado` endpoint

### Issue 3: Network Connectivity Issues

**Symptoms:**
- Timeout errors
- Connection refused
- Intermittent failures

**Solutions:**

#### A. Test Network Connectivity
```bash
# Test basic connectivity
ping api.cloudinary.com

# Test HTTPS access
curl -I https://api.cloudinary.com/v1_1/dvexwdihj/image/upload
```

#### B. Check Firewall/Proxy Settings
- Ensure outbound HTTPS (port 443) is allowed
- Check corporate proxy settings
- Verify DNS resolution

### Issue 4: Upload Failures

**Symptoms:**
- Files upload but return errors
- Partial uploads
- Invalid file format errors

**Solutions:**

#### A. Verify File Format
```bash
# Test with minimal PDF
python -c "
import tempfile
from cloudinary_manager import CloudinaryManager

# Create minimal valid PDF
pdf_content = b'%PDF-1.4\n1 0 obj<</Type/Page>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF'

# Test upload
manager = CloudinaryManager()
if manager.is_available():
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
        f.write(pdf_content)
        f.flush()
        result = manager.subir_pdf(f.name, 'TEST-PDF-001', True)
        print('Result:', result)
"
```

#### B. Check File Size Limits
- Free tier: 10MB per file limit
- Ensure PDFs are within limits

## 🔧 Diagnostic Tools

### 1. Complete System Test
```bash
# Run comprehensive Cloudinary test
python test_cloudinary.py
```

### 2. Quick Connection Test
```bash
# Fast connectivity check
python -c "from cloudinary_manager import test_cloudinary_connection; test_cloudinary_connection()"
```

### 3. Environment Verification
```bash
# Check all environment variables
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

required_vars = ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']
for var in required_vars:
    value = os.getenv(var)
    status = 'OK' if value else 'MISSING'
    length = len(value) if value else 0
    print(f'{var}: {status} (length: {length})')
"
```

### 4. Test with Real Credentials
```bash
# Test with manual credential entry
python -c "
import cloudinary
import cloudinary.api

# Replace with your actual credentials
cloudinary.config(
    cloud_name='dvexwdihj',
    api_key='685549632198419',
    api_secret='h1ZIyNA6M7POz6-FwyiOacGVt2U'
)

try:
    result = cloudinary.api.ping()
    print('SUCCESS:', result)
except Exception as e:
    print('ERROR:', e)
"
```

## 📋 Expected Timeline

### New Account Activation:
- **Immediate**: Account creation and dashboard access
- **0-15 minutes**: Basic API access (upload/download)
- **15-30 minutes**: Full API functionality
- **1-24 hours**: Complete global propagation

### Error Resolution:
- **Authentication**: Usually resolves within 30 minutes
- **Rate limits**: Reset every 24 hours
- **Network issues**: Check connectivity and retry

## 🔄 Fallback System

The hybrid system automatically handles Cloudinary failures:

1. **Primary**: Attempt Cloudinary upload
2. **Fallback**: Use Google Drive if Cloudinary fails
3. **Emergency**: Local storage as last resort
4. **Recovery**: Retry Cloudinary on next operation

### Verify Fallback Works:
```bash
# Test complete PDF storage system
python -c "
from pdf_manager import PDFManager
from database import DatabaseManager
import datetime

db = DatabaseManager()
pdf_manager = PDFManager(db)

# Create test PDF
pdf_content = b'%PDF-1.4\n1 0 obj<</Type/Page>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF'

# Test cotization data
cotizacion = {
    'numeroCotizacion': f'TEST-{datetime.datetime.now().strftime(\"%H%M%S\")}',
    'datosGenerales': {'cliente': 'Test Cliente', 'proyecto': 'Test Project'}
}

# Test storage with fallbacks
result = pdf_manager.almacenar_pdf_nuevo(pdf_content, cotizacion)
print('Storage result:', result.get('estado'))
print('Systems used:', list(result.get('sistemas', {}).keys()))
"
```

## 🎯 Best Practices

### 1. Production Deployment:
- Always test credentials in staging first
- Use environment-specific API keys
- Monitor usage and quotas regularly

### 2. Error Handling:
- Implement graceful degradation
- Log all API failures for analysis
- Use retry logic with exponential backoff

### 3. Monitoring:
- Check `/admin/cloudinary/estado` regularly
- Set up alerts for quota usage
- Monitor fallback system usage

### 4. Security:
- Never commit API secrets to git
- Use environment variables only
- Rotate credentials periodically

## 📞 Support Resources

### Cloudinary Support:
- Documentation: https://cloudinary.com/documentation
- Support: https://support.cloudinary.com
- Status Page: https://status.cloudinary.com

### System-Specific:
- Test suite: `python test_cloudinary.py`
- Admin panel: `/admin/cloudinary/estado`
- Logs: Check application logs for detailed error messages

### Emergency Contacts:
- If Cloudinary completely fails, the system will automatically use Google Drive
- All PDFs are guaranteed to be stored via the fallback system
- Contact system administrator if all storage systems fail

---

**Remember: The hybrid system is designed to be resilient. Even if Cloudinary has issues, your PDFs will still be stored and accessible through the fallback systems.**