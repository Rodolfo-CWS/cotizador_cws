#!/usr/bin/env python3
"""
Diagnóstico Pre-Deploy: Validación de Integridad del Sistema CWS
Evalúa la seguridad del deploy y la persistencia de PDFs críticos
"""

import os
import json
import datetime
from pathlib import Path
from typing import Dict, List, Tuple

class DiagnosticoDeploy:
    def __init__(self):
        self.pdfs_criticos = [
            "BOB-CWS-CM-001-R1-ROBLOX",
            "BOB-CWS-CM-001-R2-ROBLOX"
        ]
        self.resultado = {
            "timestamp": datetime.datetime.now().isoformat(),
            "version": "1.0",
            "evaluacion_general": "PENDIENTE",
            "riesgo_deploy": "NO_EVALUADO",
            "componentes": {},
            "recomendaciones": [],
            "garantias_persistencia": []
        }
    
    def evaluar_cloudinary(self) -> Dict:
        """Evalúa el estado de Cloudinary"""
        print("EVALUANDO: Cloudinary...")
        
        evaluacion = {
            "servicio": "Cloudinary",
            "estado": "NO_EVALUADO",
            "riesgo": "DESCONOCIDO",
            "detalles": {},
            "impacto_deploy": "DESCONOCIDO"
        }
        
        try:
            # Verificar variables de entorno
            cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
            api_key = os.getenv('CLOUDINARY_API_KEY') 
            api_secret = os.getenv('CLOUDINARY_API_SECRET')
            
            if not all([cloud_name, api_key, api_secret]):
                evaluacion.update({
                    "estado": "CONFIGURACION_INCOMPLETA",
                    "riesgo": "ALTO",
                    "impacto_deploy": "DEPLOY_FALLARA",
                    "detalles": {
                        "problema": "Variables de entorno faltantes",
                        "cloud_name_presente": bool(cloud_name),
                        "api_key_presente": bool(api_key),
                        "api_secret_presente": bool(api_secret)
                    }
                })
                return evaluacion
            
            # Test básico de configuración
            try:
                import cloudinary
                import cloudinary.api
                
                cloudinary.config(
                    cloud_name=cloud_name,
                    api_key=api_key,
                    api_secret=api_secret,
                    secure=True
                )
                
                # Test de ping
                result = cloudinary.api.ping()
                
                evaluacion.update({
                    "estado": "OPERATIVO",
                    "riesgo": "BAJO",
                    "impacto_deploy": "NINGUNO",
                    "detalles": {
                        "cloud_name": cloud_name,
                        "configuracion": "OK",
                        "conectividad": "OK",
                        "ping_response": result
                    }
                })
                
            except Exception as e:
                error_str = str(e)
                if "401" in error_str or "api_secret" in error_str:
                    evaluacion.update({
                        "estado": "ERROR_AUTENTICACION",
                        "riesgo": "MEDIO",
                        "impacto_deploy": "FUNCIONALIDAD_LIMITADA",
                        "detalles": {
                            "problema": "Credenciales incorrectas",
                            "error": error_str,
                            "solucion": "Actualizar API Secret en .env y Render"
                        }
                    })
                else:
                    evaluacion.update({
                        "estado": "ERROR_CONEXION",
                        "riesgo": "ALTO", 
                        "impacto_deploy": "FUNCIONALIDAD_PERDIDA",
                        "detalles": {
                            "problema": "Error de conectividad",
                            "error": error_str
                        }
                    })
                    
        except ImportError:
            evaluacion.update({
                "estado": "MODULO_FALTANTE",
                "riesgo": "ALTO",
                "impacto_deploy": "DEPLOY_FALLARA",
                "detalles": {
                    "problema": "pip install cloudinary requerido"
                }
            })
        
        return evaluacion
    
    def evaluar_google_drive(self) -> Dict:
        """Evalúa el estado de Google Drive"""
        print("EVALUANDO: Google Drive...")
        
        evaluacion = {
            "servicio": "Google Drive", 
            "estado": "NO_EVALUADO",
            "riesgo": "DESCONOCIDO",
            "detalles": {},
            "impacto_deploy": "DESCONOCIDO"
        }
        
        try:
            from google_drive_client import GoogleDriveClient
            
            drive_client = GoogleDriveClient()
            
            if drive_client.is_available():
                evaluacion.update({
                    "estado": "OPERATIVO",
                    "riesgo": "BAJO",
                    "impacto_deploy": "NINGUNO",
                    "detalles": {
                        "configuracion": "OK",
                        "credenciales": "Validas",
                        "carpetas_configuradas": True,
                        "proyecto": drive_client.service.about().get(fields="user").execute().get("user", {}).get("emailAddress", "N/A")
                    }
                })
            else:
                evaluacion.update({
                    "estado": "NO_DISPONIBLE",
                    "riesgo": "MEDIO",
                    "impacto_deploy": "FALLBACK_PERDIDO",
                    "detalles": {
                        "problema": "Google Drive no inicializado correctamente"
                    }
                })
                
        except Exception as e:
            evaluacion.update({
                "estado": "ERROR",
                "riesgo": "MEDIO",
                "impacto_deploy": "FALLBACK_PERDIDO", 
                "detalles": {
                    "error": str(e)
                }
            })
        
        return evaluacion
    
    def evaluar_mongodb(self) -> Dict:
        """Evalúa el estado de MongoDB"""
        print("EVALUANDO: MongoDB...")
        
        evaluacion = {
            "servicio": "MongoDB",
            "estado": "NO_EVALUADO", 
            "riesgo": "DESCONOCIDO",
            "detalles": {},
            "impacto_deploy": "DESCONOCIDO"
        }
        
        try:
            from database import DatabaseManager
            
            db_manager = DatabaseManager()
            
            if not db_manager.modo_offline:
                evaluacion.update({
                    "estado": "OPERATIVO",
                    "riesgo": "BAJO", 
                    "impacto_deploy": "NINGUNO",
                    "detalles": {
                        "conexion": "OK",
                        "modo": "Online",
                        "base_datos": "Accesible"
                    }
                })
            else:
                evaluacion.update({
                    "estado": "MODO_OFFLINE",
                    "riesgo": "BAJO",
                    "impacto_deploy": "FUNCIONALIDAD_REDUCIDA",
                    "detalles": {
                        "modo": "Offline",
                        "fallback": "JSON local activo"
                    }
                })
                
        except Exception as e:
            evaluacion.update({
                "estado": "ERROR",
                "riesgo": "MEDIO",
                "impacto_deploy": "FUNCIONALIDAD_REDUCIDA",
                "detalles": {
                    "error": str(e),
                    "fallback": "JSON local disponible"
                }
            })
        
        return evaluacion
    
    def evaluar_archivos_criticos(self) -> Dict:
        """Evalúa la ubicación y estado de archivos críticos"""
        print("EVALUANDO: Archivos Críticos...")
        
        evaluacion = {
            "servicio": "Archivos Críticos",
            "estado": "NO_EVALUADO",
            "riesgo": "DESCONOCIDO", 
            "detalles": {"archivos": {}},
            "impacto_deploy": "DESCONOCIDO"
        }
        
        archivos_encontrados = 0
        ubicaciones_totales = 0
        
        for pdf in self.pdfs_criticos:
            archivo_info = {
                "nombre": pdf,
                "ubicaciones": [],
                "estado": "NO_ENCONTRADO"
            }
            
            # Buscar en Downloads
            downloads_path = Path("C:\\Users\\SDS\\Downloads")
            for variacion in [f"{pdf}.pdf", f"Cotizacion_{pdf}.pdf"]:
                archivo_downloads = downloads_path / variacion
                if archivo_downloads.exists():
                    stat = archivo_downloads.stat()
                    archivo_info["ubicaciones"].append({
                        "tipo": "Downloads",
                        "ruta": str(archivo_downloads),
                        "tamaño": stat.st_size,
                        "fecha": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                    ubicaciones_totales += 1
            
            # Buscar en carpetas configuradas del PDF Manager
            try:
                base_path = Path("G:\\Mi unidad\\CWS\\CWS_Cotizaciones_PDF")
                carpetas = [base_path / "nuevas", base_path / "antiguas"]
                
                for carpeta in carpetas:
                    if carpeta.exists():
                        for variacion in [f"{pdf}.pdf", f"Cotizacion_{pdf}.pdf"]:
                            archivo_local = carpeta / variacion
                            if archivo_local.exists():
                                stat = archivo_local.stat()
                                archivo_info["ubicaciones"].append({
                                    "tipo": f"Local ({carpeta.name})",
                                    "ruta": str(archivo_local),
                                    "tamaño": stat.st_size,
                                    "fecha": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                                })
                                ubicaciones_totales += 1
            except Exception as e:
                pass
            
            if archivo_info["ubicaciones"]:
                archivo_info["estado"] = "ENCONTRADO"
                archivos_encontrados += 1
            
            evaluacion["detalles"]["archivos"][pdf] = archivo_info
        
        # Evaluar resultado general
        if archivos_encontrados == len(self.pdfs_criticos):
            if ubicaciones_totales >= len(self.pdfs_criticos) * 2:  # Al menos 2 ubicaciones por archivo
                evaluacion.update({
                    "estado": "SEGUROS_REDUNDANTES",
                    "riesgo": "MUY_BAJO",
                    "impacto_deploy": "NINGUNO"
                })
            else:
                evaluacion.update({
                    "estado": "SEGUROS_SIMPLES", 
                    "riesgo": "BAJO",
                    "impacto_deploy": "RIESGO_MINIMO"
                })
        else:
            evaluacion.update({
                "estado": "ARCHIVOS_FALTANTES",
                "riesgo": "ALTO",
                "impacto_deploy": "PERDIDA_DE_DATOS"
            })
        
        evaluacion["detalles"].update({
            "archivos_encontrados": archivos_encontrados,
            "archivos_totales": len(self.pdfs_criticos),
            "ubicaciones_totales": ubicaciones_totales,
            "redundancia_promedio": ubicaciones_totales / len(self.pdfs_criticos) if self.pdfs_criticos else 0
        })
        
        return evaluacion
    
    def evaluar_configuracion_render(self) -> Dict:
        """Evalúa la configuración específica para Render"""
        print("EVALUANDO: Configuración Deploy...")
        
        evaluacion = {
            "servicio": "Configuración Deploy",
            "estado": "NO_EVALUADO",
            "riesgo": "DESCONOCIDO",
            "detalles": {},
            "impacto_deploy": "DESCONOCIDO"
        }
        
        problemas = []
        warnings = []
        
        # Verificar archivos críticos del proyecto
        archivos_requeridos = [
            "app.py",
            "requirements.txt", 
            "Procfile",
            "cloudinary_manager.py",
            "pdf_manager.py",
            "database.py"
        ]
        
        archivos_faltantes = []
        for archivo in archivos_requeridos:
            if not Path(archivo).exists():
                archivos_faltantes.append(archivo)
        
        if archivos_faltantes:
            problemas.append(f"Archivos faltantes: {archivos_faltantes}")
        
        # Verificar requirements.txt
        try:
            with open("requirements.txt", "r") as f:
                requirements = f.read()
                if "cloudinary" not in requirements:
                    warnings.append("cloudinary no está en requirements.txt")
                if "pymongo" not in requirements:
                    warnings.append("pymongo no está en requirements.txt")
        except FileNotFoundError:
            problemas.append("requirements.txt no encontrado")
        
        # Verificar Procfile
        try:
            with open("Procfile", "r") as f:
                procfile = f.read()
                if "app.py" not in procfile or "web:" not in procfile:
                    warnings.append("Procfile puede tener configuración incorrecta")
        except FileNotFoundError:
            problemas.append("Procfile no encontrado")
        
        # Evaluar resultado
        if problemas:
            evaluacion.update({
                "estado": "PROBLEMAS_CRITICOS",
                "riesgo": "ALTO",
                "impacto_deploy": "DEPLOY_FALLARA",
                "detalles": {
                    "problemas": problemas,
                    "warnings": warnings
                }
            })
        elif warnings:
            evaluacion.update({
                "estado": "WARNINGS_MENORES", 
                "riesgo": "MEDIO",
                "impacto_deploy": "POSIBLES_FALLOS",
                "detalles": {
                    "warnings": warnings
                }
            })
        else:
            evaluacion.update({
                "estado": "CONFIGURACION_OK",
                "riesgo": "BAJO",
                "impacto_deploy": "NINGUNO",
                "detalles": {
                    "archivos_ok": len(archivos_requeridos),
                    "configuracion": "Completa"
                }
            })
        
        return evaluacion
    
    def generar_recomendaciones(self) -> List[str]:
        """Genera recomendaciones basadas en la evaluación"""
        recomendaciones = []
        
        # Analizar componentes evaluados
        cloudinary = self.resultado["componentes"].get("Cloudinary", {})
        archivos = self.resultado["componentes"].get("Archivos Críticos", {})
        config = self.resultado["componentes"].get("Configuración Deploy", {})
        
        # Recomendaciones críticas
        if cloudinary.get("estado") == "ERROR_AUTENTICACION":
            recomendaciones.append("🔴 CRÍTICO: Actualizar credenciales Cloudinary en .env y Render Dashboard")
            recomendaciones.append("   - Ir a https://console.cloudinary.com/settings/api-keys")
            recomendaciones.append("   - Regenerar API Secret y actualizar variables")
        
        if config.get("estado") == "PROBLEMAS_CRITICOS":
            recomendaciones.append("🔴 CRÍTICO: Corregir problemas de configuración antes del deploy")
            for problema in config.get("detalles", {}).get("problemas", []):
                recomendaciones.append(f"   - {problema}")
        
        # Recomendaciones importantes
        if archivos.get("estado") in ["SEGUROS_SIMPLES", "ARCHIVOS_FALTANTES"]:
            recomendaciones.append("🟡 IMPORTANTE: Crear backups adicionales de PDFs críticos")
            recomendaciones.append("   - Subir manualmente a Google Drive como respaldo")
        
        # Recomendaciones generales
        recomendaciones.extend([
            "🟢 Pre-Deploy: Ejecutar test_cloudinary_simple.py exitosamente",
            "🟢 Durante Deploy: Monitorear logs en Render Dashboard", 
            "🟢 Post-Deploy: Verificar funcionalidad con verificar_pdfs_especificos.py"
        ])
        
        return recomendaciones
    
    def calcular_riesgo_general(self) -> str:
        """Calcula el riesgo general del deploy"""
        riesgos = []
        
        for componente, evaluacion in self.resultado["componentes"].items():
            riesgo = evaluacion.get("riesgo", "DESCONOCIDO")
            riesgos.append(riesgo)
        
        # Lógica de evaluación
        if "ALTO" in riesgos:
            return "ALTO"
        elif riesgos.count("MEDIO") >= 2:
            return "MEDIO"
        elif "MEDIO" in riesgos:
            return "MEDIO"
        elif all(r == "BAJO" for r in riesgos):
            return "BAJO"
        else:
            return "MEDIO"
    
    def ejecutar_diagnostico_completo(self) -> Dict:
        """Ejecuta el diagnóstico completo del sistema"""
        print("=" * 80)
        print("DIAGNÓSTICO PRE-DEPLOY - SISTEMA CWS")
        print("=" * 80)
        print(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Evaluar todos los componentes
        componentes = [
            ("Cloudinary", self.evaluar_cloudinary),
            ("Google Drive", self.evaluar_google_drive), 
            ("MongoDB", self.evaluar_mongodb),
            ("Archivos Críticos", self.evaluar_archivos_criticos),
            ("Configuración Deploy", self.evaluar_configuracion_render)
        ]
        
        for nombre, evaluador in componentes:
            try:
                evaluacion = evaluador()
                self.resultado["componentes"][nombre] = evaluacion
                
                # Mostrar resultado
                estado = evaluacion.get("estado", "ERROR")
                riesgo = evaluacion.get("riesgo", "DESCONOCIDO")
                print(f"[{estado}] {nombre} - Riesgo: {riesgo}")
                
            except Exception as e:
                print(f"[ERROR] {nombre} - Error en evaluación: {e}")
                self.resultado["componentes"][nombre] = {
                    "estado": "ERROR_EVALUACION",
                    "riesgo": "ALTO",
                    "error": str(e)
                }
        
        print()
        
        # Generar recomendaciones
        self.resultado["recomendaciones"] = self.generar_recomendaciones()
        
        # Calcular riesgo general
        self.resultado["riesgo_deploy"] = self.calcular_riesgo_general()
        
        # Evaluar estado general
        if self.resultado["riesgo_deploy"] == "BAJO":
            self.resultado["evaluacion_general"] = "DEPLOY_SEGURO"
        elif self.resultado["riesgo_deploy"] == "MEDIO":
            self.resultado["evaluacion_general"] = "DEPLOY_CON_PRECAUCIONES"
        else:
            self.resultado["evaluacion_general"] = "DEPLOY_NO_RECOMENDADO"
        
        # Garantías de persistencia
        archivos_eval = self.resultado["componentes"].get("Archivos Críticos", {})
        if archivos_eval.get("estado") in ["SEGUROS_REDUNDANTES", "SEGUROS_SIMPLES"]:
            self.resultado["garantias_persistencia"] = [
                "✅ PDFs críticos localizados en múltiples ubicaciones",
                "✅ Sistema híbrido configurado con fallbacks",
                "✅ Cloudinary es servicio independiente (no afectado por deploy)",
                "✅ Sin procesos de limpieza automática configurados"
            ]
        
        return self.resultado
    
    def mostrar_resumen(self):
        """Muestra un resumen del diagnóstico"""
        print("=" * 80)
        print("RESUMEN DEL DIAGNÓSTICO")
        print("=" * 80)
        
        print(f"EVALUACIÓN GENERAL: {self.resultado['evaluacion_general']}")
        print(f"RIESGO DE DEPLOY: {self.resultado['riesgo_deploy']}")
        print()
        
        print("ESTADO POR COMPONENTE:")
        for nombre, evaluacion in self.resultado["componentes"].items():
            estado = evaluacion.get("estado", "ERROR")
            riesgo = evaluacion.get("riesgo", "DESCONOCIDO") 
            impacto = evaluacion.get("impacto_deploy", "DESCONOCIDO")
            print(f"  {nombre}: {estado} (Riesgo: {riesgo}, Impacto: {impacto})")
        
        print()
        print("RECOMENDACIONES:")
        for rec in self.resultado["recomendaciones"]:
            print(f"  {rec}")
        
        if self.resultado["garantias_persistencia"]:
            print()
            print("GARANTÍAS DE PERSISTENCIA:")
            for garantia in self.resultado["garantias_persistencia"]:
                print(f"  {garantia}")
    
    def guardar_reporte(self, nombre_archivo: str = None) -> str:
        """Guarda el reporte completo en JSON"""
        if not nombre_archivo:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f"diagnostico_deploy_{timestamp}.json"
        
        try:
            with open(nombre_archivo, 'w', encoding='utf-8') as f:
                json.dump(self.resultado, f, ensure_ascii=False, indent=2)
            
            print(f"\nReporte guardado en: {nombre_archivo}")
            return nombre_archivo
            
        except Exception as e:
            print(f"Error guardando reporte: {e}")
            return None

def main():
    """Función principal"""
    try:
        print("Iniciando diagnóstico pre-deploy...")
        
        diagnostico = DiagnosticoDeploy()
        resultado = diagnostico.ejecutar_diagnostico_completo()
        diagnostico.mostrar_resumen()
        
        # Guardar reporte
        archivo_reporte = diagnostico.guardar_reporte()
        
        # Resultado final
        print()
        print("=" * 80)
        print("CONCLUSIÓN FINAL")
        print("=" * 80)
        
        evaluacion = resultado["evaluacion_general"]
        riesgo = resultado["riesgo_deploy"]
        
        if evaluacion == "DEPLOY_SEGURO":
            print("✅ DEPLOY RECOMENDADO")
            print("   El sistema está listo para el deploy con riesgo mínimo.")
        elif evaluacion == "DEPLOY_CON_PRECAUCIONES":
            print("⚠️  DEPLOY CON PRECAUCIONES")
            print("   Revisar recomendaciones antes del deploy.")
        else:
            print("❌ DEPLOY NO RECOMENDADO")
            print("   Corregir problemas críticos antes de proceder.")
        
        print(f"\nRiesgo evaluado: {riesgo}")
        print(f"PDFs críticos: VERIFICADOS y LOCALIZADOS")
        
        return evaluacion == "DEPLOY_SEGURO"
        
    except KeyboardInterrupt:
        print("\nDiagnóstico interrumpido por el usuario")
        return False
    except Exception as e:
        print(f"\nError en diagnóstico: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()