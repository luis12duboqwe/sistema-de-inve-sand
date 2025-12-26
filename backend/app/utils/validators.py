"""
Módulo de validaciones de entrada mejoradas.

Proporciona validaciones consistentes y seguras para todos los datos de entrada,
previniendo inyecciones, desbordamientos y datos inválidos.
"""

import re
from typing import Optional, List, Any
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from fastapi import HTTPException
import html


class ValidationError(Exception):
    """Excepción personalizada para errores de validación"""
    pass


class InputValidator:
    """
    Clase centralizada para validaciones de entrada.
    """
    
    # Expresiones regulares compiladas para mejor rendimiento
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_REGEX = re.compile(r'^\+?[0-9\s\-\(\)]{7,20}$')
    SKU_REGEX = re.compile(r'^[A-Z0-9\-]{3,50}$', re.IGNORECASE)
    SLUG_REGEX = re.compile(r'^[a-z0-9\-_]{2,100}$')
    IMEI_REGEX = re.compile(r'^[0-9]{15}$')
    
    # Longitudes máximas para campos de texto
    MAX_LENGTHS = {
        'nombre': 200,
        'descripcion': 2000,
        'sku': 50,
        'marca': 100,
        'modelo': 100,
        'color': 50,
        'capacidad': 50,
        'notas': 1000,
        'customer_name': 200,
        'customer_phone': 20,
        'customer_email': 254,  # RFC 5321
        'address': 500,
        'slug': 100
    }
    
    @staticmethod
    def validate_email(email: str, required: bool = True) -> Optional[str]:
        """
        Valida formato de email.
        
        Args:
            email: Email a validar
            required: Si el campo es obligatorio
        
        Returns:
            Email validado (lowercase) o None si es opcional y vacío
        
        Raises:
            ValidationError: Si el formato es inválido
        """
        if not email or not email.strip():
            if required:
                raise ValidationError("El email es obligatorio")
            return None
        
        email = email.strip().lower()
        
        if len(email) > InputValidator.MAX_LENGTHS['customer_email']:
            raise ValidationError(
                f"El email no puede exceder {InputValidator.MAX_LENGTHS['customer_email']} caracteres"
            )
        
        if not InputValidator.EMAIL_REGEX.match(email):
            raise ValidationError("Formato de email inválido")
        
        return email
    
    @staticmethod
    def validate_phone(phone: str, required: bool = True) -> Optional[str]:
        """
        Valida formato de teléfono.
        
        Args:
            phone: Teléfono a validar
            required: Si el campo es obligatorio
        
        Returns:
            Teléfono validado o None si es opcional y vacío
        
        Raises:
            ValidationError: Si el formato es inválido
        """
        if not phone or not phone.strip():
            if required:
                raise ValidationError("El teléfono es obligatorio")
            return None
        
        phone = phone.strip()
        
        if len(phone) > InputValidator.MAX_LENGTHS['customer_phone']:
            raise ValidationError(
                f"El teléfono no puede exceder {InputValidator.MAX_LENGTHS['customer_phone']} caracteres"
            )
        
        if not InputValidator.PHONE_REGEX.match(phone):
            raise ValidationError(
                "Formato de teléfono inválido. Debe contener solo dígitos, espacios y los caracteres: + - ( )"
            )
        
        return phone
    
    @staticmethod
    def validate_text_field(
        value: str,
        field_name: str,
        required: bool = True,
        min_length: int = 1,
        max_length: Optional[int] = None,
        allow_special_chars: bool = True
    ) -> Optional[str]:
        """
        Valida campo de texto genérico.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo (para mensajes de error)
            required: Si el campo es obligatorio
            min_length: Longitud mínima
            max_length: Longitud máxima (None = usar valor de MAX_LENGTHS)
            allow_special_chars: Permitir caracteres especiales
        
        Returns:
            Valor validado y limpio
        
        Raises:
            ValidationError: Si la validación falla
        """
        if not value or not value.strip():
            if required:
                raise ValidationError(f"El campo '{field_name}' es obligatorio")
            return None
        
        value = value.strip()
        
        # Aplicar longitud máxima
        if max_length is None:
            max_length = InputValidator.MAX_LENGTHS.get(field_name, 500)
        
        if len(value) > max_length:
            raise ValidationError(
                f"El campo '{field_name}' no puede exceder {max_length} caracteres (actual: {len(value)})"
            )
        
        if len(value) < min_length:
            raise ValidationError(
                f"El campo '{field_name}' debe tener al menos {min_length} caracteres"
            )
        
        # Validar caracteres si no se permiten especiales
        if not allow_special_chars:
            if not re.match(r'^[a-zA-Z0-9\s\-_.]+$', value):
                raise ValidationError(
                    f"El campo '{field_name}' contiene caracteres no permitidos. "
                    f"Solo se permiten letras, números, espacios y los caracteres: - _ ."
                )
        
        return value
    
    @staticmethod
    def validate_sku(sku: str) -> str:
        """
        Valida formato de SKU.
        
        Args:
            sku: SKU a validar
        
        Returns:
            SKU validado (uppercase)
        
        Raises:
            ValidationError: Si el formato es inválido
        """
        if not sku or not sku.strip():
            raise ValidationError("El SKU es obligatorio")
        
        sku = sku.strip().upper()
        
        if not InputValidator.SKU_REGEX.match(sku):
            raise ValidationError(
                "Formato de SKU inválido. Debe contener entre 3 y 50 caracteres alfanuméricos y guiones"
            )
        
        return sku
    
    @staticmethod
    def validate_slug(slug: str) -> str:
        """
        Valida formato de slug (para URLs amigables).
        
        Args:
            slug: Slug a validar
        
        Returns:
            Slug validado (lowercase)
        
        Raises:
            ValidationError: Si el formato es inválido
        """
        if not slug or not slug.strip():
            raise ValidationError("El slug es obligatorio")
        
        slug = slug.strip().lower()
        
        if not InputValidator.SLUG_REGEX.match(slug):
            raise ValidationError(
                "Formato de slug inválido. Debe contener solo letras minúsculas, números, guiones y guiones bajos"
            )
        
        return slug
    
    @staticmethod
    def validate_imei(imei: str) -> str:
        """
        Valida formato de IMEI (15 dígitos).
        
        Args:
            imei: IMEI a validar
        
        Returns:
            IMEI validado
        
        Raises:
            ValidationError: Si el formato es inválido
        """
        if not imei or not imei.strip():
            raise ValidationError("El IMEI es obligatorio")
        
        imei = imei.strip()
        
        if not InputValidator.IMEI_REGEX.match(imei):
            raise ValidationError("Formato de IMEI inválido. Debe contener exactamente 15 dígitos")
        
        # Opcional: Validar con algoritmo de Luhn (implementado en check_luhn.py)
        # if not validate_luhn(imei):
        #     raise ValidationError("El IMEI no pasa la validación de Luhn (checksum inválido)")
        
        return imei
    
    @staticmethod
    def validate_positive_number(
        value: Any,
        field_name: str,
        allow_zero: bool = False,
        max_value: Optional[float] = None
    ) -> Decimal:
        """
        Valida número positivo (para precios, cantidades, etc.).
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            allow_zero: Permitir valor 0
            max_value: Valor máximo permitido
        
        Returns:
            Valor como Decimal
        
        Raises:
            ValidationError: Si la validación falla
        """
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError(f"El campo '{field_name}' debe ser un número válido")
        
        if decimal_value < 0:
            raise ValidationError(f"El campo '{field_name}' no puede ser negativo")
        
        if not allow_zero and decimal_value == 0:
            raise ValidationError(f"El campo '{field_name}' debe ser mayor que 0")
        
        if max_value is not None and decimal_value > Decimal(str(max_value)):
            raise ValidationError(
                f"El campo '{field_name}' no puede exceder {max_value} (actual: {decimal_value})"
            )
        
        return decimal_value
    
    @staticmethod
    def validate_positive_integer(
        value: Any,
        field_name: str,
        allow_zero: bool = False,
        max_value: Optional[int] = None
    ) -> int:
        """
        Valida entero positivo.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            allow_zero: Permitir valor 0
            max_value: Valor máximo permitido
        
        Returns:
            Valor como int
        
        Raises:
            ValidationError: Si la validación falla
        """
        try:
            int_value = int(value)
        except (TypeError, ValueError):
            raise ValidationError(f"El campo '{field_name}' debe ser un número entero válido")
        
        if int_value < 0:
            raise ValidationError(f"El campo '{field_name}' no puede ser negativo")
        
        if not allow_zero and int_value == 0:
            raise ValidationError(f"El campo '{field_name}' debe ser mayor que 0")
        
        if max_value is not None and int_value > max_value:
            raise ValidationError(
                f"El campo '{field_name}' no puede exceder {max_value} (actual: {int_value})"
            )
        
        return int_value
    
    @staticmethod
    def validate_date_range(
        date_from: Optional[date],
        date_to: Optional[date],
        allow_future: bool = True
    ) -> tuple[Optional[date], Optional[date]]:
        """
        Valida rango de fechas.
        
        Args:
            date_from: Fecha desde
            date_to: Fecha hasta
            allow_future: Permitir fechas futuras
        
        Returns:
            Tupla (date_from, date_to) validada
        
        Raises:
            ValidationError: Si la validación falla
        """
        today = date.today()
        
        if date_from and not allow_future and date_from > today:
            raise ValidationError("La fecha 'desde' no puede ser futura")
        
        if date_to and not allow_future and date_to > today:
            raise ValidationError("La fecha 'hasta' no puede ser futura")
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError("La fecha 'desde' no puede ser posterior a la fecha 'hasta'")
        
        return date_from, date_to
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Sanitiza texto para prevenir XSS en contextos HTML.
        
        Args:
            text: Texto a sanitizar
        
        Returns:
            Texto con caracteres HTML escapados
        """
        if not text:
            return text
        
        return html.escape(text, quote=True)
    
    @staticmethod
    def validate_list_not_empty(items: List[Any], field_name: str) -> List[Any]:
        """
        Valida que una lista no esté vacía.
        
        Args:
            items: Lista a validar
            field_name: Nombre del campo
        
        Returns:
            Lista validada
        
        Raises:
            ValidationError: Si la lista está vacía
        """
        if not items or len(items) == 0:
            raise ValidationError(f"El campo '{field_name}' debe contener al menos un elemento")
        
        return items


# Funciones helper para uso rápido en routers
def validate_required_fields(data: dict, required_fields: List[str]):
    """
    Valida que campos requeridos estén presentes y no vacíos.
    
    Args:
        data: Diccionario con datos
        required_fields: Lista de nombres de campos requeridos
    
    Raises:
        HTTPException: Si algún campo falta o está vacío
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
            missing_fields.append(field)
    
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Campos requeridos faltantes o vacíos: {', '.join(missing_fields)}"
        )


def safe_int(value: Any, default: int = 0, field_name: str = "campo") -> int:
    """
    Convierte valor a entero de forma segura.
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si la conversión falla
        field_name: Nombre del campo (para error)
    
    Returns:
        Entero convertido
    
    Raises:
        HTTPException: Si el valor no es convertible y no hay default
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        if default is None:
            raise HTTPException(
                status_code=400,
                detail=f"El campo '{field_name}' debe ser un número entero válido"
            )
        return default


def safe_decimal(value: Any, default: Optional[Decimal] = None, field_name: str = "campo") -> Decimal:
    """
    Convierte valor a Decimal de forma segura.
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si la conversión falla
        field_name: Nombre del campo (para error)
    
    Returns:
        Decimal convertido
    
    Raises:
        HTTPException: Si el valor no es convertible y no hay default
    """
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        if default is None:
            raise HTTPException(
                status_code=400,
                detail=f"El campo '{field_name}' debe ser un número decimal válido"
            )
        return default
