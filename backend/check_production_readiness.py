#!/usr/bin/env python3
"""
Script de verificación de preparación para producción.

Este script verifica que el sistema esté correctamente configurado
y listo para ser desplegado en un entorno de producción.

Uso:
    python check_production_readiness.py
"""

import sys
import os
from pathlib import Path

# Agregar path del backend al sys.path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.config import settings
from app.config_production import prod_settings, check_production_readiness
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError
import logging

# Colores para output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Imprime encabezado resaltado"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")

def print_success(text: str):
    """Imprime mensaje de éxito"""
    print(f"  {Colors.GREEN}✓{Colors.RESET} {text}")

def print_warning(text: str):
    """Imprime advertencia"""
    print(f"  {Colors.YELLOW}⚠{Colors.RESET} {text}")

def print_error(text: str):
    """Imprime error"""
    print(f"  {Colors.RED}✗{Colors.RESET} {text}")

def print_info(text: str):
    """Imprime información"""
    print(f"  {Colors.BLUE}ℹ{Colors.RESET} {text}")


def check_environment():
    """Verifica variables de entorno críticas"""
    print_header("VERIFICACIÓN DE ENTORNO")
    
    issues = []
    
    # Verificar que existe .env o variables de entorno
    env_file = Path(backend_path) / ".env"
    if env_file.exists():
        print_success(f"Archivo .env encontrado: {env_file}")
    else:
        print_warning("Archivo .env no encontrado (puede usar variables de entorno del sistema)")
    
    # Verificar entorno (fuente de verdad: settings.environment)
    environment = (settings.environment or os.getenv("ENVIRONMENT", "development")).lower()
    print_info(f"Entorno: {environment}")
    
    if environment == "production":
        print_success("Modo producción detectado")
    else:
        print_warning(f"Entorno actual: {environment} (no es producción)")
    
    # Verificar DEBUG
    if settings.debug:
        if environment == "production":
            print_error("DEBUG=True - DEBE estar en False para producción")
            issues.append("DEBUG habilitado en producción")
        else:
            print_warning("DEBUG=True (solo recomendado en desarrollo)")
    else:
        print_success("DEBUG deshabilitado")
    
    return issues


def check_database():
    """Verifica configuración y conexión a base de datos"""
    print_header("VERIFICACIÓN DE BASE DE DATOS")
    
    issues = []
    
    # Mostrar URL de BD (ofuscando contraseña)
    db_url = settings.database_url
    if "@" in db_url and "://" in db_url:
        # Ofuscar contraseña
        parts = db_url.split("://")
        if len(parts) == 2:
            scheme = parts[0]
            rest = parts[1]
            if "@" in rest:
                credentials, host_db = rest.split("@", 1)
                if ":" in credentials:
                    user, _ = credentials.split(":", 1)
                    display_url = f"{scheme}://{user}:****@{host_db}"
                else:
                    display_url = f"{scheme}://{credentials}@{host_db}"
            else:
                display_url = db_url
        else:
            display_url = db_url
    else:
        display_url = db_url
    
    print_info(f"URL: {display_url}")
    
    environment = (settings.environment or os.getenv("ENVIRONMENT", "development")).lower()

    # Verificar tipo de base de datos
    if "sqlite" in db_url.lower():
        if environment == "production":
            print_error("SQLite detectado - NO recomendado para producción")
            print_info("  → Migrar a PostgreSQL o MySQL")
            issues.append("SQLite en producción")
        else:
            print_warning("SQLite detectado (ok para desarrollo, no recomendado en producción)")
    elif "postgresql" in db_url.lower():
        print_success("PostgreSQL detectado - Recomendado para producción")
    elif "mysql" in db_url.lower():
        print_success("MySQL detectado - Aceptable para producción")
    else:
        print_warning(f"Base de datos no reconocida: {db_url.split(':')[0]}")
    
    # Intentar conexión
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            print_success("Conexión a base de datos exitosa")
            
            # Verificar tablas principales
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            required_tables = [
                "users", "roles", "permissions",
                "products", "locations", "stock",
                "orders", "order_items", "sales_profiles"
            ]
            
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                print_error(f"Tablas faltantes: {', '.join(missing_tables)}")
                print_info("  → Ejecutar: python init_db.py --with-data")
                issues.append("Tablas faltantes en base de datos")
            else:
                print_success(f"Todas las tablas requeridas existen ({len(tables)} tablas totales)")
        
    except OperationalError as e:
        print_error(f"Error de conexión a base de datos: {e}")
        issues.append("No se puede conectar a la base de datos")
    except Exception as e:
        print_error(f"Error inesperado al verificar BD: {e}")
        issues.append("Error al verificar base de datos")
    
    return issues


