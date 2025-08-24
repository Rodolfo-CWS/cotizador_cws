#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UNIFIED DATABASE SCHEMA - CWS COTIZADOR
======================================

Esquema de base de datos unificado para el sistema que integra:
- Supabase PostgreSQL (principal)
- JSON local (offline/desarrollo)
- Cloudinary (metadatos de PDFs)
- Google Drive (índice de archivos)

Características:
- Schema único compatible con todos los sistemas
- Versionado de esquema automático
- Migración automática de estructuras
- Validación de integridad referencial
- Índices optimizados para búsquedas

Versión: 1.0.0 - Esquema Inicial Unificado
Fecha: 2025-08-19
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

# ===== DEFINICIONES DE ESQUEMA =====

@dataclass
class SchemaVersion:
    """Información de versión del esquema"""
    version: str
    applied_at: datetime
    description: str
    migrations_applied: List[str] = None
    
    def __post_init__(self):
        if self.migrations_applied is None:
            self.migrations_applied = []

# Esquema principal para cotizaciones
COTIZACIONES_SCHEMA = {
    "table_name": "cotizaciones",
    "version": "1.0.0",
    "description": "Tabla principal de cotizaciones CWS",
    "columns": {
        # Identificación única
        "id": {
            "type": "uuid",
            "primary_key": True,
            "default": "gen_random_uuid()",
            "description": "ID único del registro"
        },
        
        # Información de negocio
        "numero_cotizacion": {
            "type": "varchar(100)",
            "unique": True,
            "not_null": True,
            "index": True,
            "description": "Número único de cotización (formato: CLIENTE-CWS-VENDOR-###-R#-PROYECTO)"
        },
        
        "revision": {
            "type": "integer",
            "default": 1,
            "not_null": True,
            "description": "Número de revisión de la cotización"
        },
        
        # Datos del cliente (JSON normalizado)
        "datos_generales": {
            "type": "jsonb",
            "not_null": True,
            "description": "Información general del cliente y proyecto",
            "schema": {
                "cliente": {"type": "string", "required": True},
                "vendedor": {"type": "string", "required": True},
                "proyecto": {"type": "string", "required": True},
                "atencion_a": {"type": "string"},
                "telefono": {"type": "string"},
                "email": {"type": "string"},
                "fecha": {"type": "string"}
            }
        },
        
        # Items de la cotización
        "items": {
            "type": "jsonb",
            "default": "[]",
            "description": "Array de items cotizados",
            "schema": {
                "type": "array",
                "items": {
                    "material": {"type": "string", "required": True},
                    "cantidad": {"type": "number", "required": True},
                    "precio": {"type": "number", "required": True},
                    "unidad": {"type": "string", "default": "unidad"},
                    "categoria": {"type": "string"}
                }
            }
        },
        
        # Totales calculados
        "totales": {
            "type": "jsonb",
            "description": "Totales calculados de la cotización",
            "schema": {
                "subtotal": {"type": "number"},
                "descuento": {"type": "number", "default": 0},
                "impuestos": {"type": "number", "default": 0},
                "total": {"type": "number"}
            }
        },
        
        # Observaciones y notas
        "observaciones": {
            "type": "text",
            "description": "Observaciones y notas adicionales"
        },
        
        # Metadatos del sistema
        "fecha_creacion": {
            "type": "timestamp with time zone",
            "default": "now()",
            "not_null": True,
            "index": True,
            "description": "Fecha y hora de creación"
        },
        
        "fecha_modificacion": {
            "type": "timestamp with time zone",
            "default": "now()",
            "not_null": True,
            "description": "Fecha y hora de última modificación"
        },
        
        "version": {
            "type": "varchar(10)",
            "default": "'1.0'",
            "description": "Versión del formato de datos"
        },
        
        "estado": {
            "type": "varchar(20)",
            "default": "'activa'",
            "description": "Estado de la cotización (activa, archivada, eliminada)"
        },
        
        # Control de sincronización
        "timestamp": {
            "type": "bigint",
            "description": "Timestamp Unix para sincronización"
        },
        
        "hash_contenido": {
            "type": "varchar(64)",
            "description": "Hash MD5 del contenido para detección de cambios"
        },
        
        "sincronizado": {
            "type": "boolean",
            "default": "true",
            "description": "Indica si el registro está sincronizado"
        },
        
        # Metadatos adicionales
        "metadata": {
            "type": "jsonb",
            "default": "{}",
            "description": "Metadatos adicionales del sistema",
            "schema": {
                "fuente_creacion": {"type": "string"},
                "ip_creacion": {"type": "string"},
                "user_agent": {"type": "string"},
                "migracion_id": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    
    "indexes": [
        {
            "name": "idx_numero_cotizacion",
            "columns": ["numero_cotizacion"],
            "unique": True
        },
        {
            "name": "idx_fecha_creacion", 
            "columns": ["fecha_creacion"],
            "type": "btree"
        },
        {
            "name": "idx_cliente_gin",
            "columns": ["(datos_generales->'cliente')"],
            "type": "gin"
        },
        {
            "name": "idx_vendedor_gin",
            "columns": ["(datos_generales->'vendedor')"],
            "type": "gin"
        },
        {
            "name": "idx_items_gin",
            "columns": ["items"],
            "type": "gin"
        },
        {
            "name": "idx_busqueda_texto",
            "expression": "to_tsvector('spanish', coalesce(numero_cotizacion,'') || ' ' || coalesce(datos_generales->>'cliente','') || ' ' || coalesce(datos_generales->>'proyecto',''))",
            "type": "gin"
        }
    ],
    
    "constraints": [
        {
            "name": "chk_revision_positiva",
            "type": "check",
            "expression": "revision > 0"
        },
        {
            "name": "chk_estado_valido",
            "type": "check", 
            "expression": "estado IN ('activa', 'archivada', 'eliminada')"
        }
    ]
}

# Esquema para archivos PDF
PDF_FILES_SCHEMA = {
    "table_name": "pdf_files",
    "version": "1.0.0",
    "description": "Índice de archivos PDF almacenados",
    "columns": {
        "id": {
            "type": "uuid",
            "primary_key": True,
            "default": "gen_random_uuid()"
        },
        
        "numero_cotizacion": {
            "type": "varchar(100)",
            "not_null": True,
            "index": True,
            "description": "Número de cotización asociado"
        },
        
        # Información del archivo
        "nombre_archivo": {
            "type": "varchar(255)",
            "not_null": True,
            "description": "Nombre original del archivo"
        },
        
        "tamaño_bytes": {
            "type": "bigint",
            "description": "Tamaño del archivo en bytes"
        },
        
        "hash_contenido": {
            "type": "varchar(64)",
            "description": "Hash SHA256 del contenido del PDF"
        },
        
        # Ubicaciones de almacenamiento (múltiples proveedores)
        "ubicaciones": {
            "type": "jsonb",
            "default": "{}",
            "description": "URLs y metadatos de almacenamiento por proveedor",
            "schema": {
                "cloudinary": {
                    "url": {"type": "string"},
                    "public_id": {"type": "string"},
                    "version": {"type": "string"},
                    "folder": {"type": "string"}
                },
                "google_drive": {
                    "file_id": {"type": "string"},
                    "url": {"type": "string"},
                    "folder_id": {"type": "string"}
                },
                "local": {
                    "ruta": {"type": "string"},
                    "existe": {"type": "boolean"}
                }
            }
        },
        
        "proveedor_principal": {
            "type": "varchar(20)",
            "default": "'cloudinary'",
            "description": "Proveedor de almacenamiento principal"
        },
        
        # Metadatos de fechas
        "fecha_creacion": {
            "type": "timestamp with time zone",
            "default": "now()",
            "not_null": True
        },
        
        "fecha_subida": {
            "type": "timestamp with time zone",
            "description": "Fecha de primera subida a almacenamiento"
        },
        
        "fecha_ultimo_acceso": {
            "type": "timestamp with time zone",
            "description": "Fecha de último acceso al archivo"
        },
        
        # Estado y validación
        "estado": {
            "type": "varchar(20)",
            "default": "'disponible'",
            "description": "Estado del archivo (disponible, procesando, error, eliminado)"
        },
        
        "verificado": {
            "type": "boolean",
            "default": "false",
            "description": "Indica si la integridad del archivo ha sido verificada"
        },
        
        "ultima_verificacion": {
            "type": "timestamp with time zone",
            "description": "Fecha de última verificación de integridad"
        },
        
        # Metadatos adicionales
        "metadata": {
            "type": "jsonb",
            "default": "{}",
            "description": "Metadatos adicionales del PDF"
        }
    },
    
    "indexes": [
        {
            "name": "idx_pdf_numero_cotizacion",
            "columns": ["numero_cotizacion"]
        },
        {
            "name": "idx_pdf_fecha_creacion",
            "columns": ["fecha_creacion"]
        },
        {
            "name": "idx_pdf_hash",
            "columns": ["hash_contenido"]
        },
        {
            "name": "idx_pdf_ubicaciones_gin",
            "columns": ["ubicaciones"],
            "type": "gin"
        }
    ],
    
    "foreign_keys": [
        {
            "name": "fk_pdf_cotizacion",
            "columns": ["numero_cotizacion"],
            "references": {
                "table": "cotizaciones",
                "columns": ["numero_cotizacion"]
            },
            "on_delete": "cascade"
        }
    ]
}

# Esquema para log del sistema
SYSTEM_LOGS_SCHEMA = {
    "table_name": "system_logs",
    "version": "1.0.0", 
    "description": "Logs del sistema unificado",
    "columns": {
        "id": {
            "type": "uuid",
            "primary_key": True,
            "default": "gen_random_uuid()"
        },
        
        "timestamp": {
            "type": "timestamp with time zone",
            "default": "now()",
            "not_null": True,
            "index": True
        },
        
        "nivel": {
            "type": "varchar(10)",
            "not_null": True,
            "description": "Nivel del log (INFO, WARNING, ERROR, CRITICAL)"
        },
        
        "modulo": {
            "type": "varchar(50)",
            "description": "Módulo que generó el log"
        },
        
        "mensaje": {
            "type": "text",
            "not_null": True,
            "description": "Mensaje del log"
        },
        
        "contexto": {
            "type": "jsonb",
            "default": "{}",
            "description": "Contexto adicional del evento"
        },
        
        "usuario": {
            "type": "varchar(50)",
            "description": "Usuario relacionado con el evento"
        },
        
        "ip_address": {
            "type": "inet",
            "description": "Dirección IP del origen"
        }
    },
    
    "indexes": [
        {
            "name": "idx_logs_timestamp",
            "columns": ["timestamp"]
        },
        {
            "name": "idx_logs_nivel",
            "columns": ["nivel"]
        },
        {
            "name": "idx_logs_modulo",
            "columns": ["modulo"]
        }
    ],
    
    "partitioning": {
        "type": "range",
        "column": "timestamp",
        "interval": "1 month"
    }
}

# Esquema para configuración del sistema
SYSTEM_CONFIG_SCHEMA = {
    "table_name": "system_config",
    "version": "1.0.0",
    "description": "Configuración del sistema unificado",
    "columns": {
        "clave": {
            "type": "varchar(100)",
            "primary_key": True,
            "description": "Clave de configuración"
        },
        
        "valor": {
            "type": "jsonb",
            "not_null": True,
            "description": "Valor de configuración (JSON)"
        },
        
        "descripcion": {
            "type": "text",
            "description": "Descripción de la configuración"
        },
        
        "categoria": {
            "type": "varchar(50)",
            "description": "Categoría de configuración"
        },
        
        "modificado_en": {
            "type": "timestamp with time zone",
            "default": "now()"
        },
        
        "modificado_por": {
            "type": "varchar(50)",
            "description": "Usuario que modificó la configuración"
        }
    }
}

# ===== GENERADOR DE SQL =====

class UnifiedSchemaManager:
    """Gestor del esquema unificado de base de datos"""
    
    def __init__(self):
        self.schemas = {
            "cotizaciones": COTIZACIONES_SCHEMA,
            "pdf_files": PDF_FILES_SCHEMA, 
            "system_logs": SYSTEM_LOGS_SCHEMA,
            "system_config": SYSTEM_CONFIG_SCHEMA
        }
        
        self.current_version = "1.0.0"
        logger.info(f"🗄️ [SCHEMA] Schema Manager inicializado v{self.current_version}")
    
    def generate_create_table_sql(self, schema: Dict[str, Any]) -> str:
        """Generar SQL CREATE TABLE para un esquema"""
        table_name = schema["table_name"]
        columns = schema["columns"]
        
        sql_parts = [f"CREATE TABLE IF NOT EXISTS {table_name} ("]
        
        # Columnas
        column_definitions = []
        for col_name, col_def in columns.items():
            col_sql = f"  {col_name} {col_def['type']}"
            
            # Constraints de columna
            if col_def.get("primary_key"):
                col_sql += " PRIMARY KEY"
            if col_def.get("not_null"):
                col_sql += " NOT NULL"
            if col_def.get("unique"):
                col_sql += " UNIQUE"
            if col_def.get("default"):
                col_sql += f" DEFAULT {col_def['default']}"
            
            column_definitions.append(col_sql)
        
        sql_parts.append(",\n".join(column_definitions))
        
        # Constraints de tabla
        if "constraints" in schema:
            for constraint in schema["constraints"]:
                if constraint["type"] == "check":
                    sql_parts.append(f",\n  CONSTRAINT {constraint['name']} CHECK ({constraint['expression']})")
        
        sql_parts.append(");")
        
        return "\n".join(sql_parts)
    
    def generate_indexes_sql(self, schema: Dict[str, Any]) -> List[str]:
        """Generar SQL para crear índices"""
        indexes_sql = []
        table_name = schema["table_name"]
        
        if "indexes" in schema:
            for index in schema["indexes"]:
                index_name = index["name"]
                
                if "expression" in index:
                    # Índice funcional
                    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}"
                    if index.get("type"):
                        sql += f" USING {index['type']}"
                    sql += f" ({index['expression']});"
                else:
                    # Índice normal
                    columns = ", ".join(index["columns"])
                    sql = f"CREATE"
                    if index.get("unique"):
                        sql += " UNIQUE"
                    sql += f" INDEX IF NOT EXISTS {index_name} ON {table_name}"
                    if index.get("type"):
                        sql += f" USING {index['type']}"
                    sql += f" ({columns});"
                
                indexes_sql.append(sql)
        
        return indexes_sql
    
    def generate_foreign_keys_sql(self, schema: Dict[str, Any]) -> List[str]:
        """Generar SQL para claves foráneas"""
        fk_sql = []
        table_name = schema["table_name"]
        
        if "foreign_keys" in schema:
            for fk in schema["foreign_keys"]:
                columns = ", ".join(fk["columns"])
                ref_table = fk["references"]["table"]
                ref_columns = ", ".join(fk["references"]["columns"])
                
                sql = f"ALTER TABLE {table_name} ADD CONSTRAINT {fk['name']} "
                sql += f"FOREIGN KEY ({columns}) REFERENCES {ref_table} ({ref_columns})"
                
                if fk.get("on_delete"):
                    sql += f" ON DELETE {fk['on_delete'].upper()}"
                if fk.get("on_update"):
                    sql += f" ON UPDATE {fk['on_update'].upper()}"
                
                sql += ";"
                fk_sql.append(sql)
        
        return fk_sql
    
    def generate_full_schema_sql(self) -> str:
        """Generar SQL completo para todo el esquema"""
        sql_parts = [
            "-- ========================================",
            "-- CWS COTIZADOR - ESQUEMA UNIFICADO",
            f"-- Versión: {self.current_version}",
            f"-- Generado: {datetime.now().isoformat()}",
            "-- ========================================",
            "",
            "-- Habilitar extensiones necesarias",
            "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";",
            "CREATE EXTENSION IF NOT EXISTS \"pg_trgm\";",
            ""
        ]
        
        # Crear tablas
        sql_parts.append("-- ===== TABLAS =====")
        for schema_name, schema in self.schemas.items():
            sql_parts.append(f"-- Tabla: {schema['table_name']}")
            sql_parts.append(f"-- {schema['description']}")
            sql_parts.append(self.generate_create_table_sql(schema))
            sql_parts.append("")
        
        # Crear índices
        sql_parts.append("-- ===== ÍNDICES =====")
        for schema_name, schema in self.schemas.items():
            indexes = self.generate_indexes_sql(schema)
            if indexes:
                sql_parts.append(f"-- Índices para {schema['table_name']}")
                sql_parts.extend(indexes)
                sql_parts.append("")
        
        # Crear claves foráneas
        sql_parts.append("-- ===== CLAVES FORÁNEAS =====")
        for schema_name, schema in self.schemas.items():
            fks = self.generate_foreign_keys_sql(schema)
            if fks:
                sql_parts.append(f"-- FK para {schema['table_name']}")
                sql_parts.extend(fks)
                sql_parts.append("")
        
        # Configuración inicial
        sql_parts.extend([
            "-- ===== CONFIGURACIÓN INICIAL =====",
            "INSERT INTO system_config (clave, valor, descripcion, categoria) VALUES",
            "('schema_version', '\"1.0.0\"', 'Versión actual del esquema', 'sistema'),",
            "('created_at', '\"" + datetime.now().isoformat() + "\"', 'Fecha de creación del esquema', 'sistema'),",
            "('auto_vacuum', 'true', 'Habilitar auto-vacuum', 'performance'),",
            "('search_language', '\"spanish\"', 'Idioma para búsqueda full-text', 'search')",
            "ON CONFLICT (clave) DO UPDATE SET ",
            "  valor = EXCLUDED.valor,",
            "  modificado_en = now();",
            ""
        ])
        
        # Funciones auxiliares
        sql_parts.extend([
            "-- ===== FUNCIONES AUXILIARES =====",
            "",
            "-- Función para actualizar fecha_modificacion automáticamente",
            "CREATE OR REPLACE FUNCTION actualizar_fecha_modificacion()",
            "RETURNS TRIGGER AS $$",
            "BEGIN",
            "    NEW.fecha_modificacion = now();",
            "    RETURN NEW;",
            "END;",
            "$$ LANGUAGE plpgsql;",
            "",
            "-- Trigger para actualizar fecha_modificacion en cotizaciones",
            "DROP TRIGGER IF EXISTS trigger_actualizar_fecha_modificacion ON cotizaciones;",
            "CREATE TRIGGER trigger_actualizar_fecha_modificacion",
            "    BEFORE UPDATE ON cotizaciones",
            "    FOR EACH ROW",
            "    EXECUTE FUNCTION actualizar_fecha_modificacion();",
            "",
            "-- Función para búsqueda full-text",
            "CREATE OR REPLACE FUNCTION buscar_cotizaciones(termino text, limite integer DEFAULT 20)",
            "RETURNS TABLE(",
            "    numero_cotizacion varchar,",
            "    cliente text,",
            "    proyecto text,",
            "    fecha_creacion timestamp with time zone,",
            "    ranking real",
            ") AS $$",
            "BEGIN",
            "    RETURN QUERY",
            "    SELECT ",
            "        c.numero_cotizacion,",
            "        c.datos_generales->>'cliente' as cliente,",
            "        c.datos_generales->>'proyecto' as proyecto,",
            "        c.fecha_creacion,",
            "        ts_rank(to_tsvector('spanish', ",
            "            coalesce(c.numero_cotizacion,'') || ' ' || ",
            "            coalesce(c.datos_generales->>'cliente','') || ' ' ||",
            "            coalesce(c.datos_generales->>'proyecto','')",
            "        ), plainto_tsquery('spanish', termino)) as ranking",
            "    FROM cotizaciones c",
            "    WHERE to_tsvector('spanish', ",
            "        coalesce(c.numero_cotizacion,'') || ' ' || ",
            "        coalesce(c.datos_generales->>'cliente','') || ' ' ||",
            "        coalesce(c.datos_generales->>'proyecto','')",
            "    ) @@ plainto_tsquery('spanish', termino)",
            "    AND c.estado = 'activa'",
            "    ORDER BY ranking DESC",
            "    LIMIT limite;",
            "END;",
            "$$ LANGUAGE plpgsql;",
            ""
        ])
        
        return "\n".join(sql_parts)
    
    def generate_json_schema(self) -> Dict[str, Any]:
        """Generar esquema JSON compatible para validación"""
        json_schemas = {}
        
        for schema_name, schema in self.schemas.items():
            json_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": schema["description"],
                "type": "object",
                "properties": {},
                "required": []
            }
            
            for col_name, col_def in schema["columns"].items():
                prop_schema = self._convert_db_type_to_json_schema(col_def)
                json_schema["properties"][col_name] = prop_schema
                
                if col_def.get("not_null") and not col_def.get("default"):
                    json_schema["required"].append(col_name)
            
            json_schemas[schema_name] = json_schema
        
        return json_schemas
    
    def _convert_db_type_to_json_schema(self, col_def: Dict[str, Any]) -> Dict[str, Any]:
        """Convertir tipo de BD a esquema JSON"""
        db_type = col_def["type"].lower()
        
        # Mapeo de tipos
        if "varchar" in db_type or db_type == "text":
            return {"type": "string", "description": col_def.get("description", "")}
        elif db_type in ["integer", "bigint"]:
            return {"type": "integer", "description": col_def.get("description", "")}
        elif db_type in ["real", "numeric", "decimal"]:
            return {"type": "number", "description": col_def.get("description", "")}
        elif db_type == "boolean":
            return {"type": "boolean", "description": col_def.get("description", "")}
        elif db_type == "jsonb":
            schema = {"type": "object", "description": col_def.get("description", "")}
            if "schema" in col_def:
                schema.update(col_def["schema"])
            return schema
        elif "timestamp" in db_type:
            return {"type": "string", "format": "date-time", "description": col_def.get("description", "")}
        elif db_type == "uuid":
            return {"type": "string", "format": "uuid", "description": col_def.get("description", "")}
        else:
            return {"type": "string", "description": col_def.get("description", "")}
    
    def save_schema_files(self, output_dir: Optional[str] = None) -> Dict[str, str]:
        """Guardar archivos de esquema"""
        if output_dir is None:
            output_dir = Path(__file__).parent / "schema_output"
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        files_created = {}
        
        # SQL completo
        sql_file = output_path / "unified_schema.sql"
        sql_content = self.generate_full_schema_sql()
        sql_file.write_text(sql_content, encoding='utf-8')
        files_created["sql"] = str(sql_file)
        
        # Esquemas JSON
        json_schemas = self.generate_json_schema()
        json_file = output_path / "json_schemas.json"
        json_file.write_text(
            json.dumps(json_schemas, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        files_created["json"] = str(json_file)
        
        # Documentación
        doc_file = output_path / "schema_documentation.md"
        doc_content = self._generate_documentation()
        doc_file.write_text(doc_content, encoding='utf-8')
        files_created["documentation"] = str(doc_file)
        
        # Versión actual
        version_file = output_path / "schema_version.json"
        version_info = {
            "version": self.current_version,
            "created_at": datetime.now().isoformat(),
            "tables_count": len(self.schemas),
            "tables": list(self.schemas.keys())
        }
        version_file.write_text(
            json.dumps(version_info, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        files_created["version"] = str(version_file)
        
        logger.info(f"📁 [SCHEMA] Archivos guardados en: {output_path}")
        for file_type, file_path in files_created.items():
            logger.info(f"   📄 {file_type}: {Path(file_path).name}")
        
        return files_created
    
    def _generate_documentation(self) -> str:
        """Generar documentación del esquema"""
        doc_parts = [
            f"# CWS Cotizador - Esquema de Base de Datos Unificado",
            f"",
            f"**Versión:** {self.current_version}  ",
            f"**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Tablas:** {len(self.schemas)}",
            f"",
            f"## Descripción General",
            f"",
            f"Este esquema unificado está diseñado para soportar múltiples sistemas de almacenamiento:",
            f"- **Supabase PostgreSQL** (principal)",
            f"- **JSON Local** (desarrollo/offline)", 
            f"- **Cloudinary** (metadatos de PDFs)",
            f"- **Google Drive** (índice de archivos)",
            f"",
            f"## Características Principales",
            f"",
            f"- ✅ **Compatibilidad Multi-Sistema**: Esquema único para todos los backends",
            f"- ✅ **Búsqueda Avanzada**: Índices GIN y full-text search en español",
            f"- ✅ **Integridad Referencial**: Claves foráneas y constraints",
            f"- ✅ **Auditoria Completa**: Timestamps automáticos y logs del sistema",
            f"- ✅ **Flexibilidad JSON**: Campos JSONB para datos semi-estructurados",
            f"- ✅ **Optimización**: Índices especializados para consultas frecuentes",
            f""
        ]
        
        for schema_name, schema in self.schemas.items():
            doc_parts.extend([
                f"## Tabla: `{schema['table_name']}`",
                f"",
                f"**Descripción:** {schema['description']}",
                f"",
                f"### Columnas",
                f"",
                f"| Columna | Tipo | Descripción | Constraints |",
                f"|---------|------|-------------|-------------|"
            ])
            
            for col_name, col_def in schema['columns'].items():
                constraints = []
                if col_def.get('primary_key'):
                    constraints.append('PK')
                if col_def.get('not_null'):
                    constraints.append('NOT NULL')
                if col_def.get('unique'):
                    constraints.append('UNIQUE')
                if col_def.get('index'):
                    constraints.append('INDEX')
                
                constraint_str = ', '.join(constraints) if constraints else '-'
                description = col_def.get('description', '').replace('|', '\\|')
                
                doc_parts.append(f"| `{col_name}` | {col_def['type']} | {description} | {constraint_str} |")
            
            # Índices
            if 'indexes' in schema:
                doc_parts.extend([
                    f"",
                    f"### Índices",
                    f""
                ])
                for index in schema['indexes']:
                    if 'expression' in index:
                        doc_parts.append(f"- **{index['name']}**: Índice funcional sobre `{index['expression']}`")
                    else:
                        columns = ', '.join([f"`{col}`" for col in index['columns']])
                        unique_str = " (UNIQUE)" if index.get('unique') else ""
                        doc_parts.append(f"- **{index['name']}**: {columns}{unique_str}")
            
            doc_parts.append("")
        
        return "\n".join(doc_parts)

def main():
    """Función principal para generar esquema"""
    try:
        print("CWS COTIZADOR - GENERADOR DE ESQUEMA UNIFICADO")
        print("=" * 60)
        print()
        
        # Crear gestor de esquema
        schema_manager = UnifiedSchemaManager()
        
        # Generar archivos
        print("Generando archivos de esquema...")
        files_created = schema_manager.save_schema_files()
        
        print("Esquema generado exitosamente")
        print("Archivos creados en: schema_output/")
        
        for file_type, file_path in files_created.items():
            file_name = Path(file_path).name
            print(f"   {file_type.upper()}: {file_name}")
        
        print()
        print("PROXIMOS PASOS:")
        print("   1. Revisar: schema_output/unified_schema.sql")
        print("   2. Aplicar en Supabase: Ejecutar SQL en el Dashboard")
        print("   3. Validar: Usar json_schemas.json para validacion de datos")
        print("   4. Documentar: Compartir schema_documentation.md con el equipo")
        
    except Exception as e:
        print(f"ERROR generando esquema: {e}")
        raise

if __name__ == "__main__":
    main()