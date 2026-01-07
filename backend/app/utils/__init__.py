"""
Módulo de utilidades del backend.

Este paquete contiene utilidades compartidas para:
- Gestión de stock (stock_manager.py)
- Validaciones de entrada (validators.py)
- Exportación HTML segura (html_export.py)
- Sistema de logging (logging_config.py)
"""

from .stock_manager import StockManager, get_stock_manager, StockValidationError
from .validators import InputValidator, ValidationError, validate_required_fields, safe_int, safe_decimal
from .html_export import SafeHTMLBuilder, sanitize_for_csv, generate_safe_filename
from .logging_config import setup_logging, get_logger, LogContext, log_critical_operation

__all__ = [
    # Stock Management
    "StockManager",
    "get_stock_manager",
    "StockValidationError",
    
    # Validations
    "InputValidator",
    "ValidationError",
    "validate_required_fields",
    "safe_int",
    "safe_decimal",
    
    # HTML Export
    "SafeHTMLBuilder",
    "sanitize_for_csv",
    "generate_safe_filename",
    
    # Logging
    "setup_logging",
    "get_logger",
    "LogContext",
    "log_critical_operation",
]
