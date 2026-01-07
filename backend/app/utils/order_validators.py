from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Location, Profile, SalesProfile, Product


def resolve_sales_profile(
    db: Session,
    sales_profile_slug: Optional[str],
    profile_slug: Optional[str]
) -> Tuple[Optional[SalesProfile], Optional[Profile], Optional[int], Optional[int]]:
    """Resolve sales_profile (V2) or legacy profile and return objects and IDs.

    Raises:
        HTTPException: if required slugs are missing or not found.
    """
    sales_profile_id_for_order: Optional[int] = None
    profile_id_for_order: Optional[int] = None
    sales_profile: Optional[SalesProfile] = None
    profile: Optional[Profile] = None

    if sales_profile_slug:
        sales_profile = db.query(SalesProfile).filter(
            SalesProfile.slug == sales_profile_slug,
            SalesProfile.active == True
        ).first()
        if not sales_profile:
            raise HTTPException(
                status_code=404,
                detail=f"El perfil de venta con slug '{sales_profile_slug}' no fue encontrado o está inactivo"
            )
        sales_profile_id_for_order = sales_profile.id
    elif profile_slug:
        profile = db.query(Profile).filter(Profile.slug == profile_slug).first()
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"El perfil con slug '{profile_slug}' no fue encontrado"
            )
        profile_id_for_order = profile.id
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "Debe especificar un canal de venta. "
                "Use 'sales_profile_slug' para V2.0 (ejemplo: 'bot-whatsapp') "
                "o 'profile_slug' para modo legacy."
            )
        )

    return sales_profile, profile, sales_profile_id_for_order, profile_id_for_order


def validate_location_and_phone(db: Session, source_location_id: Optional[int], customer_phone: Optional[str]) -> Tuple[Location, str]:
    """Validate source location and customer phone; returns location and normalized phone."""
    source_location = validate_location_exists(db, source_location_id)
    phone = normalize_customer_phone(customer_phone)
    return source_location, phone


def validate_location_exists(db: Session, location_id: Optional[int]) -> Location:
    """Valida que la ubicación exista y esté activa."""
    if not location_id or location_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="source_location_id es obligatorio en V2.0 y debe ser un ID válido (mayor a 0)"
        )

    source_location = db.query(Location).filter(
        Location.id == location_id,
        Location.activo == True
    ).first()
    if not source_location:
        raise HTTPException(
            status_code=404,
            detail=f"Ubicación con ID {location_id} no encontrada o inactiva"
        )
    return source_location


def normalize_customer_phone(customer_phone: Optional[str]) -> str:
    """Normaliza y valida teléfono de cliente."""
    phone = str(customer_phone or "").strip()
    if not phone:
        raise HTTPException(
            status_code=400,
            detail="El número de teléfono del cliente es requerido"
        )
    return phone


def validate_product_exists(db: Session, product_id: Optional[int]) -> Product:
    """Valida que el producto exista y esté activo."""
    if not product_id or product_id <= 0:
        raise HTTPException(status_code=400, detail="product_id debe ser un ID válido")

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.activo == True
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Producto con ID {product_id} no encontrado o inactivo"
        )

    return product
