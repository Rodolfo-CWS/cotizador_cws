#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UNIFIED SEARCH SYSTEM
====================

Sistema de búsqueda unificado que integra todas las fuentes de datos:
- Supabase PostgreSQL (cotizaciones principales)
- JSON Local (respaldo offline)
- Cloudinary (PDFs con metadatos)
- Google Drive (PDFs antiguos del administrador)

Características:
- Búsqueda paralela en múltiples fuentes
- Scoring de relevancia
- Cache de resultados frecuentes
- Filtros avanzados
- Paginación inteligente
- Búsqueda difusa (fuzzy search)
"""

import os
import json
import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import re
from pathlib import Path
import hashlib

# Para búsqueda difusa
try:
    from fuzzywuzzy import fuzz, process
    FUZZY_SEARCH_AVAILABLE = True
except ImportError:
    FUZZY_SEARCH_AVAILABLE = False
    logging.warning("fuzzywuzzy no disponible - búsqueda difusa deshabilitada")

# Para cache
from collections import OrderedDict

logger = logging.getLogger(__name__)

class SearchResultType(Enum):
    """Tipos de resultados de búsqueda"""
    COTIZACION = "cotizacion"
    PDF_NUEVO = "pdf_nuevo"
    PDF_HISTORICO = "pdf_historico"
    PDF_CLOUDINARY = "pdf_cloudinary"

class SearchSource(Enum):
    """Fuentes de búsqueda"""
    SUPABASE = "supabase"
    JSON_LOCAL = "json_local"
    CLOUDINARY = "cloudinary"
    GOOGLE_DRIVE = "google_drive"

@dataclass
class SearchFilter:
    """Filtros de búsqueda"""
    cliente: Optional[str] = None
    vendedor: Optional[str] = None
    proyecto: Optional[str] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None
    tipo_resultado: Optional[SearchResultType] = None
    fuente: Optional[SearchSource] = None
    solo_con_desglose: Optional[bool] = None
    revision_minima: Optional[int] = None

@dataclass
class SearchResult:
    """Resultado de búsqueda unificado"""
    id: str
    numero_cotizacion: str
    cliente: str
    vendedor: str = ""
    proyecto: str = ""
    fecha_creacion: Optional[datetime] = None
    tipo: SearchResultType = SearchResultType.COTIZACION
    fuente: SearchSource = SearchSource.SUPABASE
    relevancia_score: float = 0.0
    tiene_desglose: bool = False
    tiene_pdf: bool = False
    url_pdf: Optional[str] = None
    revision: int = 1
    observaciones: str = ""
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SearchResponse:
    """Respuesta de búsqueda completa"""
    resultados: List[SearchResult]
    total: int
    page: int
    per_page: int
    total_pages: int
    query: str
    filters: SearchFilter
    fuentes_consultadas: List[SearchSource]
    tiempo_busqueda_ms: int
    from_cache: bool = False
    estadisticas: Dict = None
    
    def __post_init__(self):
        if self.estadisticas is None:
            self.estadisticas = {}

class SearchCache:
    """Cache LRU para resultados de búsqueda"""
    
    def __init__(self, max_size: int = 100, ttl_minutes: int = 15):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_minutes * 60
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, query: str, filters: SearchFilter, page: int, per_page: int) -> str:
        """Crear clave única para cache"""
        filter_dict = asdict(filters) if filters else {}
        key_data = {
            "query": query.lower().strip(),
            "filters": filter_dict,
            "page": page,
            "per_page": per_page
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, query: str, filters: SearchFilter, page: int, per_page: int) -> Optional[SearchResponse]:
        """Obtener resultado del cache"""
        key = self._make_key(query, filters, page, per_page)
        
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            
            # Verificar TTL
            if time.time() - timestamp < self.ttl_seconds:
                # Mover al final (LRU)
                self.cache.move_to_end(key)
                self.hits += 1
                
                # Marcar como desde cache
                cached_data.from_cache = True
                return cached_data
            else:
                # Expirado, eliminar
                del self.cache[key]
        
        self.misses += 1
        return None
    
    def put(self, query: str, filters: SearchFilter, page: int, per_page: int, response: SearchResponse):
        """Guardar resultado en cache"""
        key = self._make_key(query, filters, page, per_page)
        
        # Eliminar más antiguo si excede tamaño
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        
        # Agregar al final
        self.cache[key] = (response, time.time())
    
    def clear(self):
        """Limpiar cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas del cache"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "cache_size": len(self.cache),
            "max_size": self.max_size
        }

