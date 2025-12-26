"""
Sistema de logging centralizado y configurado para el backend.

Este módulo proporciona configuración de logging estructurado con:
- Diferentes niveles de log según el entorno (dev/prod)
- Rotación de archivos de log
- Formato consistente con contexto útil
- Logging de excepciones con stack traces
- Integración con sistemas de monitoreo (preparado para APM)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional
import json

from app.config import settings


class StructuredFormatter(logging.Formatter):
    """
    Formateador que produce logs en formato estructurado (JSON).
    Útil para integración con sistemas de análisis de logs.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Agregar información de excepción si existe
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Agregar campos personalizados si existen
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """
    Formateador con colores para mejor legibilidad en consola durante desarrollo.
    """
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Formato: [TIMESTAMP] LEVEL - logger.module - message
        log_message = (
            f"{color}[{self.formatTime(record)}] {record.levelname:8}{reset} - "
            f"{record.name}.{record.module} - {record.getMessage()}"
        )
        
        # Agregar excepción si existe
        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"
        
        return log_message


def setup_logging(
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    structured: bool = False
):
    """
    Configura el sistema de logging para toda la aplicación.
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directorio para archivos de log (default: ./logs)
        enable_file_logging: Habilitar logging a archivos
        enable_console_logging: Habilitar logging a consola
        structured: Usar formato estructurado (JSON) en archivos
    """
    
    # Determinar nivel de logging
    if log_level is None:
        log_level = "DEBUG" if settings.debug else "INFO"
    
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Limpiar handlers existentes
    root_logger.handlers.clear()
    
    # === CONSOLE HANDLER ===
    if enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        if structured:
            console_formatter = StructuredFormatter()
        else:
            console_formatter = ColoredConsoleFormatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # === FILE HANDLERS ===
    if enable_file_logging:
        if log_dir is None:
            log_dir = "./logs"
        
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Handler para logs generales (con rotación por tamaño)
        general_log_file = log_path / "app.log"
        file_handler = RotatingFileHandler(
            filename=general_log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        
        if structured:
            file_formatter = StructuredFormatter()
        else:
            file_formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Handler para errores (con rotación diaria)
        error_log_file = log_path / "errors.log"
        error_handler = TimedRotatingFileHandler(
            filename=error_log_file,
            when='midnight',
            interval=1,
            backupCount=30,  # Mantener 30 días
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
    
    # === LOGGERS ESPECÍFICOS ===
    
    # Silenciar logs muy verbosos de librerías externas
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # Logger específico para operaciones de stock (críticas)
    stock_logger = logging.getLogger("app.stock")
    stock_logger.setLevel(logging.DEBUG)  # Siempre en DEBUG para trazabilidad
    
    # Logger para autenticación y seguridad
    auth_logger = logging.getLogger("app.auth")
    auth_logger.setLevel(logging.INFO)
    
    logging.info(f"Sistema de logging configurado - Nivel: {log_level}, Archivos: {enable_file_logging}")


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado para un módulo específico.
    
    Args:
        name: Nombre del módulo (usar __name__)
    
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager para agregar contexto temporal a los logs.
    
    Uso:
        with LogContext(user_id=123, request_id="abc"):
            logger.info("Operación realizada")  # Incluirá user_id y request_id
    """
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.old_factory = None
    
    def __enter__(self):
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        self.old_factory = old_factory
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


# Función helper para logging de operaciones críticas con contexto
def log_critical_operation(
    logger: logging.Logger,
    operation: str,
    details: dict,
    user_id: Optional[int] = None,
    success: bool = True
):
    """
    Registra operaciones críticas con contexto completo.
    
    Args:
        logger: Logger a usar
        operation: Nombre de la operación
        details: Detalles de la operación (dict)
        user_id: ID del usuario que ejecuta
        success: Si la operación fue exitosa
    """
    log_data = {
        "operation": operation,
        "success": success,
        "user_id": user_id,
        **details
    }
    
    message = f"Operación crítica: {operation} - {'ÉXITO' if success else 'FALLO'}"
    
    if success:
        logger.info(message, extra=log_data)
    else:
        logger.error(message, extra=log_data)


# Decorador para logging automático de funciones
def log_function_call(logger: Optional[logging.Logger] = None):
    """
    Decorador que registra la llamada y resultado de una función.
    
    Uso:
        @log_function_call()
        def my_function(arg1, arg2):
            ...
    """
    import functools
    
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__qualname__
            logger.debug(f"Llamando {func_name} con args={args}, kwargs={kwargs}")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func_name} completada exitosamente")
                return result
            except Exception as e:
                logger.error(f"{func_name} falló con excepción: {e}", exc_info=True)
                raise
        
        return wrapper
    
    return decorator


# Inicializar logging al importar el módulo (si está en producción)
if not settings.debug:
    setup_logging(enable_console_logging=True, enable_file_logging=True)
