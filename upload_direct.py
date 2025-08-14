#!/usr/bin/env python3
"""
Upload directo a Cloudinary sin managers intermedios
"""

import cloudinary
import cloudinary.uploader
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def upload_pdf_direct():
    """Sube PDFs directamente a Cloudinary"""
    print("=" * 50)
    print("UPLOAD DIRECTO A CLOUDINARY")
    print("=" * 50)
    
    # Configurar Cloudinary
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET'),
        secure=True
    )
    
    print(f"Cloud: {os.getenv('CLOUDINARY_CLOUD_NAME')}")
    print()
    
    # Archivos a subir
    target_files = [
        ("BOB-CWS-CM-001-R1-ROBLOX", "C:/Users/SDS/Downloads/Cotizacion_BOB-CWS-CM-001-R1-ROBLOX.pdf"),
        ("BOB-CWS-CM-001-R2-ROBLOX", "C:/Users/SDS/Downloads/Cotizacion_BOB-CWS-CM-001-R2-ROBLOX.pdf")
    ]
    
    results = []
    
    for pdf_name, file_path in target_files:
        print(f"[UPLOADING] {pdf_name}")
        
        # Verificar que archivo existe
        if not Path(file_path).exists():
            print(f"  [ERROR] File not found: {file_path}")
            results.append({"name": pdf_name, "status": "NOT_FOUND"})
            continue
        
        try:
            # Subir a Cloudinary
            upload_result = cloudinary.uploader.upload(
                file_path,
                public_id=f"cotizaciones/nuevas/{pdf_name}",
                resource_type="raw",  # Para PDFs
                format="pdf",
                overwrite=True
            )
            
            print(f"  [SUCCESS] Uploaded")
            print(f"  URL: {upload_result.get('secure_url', 'N/A')}")
            print(f"  Public ID: {upload_result.get('public_id', 'N/A')}")
            print(f"  Format: {upload_result.get('format', 'N/A')}")
            print(f"  Size: {upload_result.get('bytes', 0):,} bytes")
            
            results.append({
                "name": pdf_name,
                "status": "SUCCESS",
                "url": upload_result.get('secure_url'),
                "public_id": upload_result.get('public_id'),
                "size": upload_result.get('bytes', 0)
            })
            
        except Exception as e:
            print(f"  [ERROR] Upload failed: {e}")
            results.append({
                "name": pdf_name,
                "status": "ERROR",
                "error": str(e)
            })
        
        print()
    
    # Resumen
    print("=" * 50)
    print("UPLOAD RESULTS")
    print("=" * 50)
    
    successful = [r for r in results if r["status"] == "SUCCESS"]
    failed = [r for r in results if r["status"] != "SUCCESS"]
    
    print(f"SUCCESSFUL: {len(successful)}")
    for result in successful:
        print(f"  {result['name']}: {result['url']}")
    
    if failed:
        print(f"FAILED: {len(failed)}")
        for result in failed:
            print(f"  {result['name']}: {result.get('error', result['status'])}")
    
    return len(successful) == len(target_files)

def verify_uploads():
    """Verifica que los uploads estén en Cloudinary"""
    print("\n" + "=" * 50)
    print("VERIFYING UPLOADS")
    print("=" * 50)
    
    import cloudinary.api
    
    target_public_ids = [
        "cotizaciones/nuevas/BOB-CWS-CM-001-R1-ROBLOX",
        "cotizaciones/nuevas/BOB-CWS-CM-001-R2-ROBLOX"
    ]
    
    all_found = True
    
    for public_id in target_public_ids:
        try:
            resource = cloudinary.api.resource(public_id, resource_type="raw")
            print(f"[FOUND] {public_id}")
            print(f"  URL: {resource.get('secure_url', 'N/A')}")
            print(f"  Size: {resource.get('bytes', 0):,} bytes")
            print(f"  Created: {resource.get('created_at', 'N/A')}")
        except Exception as e:
            print(f"[NOT FOUND] {public_id}: {e}")
            all_found = False
        print()
    
    return all_found

if __name__ == "__main__":
    try:
        # Upload PDFs
        success = upload_pdf_direct()
        
        if success:
            print("\nVERIFYING UPLOADS...")
            verify_uploads()
            print("SUCCESS: All PDFs uploaded and verified!")
        else:
            print("ERROR: Some uploads failed")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()