class UnifiedSearchSystem:
    """Sistema de búsqueda unificado"""
    
    def __init__(self, storage_manager):
        """Inicializar sistema de búsqueda"""
        self.storage_manager = storage_manager
        
        # Cache de resultados
        cache_size = int(os.getenv('SEARCH_CACHE_SIZE', '100'))
        cache_ttl = int(os.getenv('SEARCH_CACHE_TTL_MINUTES', '15'))
        self.cache = SearchCache(cache_size, cache_ttl)
        
        # Configuración
        self.config = {
            "enable_fuzzy_search": os.getenv('ENABLE_FUZZY_SEARCH', 'true').lower() == 'true' and FUZZY_SEARCH_AVAILABLE,
            "fuzzy_threshold": int(os.getenv('FUZZY_SEARCH_THRESHOLD', '80')),
            "parallel_search": os.getenv('ENABLE_PARALLEL_SEARCH', 'true').lower() == 'true',
            "search_timeout_seconds": int(os.getenv('SEARCH_TIMEOUT_SECONDS', '30')),
            "min_relevance_score": float(os.getenv('MIN_RELEVANCE_SCORE', '0.1')),
            "max_results_per_source": int(os.getenv('MAX_RESULTS_PER_SOURCE', '500')),
            "enable_search_cache": os.getenv('ENABLE_SEARCH_CACHE', 'true').lower() == 'true'
        }
        
        # Estadísticas
        self.stats = {
            "total_searches": 0,
            "cache_hits": 0,
            "avg_search_time_ms": 0,
            "search_by_source": {source.value: 0 for source in SearchSource},
            "last_search_time": None
        }
        
        logger.info("🔍 [UNIFIED_SEARCH] Sistema de búsqueda unificado iniciado")
        logger.info(f"   Cache: {'Habilitado' if self.config['enable_search_cache'] else 'Deshabilitado'}")
        logger.info(f"   Fuzzy Search: {'Habilitado' if self.config['enable_fuzzy_search'] else 'Deshabilitado'}")
        logger.info(f"   Búsqueda paralela: {'Habilitada' if self.config['parallel_search'] else 'Deshabilitada'}")
    
    def buscar(self, query: str, page: int = 1, per_page: int = 20, 
              filters: Optional[SearchFilter] = None) -> SearchResponse:
        """
        Realizar búsqueda unificada en todas las fuentes
        """
        start_time = time.time()
        
        # Verificar cache primero
        if self.config['enable_search_cache']:
            cached_result = self.cache.get(query, filters, page, per_page)
            if cached_result:
                self.stats["cache_hits"] += 1
                logger.info(f"🎯 [SEARCH_CACHE] Resultado desde cache: '{query}'")
                return cached_result
        
        try:
            logger.info(f"🔍 [SEARCH] Búsqueda unificada: '{query}' (página {page})")
            
            # Normalizar query
            normalized_query = self._normalize_query(query)
            
            # Buscar en paralelo si está habilitado
            if self.config['parallel_search']:
                all_results = self._search_parallel(normalized_query, filters)
            else:
                all_results = self._search_sequential(normalized_query, filters)
            
            # Calcular relevancia y ordenar
            scored_results = self._calculate_relevance(all_results, normalized_query)
            
            # Filtrar por relevancia mínima
            filtered_results = [
                r for r in scored_results 
                if r.relevancia_score >= self.config['min_relevance_score']
            ]
            
            # Aplicar filtros adicionales
            if filters:
                filtered_results = self._apply_filters(filtered_results, filters)
            
            # Paginación
            total = len(filtered_results)
            start = (page - 1) * per_page
            end = start + per_page
            paginated_results = filtered_results[start:end]
            
            # Crear respuesta
            search_time_ms = int((time.time() - start_time) * 1000)
            
            fuentes_consultadas = list(set(r.fuente for r in all_results))
            
            response = SearchResponse(
                resultados=paginated_results,
                total=total,
                page=page,
                per_page=per_page,
                total_pages=(total + per_page - 1) // per_page,
                query=query,
                filters=filters or SearchFilter(),
                fuentes_consultadas=fuentes_consultadas,
                tiempo_busqueda_ms=search_time_ms,
                estadisticas={
                    "resultados_por_fuente": {
                        source.value: len([r for r in all_results if r.fuente == source])
                        for source in fuentes_consultadas
                    },
                    "promedio_relevancia": sum(r.relevancia_score for r in paginated_results) / len(paginated_results) if paginated_results else 0,
                    "tipos_resultado": {
                        tipo.value: len([r for r in paginated_results if r.tipo == tipo])
                        for tipo in SearchResultType
                    }
                }
            )
            
            # Guardar en cache
            if self.config['enable_search_cache']:
                self.cache.put(query, filters, page, per_page, response)
            
            # Actualizar estadísticas
            self._update_stats(search_time_ms, fuentes_consultadas)
            
            logger.info(f"🎯 [SEARCH] {len(paginated_results)}/{total} resultados en {search_time_ms}ms")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ [SEARCH] Error en búsqueda: {e}")
            return SearchResponse(
                resultados=[],
                total=0,
                page=page,
                per_page=per_page,
                total_pages=0,
                query=query,
                filters=filters or SearchFilter(),
                fuentes_consultadas=[],
                tiempo_busqueda_ms=int((time.time() - start_time) * 1000),
                estadisticas={"error": str(e)}
            )
    
    def _search_parallel(self, query: str, filters: Optional[SearchFilter]) -> List[SearchResult]:
        """Buscar en paralelo en todas las fuentes"""
        import concurrent.futures
        
        all_results = []
        search_functions = [
            ("supabase", self._search_supabase),
            ("json_local", self._search_json_local),
            ("cloudinary", self._search_cloudinary),
            ("google_drive", self._search_google_drive)
        ]
        
        # Filtrar fuentes según filtros
        if filters and filters.fuente:
            search_functions = [(name, func) for name, func in search_functions if name == filters.fuente.value]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Enviar tareas
            future_to_source = {
                executor.submit(func, query, filters): source_name
                for source_name, func in search_functions
            }
            
            # Recoger resultados con timeout
            for future in concurrent.futures.as_completed(
                future_to_source, 
                timeout=self.config['search_timeout_seconds']
            ):
                source_name = future_to_source[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                    logger.debug(f"✅ [SEARCH_{source_name.upper()}] {len(results)} resultados")
                except Exception as e:
                    logger.error(f"❌ [SEARCH_{source_name.upper()}] Error: {e}")
        
        return all_results
    
    def _search_sequential(self, query: str, filters: Optional[SearchFilter]) -> List[SearchResult]:
        """Buscar secuencialmente en todas las fuentes"""
        all_results = []
        
        search_functions = [
            ("supabase", self._search_supabase),
            ("json_local", self._search_json_local),
            ("cloudinary", self._search_cloudinary),
            ("google_drive", self._search_google_drive)
        ]
        
        # Filtrar fuentes según filtros
        if filters and filters.fuente:
            search_functions = [(name, func) for name, func in search_functions if name == filters.fuente.value]
        
        for source_name, search_func in search_functions:
            try:
                results = search_func(query, filters)
                all_results.extend(results)
                logger.debug(f"✅ [SEARCH_{source_name.upper()}] {len(results)} resultados")
            except Exception as e:
                logger.error(f"❌ [SEARCH_{source_name.upper()}] Error: {e}")
        
        return all_results
    
    def _search_supabase(self, query: str, filters: Optional[SearchFilter]) -> List[SearchResult]:
        """Buscar en Supabase PostgreSQL"""
        results = []
        
        try:
            if self.storage_manager.system_health.supabase.value != "online":
                return results
            
            # Realizar búsqueda con límite alto para filtrar localmente
            search_result = self.storage_manager.supabase.buscar_cotizaciones(
                query, 1, self.config['max_results_per_source']
            )
            
            if search_result.get('error'):
                logger.warning(f"⚠️ [SEARCH_SUPABASE] Error: {search_result['error']}")
                return results
            
            cotizaciones = search_result.get('resultados', [])
            
            for cot in cotizaciones:
                datos_gen = cot.get('datosGenerales', {})
                
                result = SearchResult(
                    id=str(cot.get('_id', cot.get('id', ''))),
                    numero_cotizacion=cot.get('numeroCotizacion', ''),
                    cliente=datos_gen.get('cliente', ''),
                    vendedor=datos_gen.get('vendedor', ''),
                    proyecto=datos_gen.get('proyecto', ''),
                    fecha_creacion=self._parse_date(cot.get('fechaCreacion')),
                    tipo=SearchResultType.COTIZACION,
                    fuente=SearchSource.SUPABASE,
                    tiene_desglose=True,
                    revision=cot.get('revision', 1),
                    observaciones=cot.get('observaciones', ''),
                    metadata={
                        "items_count": len(cot.get('items', [])),
                        "version": cot.get('version', ''),
                        "timestamp": cot.get('timestamp', 0)
                    }
                )
                results.append(result)
            
            self.stats["search_by_source"]["supabase"] += 1
            
        except Exception as e:
            logger.error(f"❌ [SEARCH_SUPABASE] Error: {e}")
        
        return results
    
    def _search_json_local(self, query: str, filters: Optional[SearchFilter]) -> List[SearchResult]:
        """Buscar en JSON local"""
        results = []
        
        try:
            json_data = self.storage_manager.supabase._cargar_datos_offline()
            cotizaciones = json_data.get('cotizaciones', [])
            
            for cot in cotizaciones:
                datos_gen = cot.get('datosGenerales', {})
                
                # Aplicar filtro básico de texto
                if query and not self._matches_text_query(cot, query):
                    continue
                
                result = SearchResult(
                    id=str(cot.get('_id', cot.get('id', hash(str(cot))))),
                    numero_cotizacion=cot.get('numeroCotizacion', ''),
                    cliente=datos_gen.get('cliente', ''),
                    vendedor=datos_gen.get('vendedor', ''),
                    proyecto=datos_gen.get('proyecto', ''),
                    fecha_creacion=self._parse_date(cot.get('fechaCreacion')),
                    tipo=SearchResultType.COTIZACION,
                    fuente=SearchSource.JSON_LOCAL,
                    tiene_desglose=True,
                    revision=cot.get('revision', 1),
                    observaciones=cot.get('observaciones', ''),
                    metadata={
                        "items_count": len(cot.get('items', [])),
                        "from_offline": True,
                        "timestamp": cot.get('timestamp', 0)
                    }
                )
                results.append(result)
            
            self.stats["search_by_source"]["json_local"] += 1
            
        except Exception as e:
            logger.error(f"❌ [SEARCH_JSON_LOCAL] Error: {e}")
        
        return results
    
    def _search_cloudinary(self, query: str, filters: Optional[SearchFilter]) -> List[SearchResult]:
        """Buscar PDFs en Cloudinary"""
        results = []
        
        try:
            if not self.storage_manager.cloudinary.is_available():
                return results
            
            # Buscar en ambas carpetas
            carpetas = ["nuevas", "antiguas"] if not filters or not filters.tipo_resultado else ["nuevas"]
            
            for carpeta in carpetas:
                try:
                    cloudinary_results = self.storage_manager.cloudinary.listar_pdfs(
                        folder=carpeta,
                        max_resultados=self.config['max_results_per_source'] // 2
                    )
                    
                    archivos = cloudinary_results.get('archivos', [])
                    
                    for archivo in archivos:
                        numero_cot = archivo.get('numero_cotizacion', '')
                        
                        # Filtro básico de texto
                        if query and query.lower() not in numero_cot.lower():
                            continue
                        
                        result = SearchResult(
                            id=archivo.get('public_id', ''),
                            numero_cotizacion=numero_cot,
                            cliente="Cloudinary",
                            proyecto=numero_cot,
                            fecha_creacion=self._parse_date(archivo.get('fecha_creacion')),
                            tipo=SearchResultType.PDF_CLOUDINARY,
                            fuente=SearchSource.CLOUDINARY,
                            tiene_pdf=True,
                            url_pdf=archivo.get('url', ''),
                            metadata={
                                "bytes": archivo.get('bytes', 0),
                                "version": archivo.get('version', ''),
                                "carpeta": carpeta,
                                "tags": archivo.get('tags', [])
                            }
                        )
                        results.append(result)
                        
                except Exception as e:
                    logger.error(f"❌ [SEARCH_CLOUDINARY_{carpeta}] Error: {e}")
            
            self.stats["search_by_source"]["cloudinary"] += 1
            
        except Exception as e:
            logger.error(f"❌ [SEARCH_CLOUDINARY] Error: {e}")
        
        return results
    
    def _search_google_drive(self, query: str, filters: Optional[SearchFilter]) -> List[SearchResult]:
        """Buscar PDFs en Google Drive"""
        results = []
        
        try:
            if not self.storage_manager.google_drive.is_available():
                return results
            
            drive_pdfs = self.storage_manager.google_drive.buscar_pdfs(query)
            
            for pdf in drive_pdfs:
                result = SearchResult(
                    id=pdf.get('id', ''),
                    numero_cotizacion=pdf.get('numero_cotizacion', ''),
                    cliente="Google Drive (Histórico)",
                    proyecto=pdf.get('numero_cotizacion', ''),
                    fecha_creacion=self._parse_date(pdf.get('fecha_modificacion')),
                    tipo=SearchResultType.PDF_HISTORICO,
                    fuente=SearchSource.GOOGLE_DRIVE,
                    tiene_pdf=True,
                    metadata={
                        "drive_id": pdf.get('id', ''),
                        "tamaño": pdf.get('tamaño', ''),
                        "carpeta_origen": pdf.get('carpeta_origen', 'desconocida')
                    }
                )
                results.append(result)
            
            self.stats["search_by_source"]["google_drive"] += 1
            
        except Exception as e:
            logger.error(f"❌ [SEARCH_GOOGLE_DRIVE] Error: {e}")
        
        return results
    
    def _matches_text_query(self, item: Dict, query: str) -> bool:
        """Verificar si un item coincide con el query de texto"""
        if not query:
            return True
        
        query_lower = query.lower()
        search_fields = [
            str(item.get('numeroCotizacion', '')),
            str(item.get('datosGenerales', {}).get('cliente', '')),
            str(item.get('datosGenerales', {}).get('vendedor', '')),
            str(item.get('datosGenerales', {}).get('proyecto', '')),
            str(item.get('datosGenerales', {}).get('atencionA', '')),
            str(item.get('observaciones', ''))
        ]
        
        # Búsqueda exacta
        for field in search_fields:
            if query_lower in field.lower():
                return True
        
        # Búsqueda difusa si está habilitada
        if self.config['enable_fuzzy_search']:
            for field in search_fields:
                if field and fuzz.partial_ratio(query_lower, field.lower()) >= self.config['fuzzy_threshold']:
                    return True
        
        return False
    
    def _calculate_relevance(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """Calcular relevancia de resultados y ordenar"""
        if not query:
            # Sin query, ordenar por fecha
            return sorted(results, key=lambda r: r.fecha_creacion or datetime.min, reverse=True)
        
        query_lower = query.lower()
        
        for result in results:
            score = 0.0
            
            # Coincidencia exacta en número de cotización (máxima relevancia)
            if query_lower == result.numero_cotizacion.lower():
                score += 100.0
            elif query_lower in result.numero_cotizacion.lower():
                score += 50.0
            
            # Coincidencia en cliente
            if query_lower in result.cliente.lower():
                score += 30.0
            
            # Coincidencia en proyecto
            if query_lower in result.proyecto.lower():
                score += 20.0
            
            # Coincidencia en vendedor
            if query_lower in result.vendedor.lower():
                score += 15.0
            
            # Bonus por fuente confiable
            if result.fuente == SearchSource.SUPABASE:
                score += 10.0
            elif result.fuente == SearchSource.JSON_LOCAL:
                score += 8.0
            
            # Bonus por tener desglose
            if result.tiene_desglose:
                score += 5.0
            
            # Penalización por antigüedad (últimos 30 días más relevantes)
            if result.fecha_creacion:
                days_old = (datetime.now() - result.fecha_creacion).days
                if days_old <= 30:
                    score += 5.0 - (days_old / 6)  # Decae gradualmente
            
            # Búsqueda difusa si está habilitada
            if self.config['enable_fuzzy_search']:
                search_text = f"{result.numero_cotizacion} {result.cliente} {result.proyecto}".lower()
                fuzzy_score = fuzz.partial_ratio(query_lower, search_text)
                score += fuzzy_score / 10  # Normalizar a 0-10
            
            # Normalizar score a 0-1
            result.relevancia_score = min(score / 100.0, 1.0)
        
        # Ordenar por relevancia descendente, luego por fecha
        return sorted(
            results,
            key=lambda r: (r.relevancia_score, r.fecha_creacion or datetime.min),
            reverse=True
        )
    
    def _apply_filters(self, results: List[SearchResult], filters: SearchFilter) -> List[SearchResult]:
        """Aplicar filtros adicionales a los resultados"""
        filtered = results
        
        if filters.cliente:
            filtered = [r for r in filtered if filters.cliente.lower() in r.cliente.lower()]
        
        if filters.vendedor:
            filtered = [r for r in filtered if filters.vendedor.lower() in r.vendedor.lower()]
        
        if filters.proyecto:
            filtered = [r for r in filtered if filters.proyecto.lower() in r.proyecto.lower()]
        
        if filters.fecha_desde:
            filtered = [r for r in filtered if r.fecha_creacion and r.fecha_creacion >= filters.fecha_desde]
        
        if filters.fecha_hasta:
            filtered = [r for r in filtered if r.fecha_creacion and r.fecha_creacion <= filters.fecha_hasta]
        
        if filters.tipo_resultado:
            filtered = [r for r in filtered if r.tipo == filters.tipo_resultado]
        
        if filters.fuente:
            filtered = [r for r in filtered if r.fuente == filters.fuente]
        
        if filters.solo_con_desglose is not None:
            filtered = [r for r in filtered if r.tiene_desglose == filters.solo_con_desglose]
        
        if filters.revision_minima:
            filtered = [r for r in filtered if r.revision >= filters.revision_minima]
        
        return filtered
    
    def _normalize_query(self, query: str) -> str:
        """Normalizar query de búsqueda"""
        if not query:
            return ""
        
        # Limpiar espacios extra
        normalized = re.sub(r'\s+', ' ', query.strip())
        
        # Expandir abreviaciones comunes
        replacements = {
            'cot': 'cotizacion',
            'cli': 'cliente',
            'vend': 'vendedor',
            'proy': 'proyecto'
        }
        
        for abbrev, full in replacements.items():
            normalized = re.sub(r'\b' + abbrev + r'\b', full, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """Parsear fecha de diferentes formatos"""
        if not date_str:
            return None
        
        if isinstance(date_str, datetime):
            return date_str
        
        if isinstance(date_str, (int, float)):
            try:
                return datetime.fromtimestamp(date_str / 1000 if date_str > 1e10 else date_str)
            except:
                return None
        
        if isinstance(date_str, str):
            # Intentar diferentes formatos
            formats = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%d/%m/%Y',
                '%m/%d/%Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.replace('Z', ''), fmt)
                except:
                    continue
        
        return None
    
    def _update_stats(self, search_time_ms: int, fuentes_consultadas: List[SearchSource]):
        """Actualizar estadísticas de búsqueda"""
        self.stats["total_searches"] += 1
        self.stats["last_search_time"] = datetime.now()
        
        # Calcular promedio móvil del tiempo de búsqueda
        current_avg = self.stats["avg_search_time_ms"]
        total_searches = self.stats["total_searches"]
        
        self.stats["avg_search_time_ms"] = (
            (current_avg * (total_searches - 1) + search_time_ms) / total_searches
        )
    
    def buscar_por_numero_exacto(self, numero_cotizacion: str) -> Optional[SearchResult]:
        """Buscar cotización por número exacto (optimizado)"""
        try:
            # Intentar en Supabase primero
            result = self.storage_manager.obtener_cotizacion(numero_cotizacion)
            
            if result.success and result.data.get('encontrado'):
                item = result.data['item']
                datos_gen = item.get('datosGenerales', {})
                
                return SearchResult(
                    id=str(item.get('_id', item.get('id', ''))),
                    numero_cotizacion=item.get('numeroCotizacion', numero_cotizacion),
                    cliente=datos_gen.get('cliente', ''),
                    vendedor=datos_gen.get('vendedor', ''),
                    proyecto=datos_gen.get('proyecto', ''),
                    fecha_creacion=self._parse_date(item.get('fechaCreacion')),
                    tipo=SearchResultType.COTIZACION,
                    fuente=SearchSource.SUPABASE if result.source == 'supabase' else SearchSource.JSON_LOCAL,
                    relevancia_score=1.0,  # Coincidencia exacta
                    tiene_desglose=True,
                    revision=item.get('revision', 1),
                    metadata={"exact_match": True}
                )
            
        except Exception as e:
            logger.error(f"❌ [SEARCH_EXACT] Error: {e}")
        
        return None
    
    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Obtener sugerencias de búsqueda"""
        suggestions = []
        
        if len(partial_query) < 2:
            return suggestions
        
        try:
            # Obtener datos únicos para sugerencias
            suggestions_data = set()
            
            # Desde Supabase/JSON
            if self.storage_manager.system_health.supabase.value == "online":
                try:
                    search_result = self.storage_manager.supabase.buscar_cotizaciones("", 1, 100)
                    for cot in search_result.get('resultados', []):
                        datos_gen = cot.get('datosGenerales', {})
                        suggestions_data.add(cot.get('numeroCotizacion', ''))
                        suggestions_data.add(datos_gen.get('cliente', ''))
                        suggestions_data.add(datos_gen.get('vendedor', ''))
                        suggestions_data.add(datos_gen.get('proyecto', ''))
                except:
                    pass
            
            # Filtrar sugerencias que coincidan con la consulta parcial
            partial_lower = partial_query.lower()
            matching_suggestions = [
                s for s in suggestions_data 
                if s and len(s) > 1 and partial_lower in s.lower()
            ]
            
            # Ordenar por relevancia y limitar
            if self.config['enable_fuzzy_search']:
                scored_suggestions = [
                    (s, fuzz.partial_ratio(partial_lower, s.lower()))
                    for s in matching_suggestions
                ]
                scored_suggestions.sort(key=lambda x: x[1], reverse=True)
                suggestions = [s[0] for s in scored_suggestions[:limit]]
            else:
                suggestions = sorted(matching_suggestions)[:limit]
            
        except Exception as e:
            logger.error(f"❌ [SEARCH_SUGGESTIONS] Error: {e}")
        
        return suggestions
    
    def clear_cache(self):
        """Limpiar cache de búsqueda"""
        self.cache.clear()
        logger.info("🧹 [SEARCH_CACHE] Cache limpiado")
    
    def get_system_stats(self) -> Dict:
        """Obtener estadísticas del sistema de búsqueda"""
        return {
            "search_stats": self.stats,
            "cache_stats": self.cache.get_stats() if self.config['enable_search_cache'] else None,
            "configuration": self.config,
            "fuzzy_search_available": FUZZY_SEARCH_AVAILABLE
        }


if __name__ == "__main__":
    # Test del sistema de búsqueda
    from unified_storage_manager import UnifiedStorageManager
    
    storage_manager = UnifiedStorageManager()
    search_system = UnifiedSearchSystem(storage_manager)
    
    # Test de búsqueda
    response = search_system.buscar("test", page=1, per_page=10)
    print(json.dumps(asdict(response), indent=2, default=str))
    
    # Test de estadísticas
    stats = search_system.get_system_stats()
    print(json.dumps(stats, indent=2, default=str))