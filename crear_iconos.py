#!/usr/bin/env python3
"""
Script para crear iconos profesionales para la app Sifra
"""

import os
from PIL import Image, ImageDraw, ImageFont
import requests

def crear_icono_sifra():
    """Crea un icono profesional Sifra si no existe logo"""
    try:
        # Verificar si ya existe el logo
        if os.path.exists('static/logo.png'):
            logo = Image.open('static/logo.png')
            print("✅ Logo existente encontrado")
        else:
            # Crear un icono simple con las letras SIFRA
            print("🎨 Creando icono Sifra...")
            logo = crear_icono_texto()
        
        # Redimensionar para diferentes tamaños
        tamaños = [16, 32, 48, 64, 128, 192, 256, 512]
        
        for tamaño in tamaños:
            icono = logo.resize((tamaño, tamaño), Image.Resampling.LANCZOS)
            icono.save(f'static/icon-{tamaño}.png', 'PNG')
            print(f"✅ Icono {tamaño}x{tamaño} creado")
        
        # Crear archivo .ico para Windows
        logo_ico = logo.resize((256, 256), Image.Resampling.LANCZOS)
        logo_ico.save('static/logo.ico', 'ICO')
        print("✅ Archivo .ico creado para Windows")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando iconos: {e}")
        return False

def crear_icono_texto():
    """Crea un icono con las letras SIFRA"""
    # Crear imagen base
    size = 512
    img = Image.new('RGBA', (size, size), (44, 82, 130, 255))  # Color azul Sifra
    draw = ImageDraw.Draw(img)
    
    # Intentar usar una fuente del sistema
    try:
        font = ImageFont.truetype("arial.ttf", size//4)
    except:
        try:
            font = ImageFont.truetype("calibri.ttf", size//4)
        except:
            font = ImageFont.load_default()
    
    # Dibujar texto SIFRA
    text = "SIFRA"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    # Sombra del texto
    draw.text((x+3, y+3), text, font=font, fill=(0, 0, 0, 128))
    # Texto principal
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    # Agregar borde circular
    draw.ellipse([10, 10, size-10, size-10], outline=(255, 255, 255, 100), width=8)
    
    return img

def instalar_pillow():
    """Instala Pillow si no está disponible"""
    try:
        import PIL
        return True
    except ImportError:
        print("📦 Instalando Pillow...")
        import subprocess
        import sys
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
            print("✅ Pillow instalado correctamente")
            return True
        except:
            print("❌ Error instalando Pillow")
            return False

def main():
    print("🎨 Sifra - Creador de Iconos Profesionales")
    print("=" * 50)
    
    if not instalar_pillow():
        print("❌ No se pudo instalar Pillow. Instálalo manualmente:")
        print("   pip install Pillow")
        return
    
    # Importar después de instalar
    global Image, ImageDraw, ImageFont
    from PIL import Image, ImageDraw, ImageFont
    
    if crear_icono_sifra():
        print("\n🎉 ¡Iconos creados exitosamente!")
        print("📁 Ubicación: static/")
        print("📋 Archivos creados:")
        print("   - icon-16.png hasta icon-512.png")
        print("   - logo.ico (para Windows)")
    else:
        print("\n❌ Error creando iconos")

if __name__ == "__main__":
    main()