"""
Utilidades para exportación segura de HTML/PDF.

Este módulo proporciona funciones para generar HTML de forma segura,
previniendo XSS y otros problemas de seguridad al exportar datos.
"""

import html
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, date


class SafeHTMLBuilder:
    """
    Constructor de HTML seguro con escape automático de datos de usuario.
    """
    
    @staticmethod
    def escape(text: Any) -> str:
        """
        Escapa caracteres especiales HTML de forma segura.
        
        Args:
            text: Texto a escapar (cualquier tipo)
        
        Returns:
            Texto escapado como string
        """
        if text is None:
            return ""
        
        # Convertir a string si no lo es
        text_str = str(text)
        
        # Escapar caracteres HTML especiales
        return html.escape(text_str, quote=True)
    
    @staticmethod
    def format_currency(amount: Decimal, currency: str = "HNL") -> str:
        """
        Formatea cantidad monetaria de forma segura.
        
        Args:
            amount: Cantidad a formatear
            currency: Código de moneda
        
        Returns:
            Cantidad formateada y escapada
        """
        if amount is None:
            return SafeHTMLBuilder.escape("0.00")
        
        try:
            formatted = f"{float(amount):,.2f}"
            return f"{SafeHTMLBuilder.escape(currency)} {formatted}"
        except (ValueError, TypeError):
            return SafeHTMLBuilder.escape(f"{currency} 0.00")
    
    @staticmethod
    def format_date(date_value: Optional[datetime | date]) -> str:
        """
        Formatea fecha de forma segura.
        
        Args:
            date_value: Fecha a formatear
        
        Returns:
            Fecha formateada y escapada
        """
        if date_value is None:
            return ""
        
        try:
            if isinstance(date_value, datetime):
                return date_value.strftime("%d/%m/%Y %H:%M")
            else:
                return date_value.strftime("%d/%m/%Y")
        except (ValueError, AttributeError):
            return SafeHTMLBuilder.escape(str(date_value))
    
    @staticmethod
    def build_table(
        headers: List[str],
        rows: List[List[Any]],
        table_class: str = "table"
    ) -> str:
        """
        Construye tabla HTML segura.
        
        Args:
            headers: Lista de encabezados
            rows: Lista de filas (cada fila es lista de valores)
            table_class: Clase CSS para la tabla
        
        Returns:
            HTML de tabla con datos escapados
        """
        html_parts = [f'<table class="{SafeHTMLBuilder.escape(table_class)}">']
        
        # Encabezados
        html_parts.append("<thead><tr>")
        for header in headers:
            html_parts.append(f"<th>{SafeHTMLBuilder.escape(header)}</th>")
        html_parts.append("</tr></thead>")
        
        # Filas
        html_parts.append("<tbody>")
        for row in rows:
            html_parts.append("<tr>")
            for cell in row:
                html_parts.append(f"<td>{SafeHTMLBuilder.escape(cell)}</td>")
            html_parts.append("</tr>")
        html_parts.append("</tbody>")
        
        html_parts.append("</table>")
        return "".join(html_parts)
    
    @staticmethod
    def build_order_html(order_data: Dict[str, Any]) -> str:
        """
        Construye HTML seguro para una orden (para PDF/impresión).
        
        Args:
            order_data: Datos de la orden
        
        Returns:
            HTML completo con datos escapados
        """
        # Escapar todos los datos
        order_id = SafeHTMLBuilder.escape(order_data.get("id", "N/A"))
        customer_name = SafeHTMLBuilder.escape(order_data.get("customer_name", ""))
        customer_phone = SafeHTMLBuilder.escape(order_data.get("customer_phone", ""))
        created_at = SafeHTMLBuilder.format_date(order_data.get("created_at"))
        
        # Construir HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Orden #{order_id}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    color: #333;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #333;
                    padding-bottom: 10px;
                }}
                .section {{
                    margin-bottom: 20px;
                }}
                .section-title {{
                    font-weight: bold;
                    font-size: 1.2em;
                    margin-bottom: 10px;
                    color: #1a5490;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                th, td {{
                    padding: 8px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                .total-row {{
                    font-weight: bold;
                    font-size: 1.1em;
                    background-color: #f9f9f9;
                }}
                .footer {{
                    margin-top: 40px;
                    text-align: center;
                    font-size: 0.9em;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Orden de Venta #{order_id}</h1>
                <p>Fecha: {created_at}</p>
            </div>
            
            <div class="section">
                <div class="section-title">Información del Cliente</div>
                <p><strong>Nombre:</strong> {customer_name}</p>
                <p><strong>Teléfono:</strong> {customer_phone}</p>
            </div>
            
            <div class="section">
                <div class="section-title">Productos</div>
        """
        
        # Tabla de items
        if "items" in order_data and order_data["items"]:
            items_rows = []
            for item in order_data["items"]:
                product_name = SafeHTMLBuilder.escape(item.get("product", {}).get("nombre", ""))
                quantity = SafeHTMLBuilder.escape(item.get("cantidad", 0))
                price = SafeHTMLBuilder.format_currency(
                    item.get("precio_unitario", 0),
                    order_data.get("moneda", "HNL")
                )
                subtotal = SafeHTMLBuilder.format_currency(
                    item.get("precio_unitario", 0) * item.get("cantidad", 0),
                    order_data.get("moneda", "HNL")
                )
                
                items_rows.append([product_name, quantity, price, subtotal])
            
            html_content += SafeHTMLBuilder.build_table(
                headers=["Producto", "Cantidad", "Precio Unitario", "Subtotal"],
                rows=items_rows
            )
        
        # Total
        total = SafeHTMLBuilder.format_currency(
            order_data.get("total", 0),
            order_data.get("moneda", "HNL")
        )
        
        html_content += f"""
            </div>
            
            <div class="section">
                <table>
                    <tr class="total-row">
                        <td colspan="3" style="text-align: right;">TOTAL:</td>
                        <td>{total}</td>
                    </tr>
                </table>
            </div>
            
            <div class="footer">
                <p>Gracias por su compra</p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    @staticmethod
    def build_report_html(
        title: str,
        data: List[Dict[str, Any]],
        columns: List[tuple[str, str]]  # [(key, display_name), ...]
    ) -> str:
        """
        Construye HTML seguro para un reporte genérico.
        
        Args:
            title: Título del reporte
            data: Lista de diccionarios con datos
            columns: Lista de tuplas (key, nombre_mostrar)
        
        Returns:
            HTML completo con datos escapados
        """
        escaped_title = SafeHTMLBuilder.escape(title)
        current_date = SafeHTMLBuilder.format_date(datetime.now())
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{escaped_title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    color: #333;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #333;
                    padding-bottom: 10px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    padding: 10px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{escaped_title}</h1>
                <p>Generado: {current_date}</p>
            </div>
        """
        
        # Construir filas de datos
        headers = [display_name for _, display_name in columns]
        rows = []
        
        for item in data:
            row = []
            for key, _ in columns:
                value = item.get(key, "")
                row.append(value)
            rows.append(row)
        
        html_content += SafeHTMLBuilder.build_table(headers, rows)
        html_content += """
        </body>
        </html>
        """
        
        return html_content


def sanitize_for_csv(value: Any) -> str:
    """
    Sanitiza valor para exportación CSV segura.
    
    Previene inyección de fórmulas en Excel (Formula Injection).
    
    Args:
        value: Valor a sanitizar
    
    Returns:
        Valor sanitizado como string
    """
    if value is None:
        return ""
    
    value_str = str(value).strip()
    
    # Prevenir inyección de fórmulas (=, +, -, @)
    if value_str and value_str[0] in ('=', '+', '-', '@'):
        # Escapar con comilla simple
        value_str = "'" + value_str
    
    # Escapar comillas dobles
    value_str = value_str.replace('"', '""')
    
    return value_str


def generate_safe_filename(base_name: str, extension: str = "pdf") -> str:
    """
    Genera nombre de archivo seguro.
    
    Args:
        base_name: Nombre base del archivo
        extension: Extensión (sin punto)
    
    Returns:
        Nombre de archivo sanitizado
    """
    import re
    from datetime import datetime
    
    # Remover caracteres no seguros
    safe_name = re.sub(r'[^\w\s-]', '', base_name)
    safe_name = re.sub(r'[\s_]+', '_', safe_name)
    safe_name = safe_name[:50]  # Limitar longitud
    
    # Agregar timestamp para unicidad
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return f"{safe_name}_{timestamp}.{extension}"