def check_security():
    """Verifica configuración de seguridad"""
    print_header("VERIFICACIÓN DE SEGURIDAD")
    
    issues = []
    
    environment = (settings.environment or os.getenv("ENVIRONMENT", "development")).lower()

    # SECRET_KEY
    if not settings.secret_key or len(settings.secret_key) < 32:
        print_error("SECRET_KEY muy corta o vacía (mínimo 32 caracteres)")
        issues.append("SECRET_KEY insegura")
    elif "your-secret-key" in settings.secret_key:
        if environment == "production":
            print_error("SECRET_KEY usando valor por defecto - CAMBIAR URGENTEMENTE")
            issues.append("SECRET_KEY por defecto")
        else:
            print_warning("SECRET_KEY parece ser el valor por defecto (cambiar antes de producción)")
    else:
        print_success(f"SECRET_KEY configurada ({len(settings.secret_key)} caracteres)")
    
    # CORS
    if "*" in settings.cors_origins:
        if environment == "production":
            print_error("CORS permite todos los orígenes (*) - RIESGO DE SEGURIDAD")
            print_info("  → Restringir a dominios específicos en producción")
            issues.append("CORS abierto")
        else:
            print_warning("CORS permite todos los orígenes (*) (restringir en producción)")
    else:
        print_success(f"CORS restringido a: {', '.join(settings.cors_origins)}")

    # Allowed hosts
    if not settings.allowed_hosts or "*" in settings.allowed_hosts:
        if environment == "production":
            print_error("ALLOWED_HOSTS permite cualquier host - Configurar dominios explícitos")
            print_info("  → Alinear con configuración del reverse proxy (Nginx/Apache)")
            issues.append("ALLOWED_HOSTS abierto")
        else:
            print_warning("ALLOWED_HOSTS está abierto (configurar antes de producción)")
    else:
        print_success(f"ALLOWED_HOSTS: {', '.join(settings.allowed_hosts)}")
    
    # JWT
    print_info(f"JWT Algorithm: {settings.algorithm}")
    print_info(f"Token expiration: {settings.access_token_expire_minutes} minutos")
    
    if settings.access_token_expire_minutes > 1440:  # > 24 horas
        print_warning("Tokens JWT expiran en más de 24 horas")
        issues.append("Expiración de tokens muy larga")
    else:
        print_success("Expiración de tokens adecuada")
    
    return issues


def check_features():
    """Verifica estado de funcionalidades"""
    print_header("VERIFICACIÓN DE FUNCIONALIDADES")
    
    issues = []
    
    # Logging
    if prod_settings.ENABLE_FILE_LOGGING:
        print_success("Logging a archivos habilitado")
        print_info(f"  → Directorio: {prod_settings.LOG_DIR}")
        
        log_dir = Path(prod_settings.LOG_DIR)
        if not log_dir.exists():
            print_warning(f"Directorio de logs no existe: {log_dir}")
            print_info("  → Se creará automáticamente al iniciar")
    else:
        print_warning("Logging a archivos deshabilitado")
        issues.append("Logging deshabilitado")
    
    # Backups
    if prod_settings.ENABLE_AUTO_BACKUP:
        print_success("Backups automáticos habilitados")
        print_info(f"  → Directorio: {prod_settings.BACKUP_DIR}")
        print_info(f"  → Retención: {prod_settings.BACKUP_RETENTION_DAYS} días")
    else:
        print_warning("Backups automáticos deshabilitados")
        print_info("  → Altamente recomendado habilitar backups")
        issues.append("Backups deshabilitados")
    
    # Email
    if prod_settings.SMTP_HOST and prod_settings.SMTP_USER:
        print_success("Email configurado")
        print_info(f"  → SMTP: {prod_settings.SMTP_HOST}:{prod_settings.SMTP_PORT}")
    else:
        print_warning("Email no configurado")
        print_info("  → Requerido para notificaciones y recuperación de contraseñas")
    
    # OpenAI
    if prod_settings.ENABLE_AI_FEATURES:
        if prod_settings.OPENAI_API_KEY:
            print_success("IA habilitada con OpenAI configurado")
            print_info(f"  → Modelo: {prod_settings.OPENAI_MODEL}")
        else:
            print_error("IA habilitada pero OPENAI_API_KEY no configurada")
            issues.append("OpenAI no configurado")
    else:
        print_info("Funcionalidades de IA deshabilitadas")
    
    # WhatsApp (N8N)
    if prod_settings.N8N_WEBHOOK_URL:
        print_success("Integración N8N/WhatsApp configurada")
    else:
        print_info("Integración N8N/WhatsApp no configurada")
    
    # Feature flags
    print_info(f"Trade-In: {'Habilitado' if prod_settings.ENABLE_TRADE_IN else 'Deshabilitado'}")
    print_info(f"Financiamiento: {'Habilitado' if prod_settings.ENABLE_FINANCING else 'Deshabilitado'}")
    print_info(f"Tracking IMEI: {'Habilitado' if prod_settings.ENABLE_IMEI_TRACKING else 'Deshabilitado'}")
    
    return issues


