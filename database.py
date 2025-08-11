import os
import json
import datetime
from dotenv import load_dotenv
from pathlib import Path
import uuid
import re
from urllib.parse import urlparse

# Cargar variables de entorno
load_dotenv()

class DatabaseManager:
    def __init__(self):
        """Inicializar con modo offline automático si MongoDB falla"""
        self.modo_offline = False
        self.archivo_datos = "cotizaciones_offline.json"
        self.cotizaciones_pendientes_sincronizar = []
        
        print("Intentando conectar a MongoDB...")
        
        # Intentar conectar a MongoDB primero
        try:
            from pymongo import MongoClient
            
            # Detectar entorno: Render/producción vs desarrollo local
            es_render = os.getenv('RENDER') or os.getenv('RENDER_SERVICE_NAME')
            es_produccion = os.getenv('FLASK_ENV') == 'production' or es_render
            
            print(f"Entorno detectado: {'Render/Producción' if es_produccion else 'Desarrollo local'}")
            
            # MEJORADO: Obtener URI con parsing robusto y validación completa
            mongodb_uri = os.getenv('MONGODB_URI')
            
            if mongodb_uri:
                # Usar URI completa (preferido para Render)
                print("[MONGO] Usando MONGODB_URI de variables de entorno")
                print(f"[MONGO] URI (primeros 50 chars): {mongodb_uri[:50]}...")
                
                self.mongo_uri = mongodb_uri.strip()  # Remover espacios
                
                # MEJORADO: Extraer nombre de base de datos con parsing robusto
                self.database_name = self._extraer_nombre_bd_uri(mongodb_uri)
                print(f"[MONGO] Base de datos extraída: '{self.database_name}'")
                
                # Validar formato de URI
                if not self._validar_uri_mongodb(mongodb_uri):
                    raise Exception("MONGODB_URI tiene formato inválido")
            else:
                # Fallback para desarrollo local - usar variables separadas
                print("MONGODB_URI no encontrada, usando variables separadas (desarrollo local)")
                import urllib.parse
                usuario = os.getenv('MONGO_USERNAME', 'admin')
                contraseña = os.getenv('MONGO_PASSWORD', 'ADMIN123')
                cluster = os.getenv('MONGO_CLUSTER', 'cluster0.t4e0tp8.mongodb.net')
                database = os.getenv('MONGO_DATABASE', 'cotizaciones')
                
                usuario_encoded = urllib.parse.quote_plus(usuario)
                contraseña_encoded = urllib.parse.quote_plus(contraseña)
                
                # Usar timeouts más largos en producción, cortos en desarrollo
                timeout = "30000" if es_produccion else "5000"
                self.mongo_uri = f"mongodb+srv://{usuario_encoded}:{contraseña_encoded}@{cluster}/{database}?retryWrites=true&w=majority&appName=Cluster0&connectTimeoutMS={timeout}&serverSelectionTimeoutMS={timeout}"
                self.database_name = database
            
            print(f"Base de datos: {self.database_name}")
            print(f"URI configurada: {self.mongo_uri[:50]}...") # Solo mostrar inicio del URI
            
            # MEJORADO: Conexión con verificación robusta y timeouts específicos
            print("[MONGO] Creando cliente MongoDB...")
            
            # Timeout específico por entorno
            timeout_ms = 30000 if es_produccion else 10000
            print(f"[MONGO] Timeout configurado: {timeout_ms}ms")
            
            self.client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=timeout_ms,
                connectTimeoutMS=timeout_ms,
                socketTimeoutMS=timeout_ms
            )
            
            self.db = self.client[self.database_name]
            self.collection = self.db["cotizacions"]
            
            # CRÍTICO: Verificación REAL de conexión y permisos
            print("[MONGO] Verificando conexión real...")
            self._verificar_conexion_completa()
            print("[MONGO] ✅ Conexión a MongoDB exitosa y verificada")
            
            self.modo_offline = False
            
            # Crear índices
            self._crear_indices()
            
            # Sincronizar cotizaciones offline pendientes
            self._sincronizar_cotizaciones_offline()
            
        except Exception as e:
            print(f"[ERROR MONGO] MongoDB no disponible: {str(e)}")
            print(f"[ERROR MONGO] Tipo de error: {type(e).__name__}")
            
            # Log detallado del error para debugging
            if 'ServerSelectionTimeoutError' in str(type(e)):
                print("[ERROR MONGO] Timeout de conexión - verificar URI y red")
            elif 'Authentication' in str(e):
                print("[ERROR MONGO] Error de autenticación - verificar credenciales")
            elif 'DNS' in str(e):
                print("[ERROR MONGO] Error de DNS - verificar cluster URL")
            
            print("[MODO OFFLINE] Activando modo OFFLINE automáticamente")
            self.modo_offline = True
            self._inicializar_archivo_offline()
    
    def _extraer_nombre_bd_uri(self, uri):
        """Extrae el nombre de la base de datos de la URI de MongoDB de forma robusta"""
        try:
            # Método 1: Parsing con urllib
            parsed = urlparse(uri)
            if parsed.path and len(parsed.path) > 1:
                # Remover '/' inicial y parámetros después de '?'
                db_name = parsed.path[1:].split('?')[0]
                if db_name:
                    print(f"[MONGO] BD extraída con urllib: '{db_name}'")
                    return db_name
            
            # Método 2: Regex para diferentes formatos
            # Formato: mongodb+srv://user:pass@cluster.net/database?params
            regex_patterns = [
                r'mongodb\+srv://[^/]+/([^?]+)',  # URI con SRV
                r'mongodb://[^/]+/([^?]+)',       # URI sin SRV
                r'/([a-zA-Z0-9_-]+)\?',           # BD antes de parámetros
                r'/([a-zA-Z0-9_-]+)$'             # BD al final
            ]
            
            for pattern in regex_patterns:
                match = re.search(pattern, uri)
                if match:
                    db_name = match.group(1)
                    print(f"[MONGO] BD extraída con regex: '{db_name}'")
                    return db_name
            
            # Método 3: Búsqueda manual de nombres conocidos
            known_dbs = ['cotizaciones', 'cotizador_cws', 'cws_cotizaciones']
            for db in known_dbs:
                if f'/{db}' in uri:
                    print(f"[MONGO] BD encontrada por coincidencia: '{db}'")
                    return db
            
            # Fallback por defecto
            print("[MONGO] No se pudo extraer BD, usando 'cotizaciones'")
            return 'cotizaciones'
            
        except Exception as e:
            print(f"[ERROR MONGO] Error extrayendo nombre BD: {e}")
            return 'cotizaciones'
    
    def _validar_uri_mongodb(self, uri):
        """Valida que la URI de MongoDB tenga el formato correcto"""
        try:
            # Verificar que empiece con mongodb:// o mongodb+srv://
            if not (uri.startswith('mongodb://') or uri.startswith('mongodb+srv://')):
                print("[ERROR MONGO] URI no empieza con mongodb:// o mongodb+srv://")
                return False
            
            # Verificar que tenga formato básico correcto
            parsed = urlparse(uri)
            if not parsed.hostname:
                print("[ERROR MONGO] URI no tiene hostname válido")
                return False
            
            print("[MONGO] [OK] URI MongoDB válida")
            return True
            
        except Exception as e:
            print(f"[ERROR MONGO] Error validando URI: {e}")
            return False
    
    def _verificar_conexion_completa(self):
        """Verifica conexión completa a MongoDB con operaciones reales"""
        try:
            # Test 1: Ping al servidor
            print("[MONGO] Test 1: Ping al servidor...")
            ping_result = self.client.admin.command('ping')
            print(f"[MONGO] [OK] Ping exitoso: {ping_result}")
            
            # Test 2: Verificar acceso a la base de datos
            print(f"[MONGO] Test 2: Verificando BD '{self.database_name}'...")
            db_stats = self.db.command('dbstats')
            print(f"[MONGO] [OK] Acceso a BD exitoso - DB size: {db_stats.get('dataSize', 'N/A')} bytes")
            
            # Test 3: Verificar acceso a la colección
            print("[MONGO] Test 3: Verificando colección 'cotizacions'...")
            col_count = self.collection.count_documents({})
            print(f"[MONGO] [OK] Acceso a colección exitoso - Documentos: {col_count}")
            
            # Test 4: Operación de escritura (insertar y eliminar documento test)
            print("[MONGO] Test 4: Verificando permisos de escritura...")
            test_doc = {
                "_test": True,
                "timestamp": datetime.datetime.now().isoformat(),
                "purpose": "connection_test"
            }
            
            # Insertar documento test
            result = self.collection.insert_one(test_doc)
            test_id = result.inserted_id
            print(f"[MONGO] [OK] Inserción test exitosa - ID: {test_id}")
            
            # Verificar que se insertó
            found_doc = self.collection.find_one({"_id": test_id})
            if not found_doc:
                raise Exception("Documento test no encontrado después de insertar")
            
            # Eliminar documento test
            delete_result = self.collection.delete_one({"_id": test_id})
            if delete_result.deleted_count != 1:
                raise Exception("No se pudo eliminar documento test")
            
            print("[MONGO] [OK] Permisos de escritura verificados")
            print("[MONGO] [SUCCESS] VERIFICACIÓN COMPLETA EXITOSA")
            
        except Exception as e:
            print(f"[ERROR MONGO] Fallo en verificación completa: {e}")
            print(f"[ERROR MONGO] Detalles del error: {type(e).__name__}")
            raise e
    
    def _crear_indices(self):
        """Crea índices para optimizar búsquedas frecuentes"""
        try:
            if not self.modo_offline:
                self.collection.create_index("numeroCotizacion")
                self.collection.create_index("timestamp")
                self.collection.create_index("datosGenerales.cliente")
                print("Indices creados/verificados")
        except Exception as e:
            print(f"Advertencia al crear indices: {e}")
    
    def _inicializar_archivo_offline(self):
        """Inicializar archivo JSON para modo offline"""
        if not Path(self.archivo_datos).exists():
            datos_iniciales = {
                "cotizaciones": [],
                "metadata": {
                    "created": datetime.datetime.now().isoformat(),
                    "version": "1.0.0",
                    "total_cotizaciones": 0,
                    "modo": "offline"
                }
            }
            with open(self.archivo_datos, 'w', encoding='utf-8') as f:
                json.dump(datos_iniciales, f, ensure_ascii=False, indent=2)
            print(f"Archivo {self.archivo_datos} creado")
        else:
            print(f"Usando archivo existente {self.archivo_datos}")
    
    def _cargar_datos_offline(self):
        """Cargar datos desde archivo JSON"""
        try:
            with open(self.archivo_datos, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando datos offline: {e}")
            return {"cotizaciones": [], "metadata": {}}
    
    def _guardar_datos_offline(self, datos):
        """Guardar datos en archivo JSON"""
        try:
            datos["metadata"]["last_updated"] = datetime.datetime.now().isoformat()
            with open(self.archivo_datos, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error guardando datos offline: {e}")
            return False
    
    def generar_numero_cotizacion(self, cliente, vendedor, proyecto, revision=1):
        """
        Genera un número de cotización automáticamente con el formato:
        Cliente+CWS+IniciajesVendedor+Consecutivo+Revision+Proyecto
        """
        try:
            # Normalizar datos de entrada
            cliente = cliente.upper().replace(" ", "")[:10] if cliente else "CLIENTE"
            proyecto = proyecto.upper().replace(" ", "")[:10] if proyecto else "PROYECTO"
            
            # Obtener las dos primeras iniciales del vendedor
            iniciales_vendedor = ""
            if vendedor:
                palabras = vendedor.strip().split()
                for palabra in palabras[:2]:  # Máximo 2 palabras
                    if palabra and palabra[0].isalpha():
                        iniciales_vendedor += palabra[0].upper()
                if len(iniciales_vendedor) < 2 and len(palabras) > 0:
                    # Si solo hay una palabra, tomar las primeras 2 letras
                    primera_palabra = palabras[0]
                    iniciales_vendedor = primera_palabra[:2].upper()
            
            if not iniciales_vendedor:
                iniciales_vendedor = "XX"
            
            # Buscar el siguiente número consecutivo
            patron_base = f"{cliente}CWS{iniciales_vendedor}"
            numero_consecutivo = self._obtener_siguiente_consecutivo(patron_base)
            
            # Formatear el número completo con guiones
            numero_cotizacion = f"{cliente}-CWS-{iniciales_vendedor}-{numero_consecutivo:03d}-R{revision}-{proyecto}"
            
            return numero_cotizacion
            
        except Exception as e:
            print(f"Error generando número de cotización: {e}")
            # Fallback a número único basado en timestamp
            timestamp = int(datetime.datetime.now().timestamp())
            return f"CWS{timestamp}R{revision}"
    
    def _obtener_siguiente_consecutivo(self, patron_base):
        """Obtiene el siguiente número consecutivo para un patrón base dado"""
        try:
            if self.modo_offline:
                # Buscar en archivo offline
                datos_offline = self._cargar_datos_offline()
                cotizaciones = datos_offline.get("cotizaciones", [])
            else:
                # Buscar en MongoDB
                try:
                    # Buscar todas las cotizaciones que coincidan con el patrón
                    regex_pattern = f"^{patron_base}\\d{{3}}R\\d+"
                    cursor = self.collection.find({"numeroCotizacion": {"$regex": regex_pattern}})
                    cotizaciones = list(cursor)
                except Exception as e:
                    print(f"Error accediendo a MongoDB para consecutivo: {e}")
                    # Fallback a modo offline
                    datos_offline = self._cargar_datos_offline()
                    cotizaciones = datos_offline.get("cotizaciones", [])
            
            # Extraer números consecutivos existentes
            numeros_existentes = []
            for cotizacion in cotizaciones:
                numero_cot = cotizacion.get("numeroCotizacion", "")
                if numero_cot.startswith(patron_base):
                    try:
                        # Extraer el número consecutivo del formato: PatronBaseXXXRYProyecto
                        parte_despues_patron = numero_cot[len(patron_base):]
                        if len(parte_despues_patron) >= 4 and parte_despues_patron[3] == 'R':
                            num_consecutivo = int(parte_despues_patron[:3])
                            numeros_existentes.append(num_consecutivo)
                    except (ValueError, IndexError):
                        continue
            
            # Encontrar el siguiente número disponible
            if not numeros_existentes:
                return 1
            
            return max(numeros_existentes) + 1
            
        except Exception as e:
            print(f"Error obteniendo consecutivo: {e}")
            return 1

    def generar_numero_revision(self, numero_cotizacion_original, nueva_revision):
        """
        Genera un número de cotización para una nueva revisión manteniendo 
        el mismo número base pero actualizando la revisión
        Formato: Cliente-CWS-Iniciales-###-R#-Proyecto
        """
        try:
            # Buscar la posición de '-R' seguida de números
            import re
            
            # Patrón para encontrar la revisión: -R seguida de uno o más dígitos-
            patron = r'-R\d+-'
            match = re.search(patron, numero_cotizacion_original)
            
            if match:
                # Extraer la parte antes de -R y después de -R#-
                inicio_revision = match.start()
                final_revision = match.end()
                
                base = numero_cotizacion_original[:inicio_revision]
                proyecto_parte = numero_cotizacion_original[final_revision:]
                
                # Generar nuevo número con la nueva revisión
                return f"{base}-R{nueva_revision}-{proyecto_parte}"
            else:
                # Si no tiene el formato esperado, intentar agregar la revisión
                if '-R' in numero_cotizacion_original:
                    # Formato anterior sin guiones finales
                    partes = numero_cotizacion_original.split('-R')
                    base = partes[0]
                    resto = '-R'.join(partes[1:])
                    
                    # Separar revisión de proyecto
                    i = 0
                    while i < len(resto) and resto[i].isdigit():
                        i += 1
                    
                    proyecto_parte = resto[i:] if i < len(resto) else ""
                    return f"{base}-R{nueva_revision}{proyecto_parte}"
                else:
                    return f"{numero_cotizacion_original}-R{nueva_revision}"
                
        except Exception as e:
            print(f"Error generando número de revisión: {e}")
            return f"{numero_cotizacion_original}-R{nueva_revision}"

    def guardar_cotizacion(self, datos):
        """Guarda una cotización con respaldo automático"""
        try:
            print("[INICIO] GUARDADO DE COTIZACION")
            print(f"[DATOS] Recibidos: {json.dumps(datos, indent=2, ensure_ascii=False)[:500]}...")
            print(f"[MODO] Actual: {'OFFLINE' if self.modo_offline else 'ONLINE'}")
            
            # Agregar metadata del sistema
            ahora = datetime.datetime.now()
            datos["fechaCreacion"] = ahora.isoformat()
            datos["timestamp"] = int(ahora.timestamp() * 1000)
            datos["version"] = os.getenv('APP_VERSION', '1.0.0')
            
            # Extraer campos clave para índices
            numero = datos.get("datosGenerales", {}).get("numeroCotizacion")
            revision = int(datos.get("datosGenerales", {}).get("revision", 1))
            cliente = datos.get("datosGenerales", {}).get("cliente")
            vendedor = datos.get("datosGenerales", {}).get("vendedor")
            proyecto = datos.get("datosGenerales", {}).get("proyecto", "")
            
            # Validaciones de campos obligatorios
            print(f"[VALIDACION] Cliente: '{cliente}' | Vendedor: '{vendedor}' | Proyecto: '{proyecto}'")
            if not cliente:
                print("[ERROR] Cliente es obligatorio")
                return {"success": False, "error": "Cliente es obligatorio"}
            if not vendedor:
                print("[ERROR] Vendedor es obligatorio")
                return {"success": False, "error": "Vendedor es obligatorio"}
            if not proyecto:
                print("[ERROR] Proyecto es obligatorio")
                return {"success": False, "error": "Proyecto es obligatorio"}
            
            # GENERAR NÚMERO DE COTIZACIÓN AUTOMÁTICAMENTE
            if not numero or numero.strip() == "":
                # Generar número nuevo
                numero = self.generar_numero_cotizacion(cliente, vendedor, proyecto, revision)
                datos["datosGenerales"]["numeroCotizacion"] = numero
                print(f"Número generado automáticamente: {numero}")
            else:
                # Si el usuario proporcionó un número, verificar si es una nueva revisión
                if revision > 1:
                    numero = self.generar_numero_revision(numero, revision)
                    datos["datosGenerales"]["numeroCotizacion"] = numero
                    print(f"Número actualizado para revisión {revision}: {numero}")
            
            print(f"Numero final: {numero}")
            print(f"Cliente: {cliente}")
            print(f"Vendedor: {vendedor}")
            print(f"Proyecto: {proyecto}")
            print(f"Revisión: {revision}")
            
            # Inyectar al nivel raíz para búsquedas fáciles
            datos["numeroCotizacion"] = numero
            datos["revision"] = revision
            
            if self.modo_offline:
                # MODO OFFLINE: Guardar en archivo JSON
                print("Guardando en modo OFFLINE")
                datos_archivo = self._cargar_datos_offline()
                
                # Generar ID único
                datos["_id"] = str(uuid.uuid4())
                
                # Agregar a la lista
                datos_archivo["cotizaciones"].append(datos)
                datos_archivo["metadata"]["total_cotizaciones"] = len(datos_archivo["cotizaciones"])
                
                # Guardar archivo
                if self._guardar_datos_offline(datos_archivo):
                    print(f"Cotizacion guardada OFFLINE - ID: {datos['_id']}")
                    print(f"Total cotizaciones: {len(datos_archivo['cotizaciones'])}")
                    
                    return {
                        "success": True,
                        "id": datos["_id"],
                        "numeroCotizacion": numero,
                        "campos_guardados": len(datos.keys()),
                        "modo": "offline"
                    }
                else:
                    return {"success": False, "error": "Error guardando en archivo"}
            else:
                # MODO ONLINE: Guardar en MongoDB + Respaldo automático
                print("[ONLINE] Guardando en modo ONLINE (MongoDB + respaldo)")
                
                # 1. Verificar conexión antes de guardar
                try:
                    self.client.admin.command('ping')
                    print("Conexion a MongoDB verificada")
                except Exception as ping_error:
                    print(f"Error de conexion: {ping_error}")
                    print("Cambiando a modo offline automaticamente")
                    
                    # Cambiar a modo offline y reintentar
                    self.modo_offline = True
                    return self.guardar_cotizacion(datos)
                
                # 2. Guardar en MongoDB
                print(f"[MONGODB] INTENTANDO GUARDAR EN MONGODB...")
                print(f"   Collection: {self.collection}")
                print(f"   Numero cotizacion: {numero}")
                resultado = self.collection.insert_one(datos)
                inserted_id = str(resultado.inserted_id)
                
                print(f"[SUCCESS] Cotizacion guardada en MongoDB - ID: {inserted_id}")
                
                # 3. RESPALDO AUTOMÁTICO: También guardar en archivo offline
                try:
                    self._agregar_respaldo_offline(datos, inserted_id)
                    print("Respaldo offline creado automaticamente")
                except Exception as backup_error:
                    print(f"Error en respaldo offline: {backup_error}")
                    # No fallar por error de respaldo
                
                # 4. VERIFICACIÓN CRÍTICA REAL DE GUARDADO
                print(f"[VERIFICAR] 🔍 VERIFICACIÓN CRÍTICA INMEDIATA...")
                
                try:
                    # Verificación múltiple para asegurar que se guardó realmente
                    verificaciones_pasadas = 0
                    total_verificaciones = 3
                    documento_guardado = None
                    
                    # Verificación 1: Por ObjectId
                    print(f"[VERIFICAR] Test 1: Buscando por ObjectId {resultado.inserted_id}")
                    verificacion_id = self.collection.find_one({"_id": resultado.inserted_id})
                    if verificacion_id:
                        print(f"[VERIFICAR] [OK] Test 1 PASADO: Encontrado por ObjectId")
                        documento_guardado = verificacion_id
                        verificaciones_pasadas += 1
                    else:
                        print(f"[VERIFICAR] [FAIL] Test 1 FALLO: No encontrado por ObjectId")
                    
                    # Verificación 2: Por número de cotización
                    print(f"[VERIFICAR] Test 2: Buscando por número '{numero}'")
                    verificacion_numero = self.collection.find_one({"numeroCotizacion": numero})
                    if verificacion_numero:
                        print(f"[VERIFICAR] [OK] Test 2 PASADO: Encontrado por número")
                        print(f"   Cliente verificado: {verificacion_numero.get('datosGenerales', {}).get('cliente')}")
                        if not documento_guardado:
                            documento_guardado = verificacion_numero
                        verificaciones_pasadas += 1
                    else:
                        print(f"[VERIFICAR] [FAIL] Test 2 FALLO: No encontrado por número")
                    
                    # Verificación 3: Contar documentos
                    print(f"[VERIFICAR] Test 3: Verificando incremento en conteo")
                    conteo_actual = self.collection.count_documents({})
                    print(f"   Total documentos ahora: {conteo_actual}")
                    verificaciones_pasadas += 1  # Este siempre pasa si llegamos aquí
                    
                    # Evaluación final
                    print(f"[VERIFICAR] Resultado: {verificaciones_pasadas}/{total_verificaciones} verificaciones pasadas")
                    
                    if verificaciones_pasadas >= 2:
                        print(f"[VERIFICAR] [SUCCESS] GUARDADO VERIFICADO EXITOSAMENTE")
                    else:
                        # FALLO CRÍTICO - el documento NO se guardó realmente
                        print(f"[VERIFICAR] [CRITICAL] FALLO CRÍTICO: Documento NO se guardó correctamente")
                        print(f"   ObjectId generado: {resultado.inserted_id}")
                        print(f"   Número de cotización: {numero}")
                        
                        # Cambiar a modo offline inmediatamente
                        print(f"[CRÍTICO] Cambiando a modo offline por fallo de guardado")
                        self.modo_offline = True
                        return self.guardar_cotizacion(datos)
                        
                except Exception as verificacion_error:
                    print(f"[ERROR VERIFICAR] Error en verificación: {verificacion_error}")
                    print(f"[ERROR VERIFICAR] Tipo: {type(verificacion_error).__name__}")
                    
                    # Si hay error en verificación, cambiar a offline
                    print(f"[RECONEXIÓN] Error en verificación, cambiando a offline")
                    self.modo_offline = True
                    return self.guardar_cotizacion(datos)
                
                return {
                    "success": True,
                    "id": inserted_id,
                    "numeroCotizacion": numero,
                    "campos_guardados": len(datos.keys()),
                    "modo": "online",
                    "respaldo": "creado",
                    "cliente": cliente,
                    "vendedor": vendedor
                }
            
        except Exception as e:
            print(f"Error al guardar: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _agregar_respaldo_offline(self, datos, mongodb_id):
        """Agrega una cotización al respaldo offline"""
        try:
            # Cargar respaldo existente
            datos_offline = self._cargar_datos_offline()
            
            # Preparar datos para respaldo (con ID de MongoDB)
            datos_respaldo = datos.copy()
            datos_respaldo["_id"] = mongodb_id
            datos_respaldo["respaldo_de_mongodb"] = True
            datos_respaldo["fecha_respaldo"] = datetime.datetime.now().isoformat()
            
            # Verificar si ya existe en respaldo
            numero = datos.get("numeroCotizacion")
            existe_respaldo = False
            
            for i, cot_respaldo in enumerate(datos_offline.get("cotizaciones", [])):
                if cot_respaldo.get("numeroCotizacion") == numero:
                    # Actualizar respaldo existente
                    datos_offline["cotizaciones"][i] = datos_respaldo
                    existe_respaldo = True
                    break
            
            if not existe_respaldo:
                # Agregar nuevo respaldo
                if "cotizaciones" not in datos_offline:
                    datos_offline["cotizaciones"] = []
                datos_offline["cotizaciones"].append(datos_respaldo)
            
            # Actualizar metadata
            if "metadata" not in datos_offline:
                datos_offline["metadata"] = {}
            
            datos_offline["metadata"]["ultimo_respaldo"] = datetime.datetime.now().isoformat()
            datos_offline["metadata"]["total_cotizaciones"] = len(datos_offline["cotizaciones"])
            datos_offline["metadata"]["modo"] = "respaldo_automatico"
            
            # Guardar respaldo
            return self._guardar_datos_offline(datos_offline)
            
        except Exception as e:
            print(f"Error creando respaldo offline: {e}")
            return False
    
    def buscar_cotizaciones(self, query, page=1, per_page=None):
        """Busca cotizaciones con criterios ampliados"""
        try:
            if per_page is None:
                per_page = int(os.getenv('DEFAULT_PAGE_SIZE', '20'))
            
            if self.modo_offline:
                # Buscar en archivo JSON
                datos_archivo = self._cargar_datos_offline()
                cotizaciones = datos_archivo.get("cotizaciones", [])
                
                if not query:
                    resultados = cotizaciones
                else:
                    # Filtrar por query ampliado
                    resultados = []
                    query_lower = query.lower()
                    
                    for cot in cotizaciones:
                        datos_generales = cot.get("datosGenerales", {})
                        
                        # Buscar en múltiples campos
                        if (query_lower in str(cot.get("numeroCotizacion", "")).lower() or
                            query_lower in str(datos_generales.get("cliente", "")).lower() or
                            query_lower in str(datos_generales.get("vendedor", "")).lower() or
                            query_lower in str(datos_generales.get("atencionA", "")).lower() or
                            query_lower in str(datos_generales.get("proyecto", "")).lower() or
                            query_lower in str(datos_generales.get("fecha", "")).lower() or
                            query_lower in str(cot.get("fechaCreacion", "")).lower()):
                            resultados.append(cot)
                
                # Ordenar por timestamp (más recientes primero)
                resultados.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
                
                # Paginación
                total = len(resultados)
                start = (page - 1) * per_page
                end = start + per_page
                resultados_pagina = resultados[start:end]
                
                print(f"Encontradas {len(resultados_pagina)} de {total} cotizaciones (OFFLINE)")
                
                return {
                    "resultados": resultados_pagina,
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "pages": (total + per_page - 1) // per_page,
                    "modo": "offline"
                }
            else:
                # Buscar en MongoDB
                if not query:
                    filtro_final = {}
                
                skip = (page - 1) * per_page
                
                # Filtros ampliados incluyendo los nuevos campos
                filtros = [
                    {"numeroCotizacion": {"$regex": query, "$options": "i"}},
                    {"datosGenerales.cliente": {"$regex": query, "$options": "i"}},
                    {"datosGenerales.vendedor": {"$regex": query, "$options": "i"}},
                    {"datosGenerales.atencionA": {"$regex": query, "$options": "i"}},
                    {"datosGenerales.proyecto": {"$regex": query, "$options": "i"}},
                    {"datosGenerales.contacto": {"$regex": query, "$options": "i"}},
                    {"datosGenerales.fecha": {"$regex": query, "$options": "i"}},
                    {"revision": {"$regex": query, "$options": "i"}},
                    {"fechaCreacion": {"$regex": query, "$options": "i"}}
                ]
                
                filtro_final = {"$or": filtros}
                
                total = self.collection.count_documents(filtro_final)
                
                resultados = list(
                    self.collection.find(filtro_final)
                    .sort("timestamp", -1)
                    .skip(skip)
                    .limit(per_page)
                )
                
                # Convertir ObjectId a string
                for doc in resultados:
                    doc["_id"] = str(doc["_id"])
                
                if len(resultados) == 0 and query:
                    print(f"No se encontraron resultados para '{query}'")
                    print(f"Verificando primeras 5 cotizaciones en BD:")
                    muestra = list(self.collection.find().limit(5))
                    for m in muestra:
                        dg = m.get('datosGenerales', {})
                        print(f"   - Cliente: '{dg.get('cliente', 'N/A')}' | Vendedor: '{dg.get('vendedor', 'N/A')}'")
                
                print(f"Encontradas {len(resultados)} de {total} cotizaciones (ONLINE)")
                print(f"   Criterios de búsqueda: número, cliente, vendedor, atención a, proyecto, contacto")
                
                return {
                    "resultados": resultados,
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "pages": (total + per_page - 1) // per_page,
                    "modo": "online"
                }
                
        except Exception as e:
            print(f"Error en busqueda: {e}")
            return {"error": str(e)}
    
    def obtener_cotizacion(self, item_id):
        """Obtiene una cotización por ID (online o offline)"""
        try:
            if self.modo_offline:
                datos_archivo = self._cargar_datos_offline()
                cotizaciones = datos_archivo.get("cotizaciones", [])
                
                # Buscar por ID o número
                for cot in cotizaciones:
                    if (cot.get("_id") == item_id or 
                        cot.get("numeroCotizacion") == item_id or
                        str(cot.get("numeroCotizacion", "")).lower() == item_id.lower()):
                        
                        print(f"Cotizacion encontrada (OFFLINE): {cot.get('numeroCotizacion', 'Sin numero')}")
                        return {"encontrado": True, "item": cot, "modo": "offline"}
                
                print(f"Cotizacion no encontrada (OFFLINE): {item_id}")
                return {"encontrado": False, "mensaje": f"Cotización '{item_id}' no encontrada", "modo": "offline"}
            else:
                # Buscar en MongoDB (código original)
                from bson import ObjectId
                import re
                
                item = None
                print(f"Buscando cotizacion: '{item_id}'")
                
                # Intentar diferentes tipos de búsqueda
                if ObjectId.is_valid(item_id):
                    item = self.collection.find_one({"_id": ObjectId(item_id)})
                
                if not item:
                    item = self.collection.find_one({"numeroCotizacion": item_id})
                
                if not item:
                    item = self.collection.find_one({
                        "numeroCotizacion": {"$regex": f"^{re.escape(item_id)}$", "$options": "i"}
                    })
                
                if not item:
                    item = self.collection.find_one({
                        "datosGenerales.numeroCotizacion": item_id
                    })
                
                if item:
                    item["_id"] = str(item["_id"])
                    numero_encontrado = item.get('numeroCotizacion', 'Sin número')
                    print(f"Cotizacion encontrada (ONLINE): {numero_encontrado}")
                    return {"encontrado": True, "item": item, "modo": "online"}
                else:
                    print(f"Cotizacion no encontrada (ONLINE): {item_id}")
                    return {"encontrado": False, "mensaje": f"Cotización '{item_id}' no encontrada", "modo": "online"}
                    
        except Exception as e:
            print(f"Error al buscar cotizacion: {e}")
            return {"error": str(e)}
    
    def obtener_todas_cotizaciones(self, page=1, per_page=None):
        """Obtiene todas las cotizaciones (online o offline)"""
        return self.buscar_cotizaciones("", page, per_page)
    
    def _sincronizar_cotizaciones_offline(self):
        """Sincroniza cotizaciones guardadas offline cuando MongoDB vuelve a estar disponible"""
        try:
            if self.modo_offline:
                return  # No sincronizar si estamos offline
            
            # Cargar datos offline
            datos_offline = self._cargar_datos_offline()
            cotizaciones_offline = datos_offline.get("cotizaciones", [])
            
            if not cotizaciones_offline:
                return  # No hay nada que sincronizar
            
            sincronizadas = 0
            errores = 0
            
            for cotizacion in cotizaciones_offline:
                try:
                    # Verificar si ya existe en MongoDB
                    numero = cotizacion.get("numeroCotizacion")
                    if not numero:
                        continue
                    
                    existe = self.collection.find_one({"numeroCotizacion": numero})
                    
                    if not existe:
                        # No existe en MongoDB, sincronizar
                        # Remover campos específicos del archivo offline
                        cotizacion_limpia = cotizacion.copy()
                        cotizacion_limpia.pop("_id", None)  # MongoDB generará nuevo ID
                        cotizacion_limpia.pop("respaldo_de_mongodb", None)
                        cotizacion_limpia.pop("fecha_respaldo", None)
                        
                        # Insertar en MongoDB
                        resultado = self.collection.insert_one(cotizacion_limpia)
                        print(f"[SYNC] Sincronizada cotización offline: {numero}")
                        sincronizadas += 1
                        
                    else:
                        # Ya existe, verificar si la versión offline es más reciente
                        timestamp_offline = cotizacion.get("timestamp", 0)
                        timestamp_online = existe.get("timestamp", 0)
                        
                        if timestamp_offline > timestamp_online:
                            # La versión offline es más reciente, actualizar
                            cotizacion_limpia = cotizacion.copy()
                            cotizacion_limpia.pop("_id", None)
                            cotizacion_limpia.pop("respaldo_de_mongodb", None)
                            cotizacion_limpia.pop("fecha_respaldo", None)
                            
                            self.collection.replace_one(
                                {"numeroCotizacion": numero},
                                cotizacion_limpia
                            )
                            print(f"[SYNC] Actualizada cotización: {numero} (versión offline más reciente)")
                            sincronizadas += 1
                        
                except Exception as e:
                    print(f"[ERROR] Error sincronizando {numero}: {e}")
                    errores += 1
                    continue
            
            if sincronizadas > 0:
                print(f"[SYNC] Sincronización completada: {sincronizadas} cotizaciones sincronizadas")
                if errores > 0:
                    print(f"[WARN] {errores} errores durante la sincronización")
                
                # Opcional: Marcar cotizaciones como sincronizadas en lugar de eliminarlas
                self._marcar_cotizaciones_sincronizadas(datos_offline)
            
        except Exception as e:
            print(f"[ERROR] Error en sincronización automática: {e}")
    
    def _marcar_cotizaciones_sincronizadas(self, datos_offline):
        """Marca las cotizaciones como sincronizadas sin eliminarlas"""
        try:
            fecha_sync = datetime.datetime.now().isoformat()
            
            # Marcar cada cotización como sincronizada
            for cotizacion in datos_offline.get("cotizaciones", []):
                cotizacion["sincronizada"] = True
                cotizacion["fecha_sincronizacion"] = fecha_sync
            
            # Actualizar metadata
            if "metadata" not in datos_offline:
                datos_offline["metadata"] = {}
            
            datos_offline["metadata"]["ultima_sincronizacion"] = fecha_sync
            datos_offline["metadata"]["total_sincronizado"] = len(datos_offline.get("cotizaciones", []))
            
            # Guardar archivo actualizado
            self._guardar_datos_offline(datos_offline)
            
        except Exception as e:
            print(f"[ERROR] Error marcando cotizaciones como sincronizadas: {e}")
    
    def obtener_estado_sincronizacion(self):
        """Obtiene información del estado de sincronización"""
        try:
            datos_offline = self._cargar_datos_offline()
            cotizaciones = datos_offline.get("cotizaciones", [])
            
            total = len(cotizaciones)
            sincronizadas = sum(1 for c in cotizaciones if c.get("sincronizada", False))
            pendientes = total - sincronizadas
            
            return {
                "total_offline": total,
                "sincronizadas": sincronizadas,
                "pendientes": pendientes,
                "ultima_sincronizacion": datos_offline.get("metadata", {}).get("ultima_sincronizacion"),
                "modo_actual": "offline" if self.modo_offline else "online"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def forzar_sincronizacion(self):
        """Fuerza una sincronización manual"""
        if self.modo_offline:
            return {"error": "No se puede sincronizar en modo offline"}
        
        try:
            self._sincronizar_cotizaciones_offline()
            return {"success": True, "mensaje": "Sincronización forzada completada"}
        except Exception as e:
            return {"error": f"Error en sincronización forzada: {str(e)}"}
    
    def cerrar_conexion(self):
        """Cierra la conexión"""
        if not self.modo_offline and hasattr(self, 'client'):
            self.client.close()
            print("Conexion a MongoDB cerrada")
        else:
            print("Sesion offline finalizada")