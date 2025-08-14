#!/usr/bin/env python3
"""
Subir PDFs específicos a Cloudinary - version simple sin unicode
"""

import os
from pathlib import Path
from cloudinary_manager import CloudinaryManager

def upload_specific_pdfs():
    """Sube PDFs específicos desde Downloads a Cloudinary"""
    print("=" * 60)
    print("SUBIENDO PDFs A CLOUDINARY")
    print("=" * 60)
    
    # PDFs objetivo
    target_pdfs = [
        "BOB-CWS-CM-001-R1-ROBLOX",
        "BOB-CWS-CM-001-R2-ROBLOX"
    ]
    
    # Inicializar Cloudinary
    try:
        cloudinary_mgr = CloudinaryManager()
        if not cloudinary_mgr.is_available():
            print("ERROR: Cloudinary no disponible")
            return False
        print("OK: Cloudinary configurado correctamente")
    except Exception as e:
        print(f"ERROR: No se pudo inicializar Cloudinary: {e}")
        return False
    
    # Buscar archivos en Downloads
    downloads_path = Path("C:/Users/SDS/Downloads")
    found_files = []
    
    print(f"\nBuscando PDFs en: {downloads_path}")
    print("-" * 40)
    
    for pdf_name in target_pdfs:
        variations = [f"{pdf_name}.pdf", f"Cotizacion_{pdf_name}.pdf"]
        found = False
        
        for variation in variations:
            file_path = downloads_path / variation
            if file_path.exists():
                found_files.append({
                    "pdf_name": pdf_name,
                    "file_path": file_path,
                    "file_name": variation
                })
                print(f"[FOUND] {variation}")
                found = True
                break
        
        if not found:
            print(f"[NOT FOUND] {pdf_name}")
    
    if not found_files:
        print("\nERROR: No se encontraron PDFs para subir")
        return False
    
    print(f"\nSubiendo {len(found_files)} archivos...")
    print("=" * 40)
    
    # Subir cada archivo
    results = []
    
    for file_info in found_files:
        pdf_name = file_info["pdf_name"]
        file_path = file_info["file_path"]
        file_name = file_info["file_name"]
        
        print(f"\n[UPLOADING] {file_name}")
        
        try:
            # Obtener tamaño del archivo
            file_size = file_path.stat().st_size
            print(f"  Size: {file_size:,} bytes")
            
            # Subir a Cloudinary (carpeta nuevas)
            result = cloudinary_mgr.subir_pdf(
                archivo_local=str(file_path),
                numero_cotizacion=pdf_name,
                es_nueva=True
            )
            
            if result.get("success"):
                cloudinary_url = result.get("url")
                public_id = result.get("public_id")
                
                print(f"  [SUCCESS] Uploaded to Cloudinary")
                print(f"  URL: {cloudinary_url}")
                print(f"  Public ID: {public_id}")
                
                results.append({
                    "file": file_name,
                    "status": "SUCCESS",
                    "url": cloudinary_url,
                    "public_id": public_id
                })
                
            else:
                error = result.get("error", "Unknown error")
                print(f"  [ERROR] Upload failed: {error}")
                results.append({
                    "file": file_name,
                    "status": "ERROR",
                    "error": error
                })
                
        except Exception as e:
            print(f"  [EXCEPTION] {e}")
            results.append({
                "file": file_name,
                "status": "EXCEPTION",
                "error": str(e)
            })
    
    # Resumen final
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if r["status"] == "SUCCESS"]
    failed = [r for r in results if r["status"] != "SUCCESS"]
    
    print(f"SUCCESSFUL: {len(successful)}")
    for result in successful:
        print(f"  - {result['file']}: {result['url']}")
    
    if failed:
        print(f"\nFAILED: {len(failed)}")
        for result in failed:
            print(f"  - {result['file']}: {result.get('error', 'Unknown')}")
    
    print(f"\nTOTAL: {len(successful)}/{len(results)} files uploaded successfully")
    
    return len(successful) == len(results)

def verify_pdfs_in_cloudinary():
    """Verifica que los PDFs estén en Cloudinary"""
    print("\n" + "=" * 60)
    print("VERIFYING PDFs IN CLOUDINARY")
    print("=" * 60)
    
    try:
        cloudinary_mgr = CloudinaryManager()
        if not cloudinary_mgr.is_available():
            print("ERROR: Cloudinary no disponible")
            return False
        
        target_pdfs = [
            "BOB-CWS-CM-001-R1-ROBLOX",
            "BOB-CWS-CM-001-R2-ROBLOX"
        ]
        
        print("Searching for PDFs in Cloudinary...")
        print()
        
        all_found = True
        
        for pdf_name in target_pdfs:
            print(f"Checking: {pdf_name}")
            
            # Check in 'nuevas' folder
            found_nuevas = cloudinary_mgr.verificar_archivo_existe(pdf_name, "nuevas")
            
            # Check in 'antiguas' folder
            found_antiguas = cloudinary_mgr.verificar_archivo_existe(pdf_name, "antiguas")
            
            if found_nuevas:
                print(f"  [FOUND] in 'nuevas' folder")
            elif found_antiguas:
                print(f"  [FOUND] in 'antiguas' folder")
            else:
                print(f"  [NOT FOUND] in any folder")
                all_found = False
        
        print()
        if all_found:
            print("SUCCESS: ALL PDFs FOUND IN CLOUDINARY")
        else:
            print("WARNING: SOME PDFs NOT FOUND IN CLOUDINARY")
            
        return all_found
        
    except Exception as e:
        print(f"ERROR in verification: {e}")
        return False

if __name__ == "__main__":
    try:
        print("Starting PDF upload process...")
        
        # Upload PDFs
        upload_success = upload_specific_pdfs()
        
        if upload_success:
            # Verify upload
            verify_pdfs_in_cloudinary()
            
            print("\nSUCCESS: PROCESS COMPLETED")
            print("PDFs are now available in Cloudinary")
            
        else:
            print("\nERROR: PROCESS COMPLETED WITH ERRORS")
            print("Check the errors shown above")
            
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()