def check_dependencies():
    """Verifica dependencias instaladas"""
    print_header("VERIFICACIÓN DE DEPENDENCIAS")
    
    issues = []
    requirements_file = Path(backend_path) / "requirements.txt"
    
    if not requirements_file.exists():
        print_error("requirements.txt no encontrado")
        return ["requirements.txt faltante"]
    
    try:
        from importlib import metadata

        def _version(dist_name: str) -> str:
            try:
                return metadata.version(dist_name)
            except metadata.PackageNotFoundError:
                return "(no instalado)"

        deps = {
            "fastapi": "FastAPI",
            "sqlalchemy": "SQLAlchemy",
            "pydantic": "Pydantic",
            "python-jose": "python-jose",
            "passlib": "passlib",
        }

        print_success("Dependencias principales (según el entorno Python actual):")
        for dist_name, label in deps.items():
            ver = _version(dist_name)
            if ver == "(no instalado)":
                print_error(f"  → {label}: {ver}")
            else:
                print_info(f"  → {label}: {ver}")

        if any(_version(k) == "(no instalado)" for k in deps.keys()):
            print_warning("Faltan dependencias en este entorno")
            print_info("  → Ejecutar: pip install -r requirements.txt")
            issues.append("Dependencias faltantes")
    except Exception as e:
        print_error(f"No se pudieron verificar dependencias: {e}")
        print_info("  → Ejecutar: pip install -r requirements.txt")
        issues.append("Verificación de dependencias fallida")
    
    return issues


def generate_report(all_issues):
    """Genera reporte final"""
    print_header("REPORTE FINAL")
    
    if not all_issues:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ SISTEMA LISTO PARA PRODUCCIÓN{Colors.RESET}\n")
        print("  No se encontraron problemas críticos.")
        print("  El sistema puede ser desplegado de forma segura.")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ SISTEMA REQUIERE ATENCIÓN{Colors.RESET}\n")
        print("  Se encontraron los siguientes problemas:\n")
        
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
        
        print(f"\n{Colors.YELLOW}Recomendación:{Colors.RESET}")
        print("  → Revisar y corregir los problemas antes de desplegar a producción")
        print("  → Consultar documentación: docs/DEPLOYMENT.md")
        print("  → Ver configuración: backend/.env.production.example")
        
        return 1


def main():
    """Función principal"""
    print(f"\n{Colors.BOLD}VERIFICACIÓN DE PREPARACIÓN PARA PRODUCCIÓN{Colors.RESET}")
    print(f"{Colors.BOLD}Sistema de Inventario Multi-Ubicación v2.0{Colors.RESET}")
    
    all_issues = []
    
    # Ejecutar verificaciones
    all_issues.extend(check_environment())
    all_issues.extend(check_database())
    all_issues.extend(check_security())
    all_issues.extend(check_features())
    all_issues.extend(check_dependencies())
    
    # Generar reporte
    exit_code = generate_report(all_issues)
    
    # Información adicional
    if exit_code == 0:
        print(f"\n{Colors.BOLD}Siguientes pasos:{Colors.RESET}")
        print("  1. Configurar servidor web (Nginx/Apache)")
        print("  2. Configurar SSL/TLS con Let's Encrypt")
        print("  3. Configurar systemd service para auto-inicio")
        print("  4. Configurar backups automáticos de BD")
        print("  5. Configurar monitoreo (opcional: Sentry, New Relic)")
        print(f"\n  Ver guía completa: {Colors.BLUE}docs/DEPLOYMENT.md{Colors.RESET}\n")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
