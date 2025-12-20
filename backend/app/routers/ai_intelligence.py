from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.database import get_db
from app.models import (
    SalesProfile, Product, Stock, FAQEntry, Order, 
    Customer, AIProfileConfig, InteractionLog, TrainingQueue, Location,
    Bank, FinancingOption, TradeInPolicy
)
from app.schemas import ProductResponse, TradeInPolicyCreate, TradeInPolicyResponse

router = APIRouter(prefix="/api/ai", tags=["AI Intelligence"])

# --- Schemas Locales (Input/Output) ---

class AIContextRequest(BaseModel):
    sales_profile_slug: str
    customer_phone: str
    message_content: str
    customer_name: Optional[str] = None

class AIContextResponse(BaseModel):
    system_prompt: str
    bot_config: Dict[str, Any]
    customer_info: Dict[str, Any]
    relevant_inventory: str  # Texto resumido para ahorrar tokens
    relevant_faqs: str       # Texto resumido
    financing_info: str      # Información de bancos y tasas
    previous_context: List[Dict[str, str]]

class InteractionLogCreate(BaseModel):
    sales_profile_slug: str
    customer_phone: str
    role: str  # user, assistant
    content: str
    tokens_used: Optional[int] = 0

class TrainingSubmission(BaseModel):
    sales_profile_slug: str
    customer_question: str
    ai_proposed_answer: Optional[str] = None

class AIConfigSchema(BaseModel):
    sales_profile_id: int
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    system_prompt: str
    initial_greeting: Optional[str] = None
    voice_tone: Optional[str] = None
    context_rules: Optional[str] = None
    is_active: bool = True
    admin_notification_phone: Optional[str] = None  # Nuevo campo

    model_config = ConfigDict(from_attributes=True)

# --- Endpoints ---

@router.get("/config/{sales_profile_id}", response_model=AIConfigSchema)
def get_ai_config(sales_profile_id: int, db: Session = Depends(get_db)):
    """Obtiene la configuración de IA para un perfil específico"""
    config = db.query(AIProfileConfig).filter(AIProfileConfig.sales_profile_id == sales_profile_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="AI Config not found")
    return config

@router.post("/config/{sales_profile_id}", response_model=AIConfigSchema)
def update_ai_config(sales_profile_id: int, config: AIConfigSchema, db: Session = Depends(get_db)):
    """Crea o actualiza la configuración de IA para un perfil"""
    # Verify profile exists
    profile = db.query(SalesProfile).filter(SalesProfile.id == sales_profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Sales Profile not found")

    db_config = db.query(AIProfileConfig).filter(AIProfileConfig.sales_profile_id == sales_profile_id).first()
    
    if not db_config:
        db_config = AIProfileConfig(sales_profile_id=sales_profile_id)
        db.add(db_config)
    
    db_config.model_name = config.model_name
    db_config.temperature = config.temperature
    db_config.system_prompt = config.system_prompt
    db_config.initial_greeting = config.initial_greeting
    db_config.voice_tone = config.voice_tone
    db_config.context_rules = config.context_rules
    db_config.is_active = config.is_active
    db_config.admin_notification_phone = config.admin_notification_phone
    
    db.commit()
    db.refresh(db_config)
    return db_config

@router.post("/context", response_model=AIContextResponse)
def get_ai_context(request: AIContextRequest, db: Session = Depends(get_db)):
    """
    El CEREBRO: Recibe un mensaje y devuelve todo lo necesario para que GPT responda.
    1. Identifica/Crea al cliente.
    2. Busca la configuración del Bot.
    3. Busca inventario y FAQs relevantes.
    """
    # 1. Validar Perfil de Venta
    profile = db.query(SalesProfile).filter(SalesProfile.slug == request.sales_profile_slug).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Sales Profile not found")
    
    # 2. Obtener Configuración de IA
    ai_config = db.query(AIProfileConfig).filter(AIProfileConfig.sales_profile_id == profile.id).first()
    
    # Prompt por defecto robusto
    default_system_prompt = """Eres un asistente de ventas experto y amable para una tienda de celulares.
    Tu objetivo es ayudar al cliente a encontrar el producto ideal y cerrar la venta.
    
    DIRECTRICES PRINCIPALES:
    1. Usa SIEMPRE la información del INVENTARIO proporcionado. No inventes productos ni precios.
    2. Si el producto no está en la lista, di que no lo tienes disponible por el momento.
    3. Para preguntas frecuentes, usa la sección de FAQs.
    4. Sé conciso y directo, usa emojis moderadamente para ser amigable.
    5. Si el cliente pregunta por financiamiento, explica las opciones disponibles claramente.
    """

    if not ai_config:
        # Configuración Default si no existe
        ai_config = AIProfileConfig(
            system_prompt=default_system_prompt,
            model_name="gpt-3.5-turbo",
            temperature=0.7
        )
    
    # 3. Gestión de Cliente (Get or Create)
    customer = db.query(Customer).filter(Customer.phone_number == request.customer_phone).first()
    if not customer:
        customer = Customer(
            phone_number=request.customer_phone,
            name=request.customer_name,
            reputation_score=100
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
    else:
        # Actualizar nombre si viene nuevo
        if request.customer_name and not customer.name:
            customer.name = request.customer_name
            db.commit()
            
    # Verificar si es Troll
    if customer.is_blocked:
        raise HTTPException(status_code=403, detail="Customer is blocked")
        
    # Si es troll pero no bloqueado, inyectar instrucción de comportamiento
    troll_instruction = ""
    if customer.is_troll:
        troll_instruction = "\n[MODO TROLL DETECTADO]: Este usuario ha sido marcado como problemático. Sé extremadamente cortante, directo y no ofrezcas descuentos ni pierdas tiempo. Responde solo lo estrictamente necesario."
    elif customer.reputation_score < 50:
        troll_instruction = "\n[ADVERTENCIA DE REPUTACIÓN]: Este cliente tiene baja reputación. Sé cauteloso, no ofrezcas créditos ni facilidades de pago excepcionales. Mantén la conversación estrictamente profesional."

    # 4. Obtener Inventario Relevante (Búsqueda Híbrida Mejorada)
    # Estrategia de Embudo: 
    # 1. Búsqueda Estricta (AND): Debe coincidir con TODAS las palabras clave (ej: "iPhone" AND "13")
    # 2. Búsqueda Relajada (OR): Si hay pocos resultados, buscar coincidencias parciales
    
    relevant_products = []
    # Filtrar palabras cortas y comunes para evitar ruido
    stop_words = {'hola', 'quiero', 'tienes', 'precio', 'cuanto', 'cuesta', 'busco', 'necesito', 'para', 'celular', 'telefono'}
    keywords = [w.lower() for w in request.message_content.split() if len(w) > 2 and w.lower() not in stop_words]
    
    if keywords:
        # 1. INTENTO ESTRICTO (AND)
        # Construir condiciones: (Nombre LIKE %k1% OR Marca LIKE %k1% OR Modelo LIKE %k1%) AND (...)
        and_conditions = []
        for k in keywords:
            term_condition = or_(
                Product.nombre.ilike(f"%{k}%"),
                Product.marca.ilike(f"%{k}%"),
                Product.modelo.ilike(f"%{k}%"),
                Product.sku.ilike(f"%{k}%")
            )
            and_conditions.append(term_condition)
            
        relevant_products = db.query(Product).options(
            joinedload(Product.stock_items).joinedload(Stock.location)
        ).filter(
            Product.activo == True,
            *and_conditions
        ).limit(10).all()
        
        # 2. INTENTO RELAJADO (OR) - Relleno si hay pocos resultados
        if len(relevant_products) < 5:
            existing_ids = [p.id for p in relevant_products]
            
            # Aplanar condiciones para un OR gigante
            or_conditions = []
            for k in keywords:
                or_conditions.append(Product.nombre.ilike(f"%{k}%"))
                or_conditions.append(Product.modelo.ilike(f"%{k}%"))
            
            more_products = db.query(Product).options(
                joinedload(Product.stock_items).joinedload(Stock.location)
            ).filter(
                Product.activo == True,
                Product.id.notin_(existing_ids),
                or_(*or_conditions)
            ).limit(10 - len(relevant_products)).all()
            
            relevant_products.extend(more_products)
            
    # B. Rellenar con Top Stock (lo más vendido/disponible) si aún faltan
    if len(relevant_products) < 10:
        # Optimización: Cargar relaciones para evitar N+1
        top_products = db.query(Product).options(
            joinedload(Product.stock_items).joinedload(Stock.location)
        ).filter(Product.activo == True).limit(20).all()
        # Ordenar por stock total (en Python porque es propiedad computada o relación)
        # Nota: Para eficiencia real, esto debería ser una query SQL con join, pero por ahora:
        top_products.sort(key=lambda p: sum(s.cantidad_disponible for s in p.stock_items), reverse=True)
        
        for p in top_products:
            if p not in relevant_products and len(relevant_products) < 15:
                relevant_products.append(p)

    inventory_text = "INVENTARIO DISPONIBLE (Ubicación: ID):\n"
    for p in relevant_products:
        stock_details = []
        total_stock_real = 0
        
        # Ordenar stock items para mostrar primero los que tienen más stock
        # (Esto se hace en memoria porque ya se cargaron con joinedload)
        sorted_stock = sorted(p.stock_items, key=lambda s: (s.cantidad_disponible - s.cantidad_reservada), reverse=True)
        
        for s in sorted_stock:
            # CÁLCULO DE STOCK REAL: Disponible - Reservado
            stock_libre = (s.cantidad_disponible or 0) - (s.cantidad_reservada or 0)
            
            if stock_libre > 0:
                # Intentar obtener nombre de ubicación de forma segura
                loc_name = s.location.nombre if s.location else f"Ubicación {s.location_id}"
                stock_details.append(f"{stock_libre} en {loc_name} (ID:{s.location_id})")
                total_stock_real += stock_libre
        
        if total_stock_real > 0:
            details_str = ", ".join(stock_details)
            color_info = f" Color: {p.color}" if p.color else ""
            # Formato de precio mejorado
            precio_fmt = f"{p.precio:,.2f}"
            inventory_text += f"- {p.nombre} ({p.capacidad or ''}){color_info}: {p.moneda} {precio_fmt} | Disp: {total_stock_real} [{details_str}]\n"
            
    # 5. Obtener FAQs Relevantes
    # Estrategia Híbrida: Palabras clave + Recientes + Populares
    relevant_faqs = []
    
    # A. Búsqueda por palabras clave (simple)
    keywords = [w.lower() for w in request.message_content.split() if len(w) > 3]
    
    if keywords:
        # Construir query OR para palabras clave
        conditions = [FAQEntry.pregunta_clave.ilike(f"%{k}%") for k in keywords]
        if conditions:
            relevant_faqs = db.query(FAQEntry).filter(
                FAQEntry.activa == True,
                or_(*conditions)
            ).limit(5).all()
            
    # B. Si no hay suficientes, rellenar con las más recientes (para que lo nuevo aparezca)
    if len(relevant_faqs) < 5:
        recent_faqs = db.query(FAQEntry).filter(FAQEntry.activa == True).order_by(FAQEntry.created_at.desc()).limit(5).all()
        for f in recent_faqs:
            if f not in relevant_faqs and len(relevant_faqs) < 5:
                relevant_faqs.append(f)
                
    # C. Si aún faltan, rellenar con populares
    if len(relevant_faqs) < 5:
        popular_faqs = db.query(FAQEntry).filter(FAQEntry.activa == True).order_by(FAQEntry.veces_usada.desc()).limit(5).all()
        for f in popular_faqs:
            if f not in relevant_faqs and len(relevant_faqs) < 5:
                relevant_faqs.append(f)

    faq_text = "PREGUNTAS FRECUENTES:\n"
    for f in relevant_faqs:
        faq_text += f"P: {f.pregunta_clave}\nR: {f.respuesta}\n"

    # 6. Información de Financiamiento
    banks = db.query(Bank).filter(Bank.active == True).all()
    financing_text = "OPCIONES DE FINANCIAMIENTO Y TARJETAS:\n"
    
    if not banks:
        financing_text += "No hay opciones de financiamiento activas actualmente.\n"
    else:
        for bank in banks:
            rate_pct = float(bank.normal_card_rate) * 100
            financing_text += f"- {bank.name}: Tasa Tarjeta Normal {rate_pct:.2f}%\n"
            
            active_options = [opt for opt in bank.financing_options if opt.active]
            if active_options:
                financing_text += "  Extrafinanciamiento:\n"
                for opt in active_options:
                    opt_rate_pct = float(opt.rate) * 100
                    financing_text += f"  * {opt.months} Meses: {opt_rate_pct:.2f}% recargo total\n"
    
    financing_text += "\nNOTA PARA EL BOT: Para calcular cuota mensual: (Precio + (Precio * %Recargo)) / Meses.\n"
    financing_text += "EJEMPLO: Precio 10,000, Recargo 5% (0.05), 12 Meses -> (10000 + 500) / 12 = 875 mensual.\n"
    financing_text += "Si el cliente paga prima, restar prima antes de calcular recargo.\n"

    # --- PROTOCOLO DE RETOMAS (TRADE-IN) ---
    # Obtener políticas dinámicas de la base de datos
    trade_in_policies = db.query(TradeInPolicy).filter(TradeInPolicy.is_active == True).all()
    
    financing_text += "\nPROTOCOLO DE RETOMAS (TRADE-IN):\n"
    financing_text += "POLÍTICA DE MARCAS Y MODELOS:\n"
    
    if not trade_in_policies:
        # Fallback por defecto si no hay reglas en DB
        financing_text += "- ACEPTAMOS ÚNICAMENTE: Apple (iPhone) y Samsung.\n"
        financing_text += "- RECHAZAMOS AUTOMÁTICAMENTE: Huawei, Xiaomi, Motorola, LG, Google Pixel, Tablets, Relojes, Laptops, Consolas, etc.\n"
        financing_text += "- MODELOS RECHAZADOS: iPhone 8 o inferior, Samsung S10 o inferior, Serie A antigua.\n"
    else:
        accepted_brands = []
        rejected_patterns = []
        
        for policy in trade_in_policies:
            if policy.action == 'reject':
                reason_str = f" ({policy.reason})" if policy.reason else ""
                rejected_patterns.append(f"{policy.pattern}{reason_str}")
            elif policy.action == 'accept_with_conditions':
                accepted_brands.append(policy.pattern)
                
        if accepted_brands:
            financing_text += f"- ACEPTAMOS PREFERENTEMENTE: {', '.join(accepted_brands)}.\n"
        if rejected_patterns:
            financing_text += "- RECHAZAMOS AUTOMÁTICAMENTE LOS SIGUIENTES MODELOS/MARCAS:\n"
            for p in rejected_patterns:
                financing_text += f"  * {p}\n"
    
    financing_text += "\nINSTRUCCIONES DE INTERACCIÓN:\n"
    financing_text += "1. Consulta la lista de RECHAZADOS arriba. Si el cliente ofrece algo que coincida con un patrón rechazado, responde amablemente que NO lo aceptamos y explica la razón si existe.\n"
    financing_text += "2. Si la marca/modelo NO está rechazado explícitamente y parece ser de gama alta/reciente, ENTONCES procede a pedir los datos obligatorios: Modelo exacto, Color, Capacidad (GB), Estado (pantalla, batería, detalles estéticos), ¿Está liberado?\n"
    financing_text += "3. Una vez tengas los datos, di: 'Gracias, consultaré con el técnico el valor de retoma. Un momento por favor.'\n"
    financing_text += "4. Si tienes un número de encargado configurado, menciona que le enviarás los datos.\n"
    financing_text += "5. CÁLCULO DE DIFERENCIA: Precio Nuevo - Valor Retoma = Diferencia a Pagar.\n"
    financing_text += "6. Si paga la diferencia con TARJETA/FINANCIAMIENTO: El recargo se aplica SOLO a la Diferencia a Pagar.\n"
    financing_text += "   Fórmula: (Diferencia + (Diferencia * %Recargo)) / Meses.\n"

    # 7. Historial Reciente (Últimos 10 mensajes)
    recent_logs = db.query(InteractionLog).filter(
        InteractionLog.customer_id == customer.id
    ).order_by(InteractionLog.created_at.desc()).limit(10).all()
    
    context_history = [{"role": log.role, "content": log.content} for log in reversed(recent_logs)]

    # Combinar prompt del sistema con instrucción troll si aplica
    final_system_prompt = ai_config.system_prompt
    if troll_instruction:
        final_system_prompt += troll_instruction

    return AIContextResponse(
        system_prompt=final_system_prompt,
        bot_config={
            "model": ai_config.model_name,
            "temperature": ai_config.temperature,
            "tone": ai_config.voice_tone,
            "context_rules": ai_config.context_rules,
            "admin_phone": ai_config.admin_notification_phone or "el encargado" # Fallback si no hay número
        },
        customer_info={
            "name": customer.name,
            "is_troll": customer.is_troll,
            "reputation": customer.reputation_score
        },
        relevant_inventory=inventory_text,
        relevant_faqs=faq_text,
        financing_info=financing_text,
        previous_context=context_history
    )

@router.post("/log")
def log_interaction(log_data: InteractionLogCreate, db: Session = Depends(get_db)):
    """Guarda un mensaje en el historial"""
    profile = db.query(SalesProfile).filter(SalesProfile.slug == log_data.sales_profile_slug).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    customer = db.query(Customer).filter(Customer.phone_number == log_data.customer_phone).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    new_log = InteractionLog(
        customer_id=customer.id,
        sales_profile_id=profile.id,
        role=log_data.role,
        content=log_data.content,
        tokens_used=log_data.tokens_used
    )
    db.add(new_log)
    
    # Actualizar contadores del cliente
    customer.last_interaction_at = datetime.utcnow()
    customer.daily_message_count += 1
    
    db.commit()
    return {"status": "logged"}

@router.post("/training/submit")
def submit_training_example(submission: TrainingSubmission, db: Session = Depends(get_db)):
    """n8n envía una pregunta que no supo responder bien"""
    profile = db.query(SalesProfile).filter(SalesProfile.slug == submission.sales_profile_slug).first()
    
    queue_item = TrainingQueue(
        sales_profile_id=profile.id if profile else None,
        customer_question=submission.customer_question,
        ai_proposed_answer=submission.ai_proposed_answer,
        status="pending"
    )
    db.add(queue_item)
    db.commit()
    return {"status": "submitted_for_review"}

@router.post("/flag-troll")
def flag_troll(phone_number: str = Body(..., embed=True), reason: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """Marca un cliente como troll manualmente o por IA"""
    customer = db.query(Customer).filter(Customer.phone_number == phone_number).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    customer.is_troll = True
    customer.reputation_score = 0
    customer.notes = (customer.notes or "") + f"\n[AUTO-FLAG] Marcado como troll: {reason}"
    
    db.commit()
    return {"status": "flagged", "customer": customer.phone_number}

# --- Training & Insights Endpoints ---

@router.get("/training-queue", response_model=List[Dict[str, Any]])
def list_training_queue(status: str = "pending", db: Session = Depends(get_db)):
    """Lista preguntas pendientes de revisión"""
    items = db.query(TrainingQueue).filter(TrainingQueue.status == status).order_by(TrainingQueue.created_at.desc()).all()
    return [{
        "id": i.id,
        "customer_question": i.customer_question,
        "ai_proposed_answer": i.ai_proposed_answer,
        "status": i.status,
        "created_at": i.created_at,
        "sales_profile": {
            "name": i.sales_profile.name if i.sales_profile else "Desconocido"
        }
    } for i in items]

@router.post("/training-queue/{item_id}/resolve")
def resolve_training_item(item_id: int, action: str = Body(..., embed=True), correction: str = Body(None, embed=True), db: Session = Depends(get_db)):
    """Resuelve un item de entrenamiento: aprobar, rechazar o convertir a FAQ"""
    item = db.query(TrainingQueue).filter(TrainingQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    if action == "convert_to_faq":
        if not correction:
            raise HTTPException(status_code=400, detail="Correction required for FAQ")
        
        # Crear FAQ automáticamente
        # Verificar si ya existe una FAQ similar para evitar duplicados
        existing_faq = db.query(FAQEntry).filter(FAQEntry.pregunta_clave == item.customer_question[:255]).first()
        if existing_faq:
            # Actualizar la existente en lugar de crear duplicado
            existing_faq.respuesta = correction
            existing_faq.veces_usada += 1
        else:
            new_faq = FAQEntry(
                pregunta_clave=item.customer_question[:255],
                respuesta=correction,
                categoria="general",
                activa=True
            )
            db.add(new_faq)
            
        item.status = "converted_to_faq"
        item.admin_correction = correction
        
    elif action == "reject":
        item.status = "rejected"
    elif action == "approve":
        item.status = "approved"
        
    db.commit()
    return {"status": "resolved"}

@router.get("/customers", response_model=List[Dict[str, Any]])
def list_customers_ai(search: Optional[str] = None, db: Session = Depends(get_db)):
    """Lista clientes con datos de inteligencia"""
    query = db.query(Customer)
    if search:
        query = query.filter(Customer.phone_number.contains(search) | Customer.name.contains(search))
    
    customers = query.order_by(Customer.last_interaction_at.desc()).limit(50).all()
    return [{
        "id": c.id,
        "phone_number": c.phone_number,
        "name": c.name,
        "is_troll": c.is_troll,
        "is_blocked": c.is_blocked,
        "reputation_score": c.reputation_score,
        "daily_message_count": c.daily_message_count,
        "last_interaction_at": c.last_interaction_at,
        "created_at": c.created_at
    } for c in customers]

@router.patch("/customers/{customer_id}")
def update_customer_ai(customer_id: int, updates: Dict[str, Any], db: Session = Depends(get_db)):
    """Actualiza estado de cliente (bloqueo, troll, notas)"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    if "is_troll" in updates:
        customer.is_troll = updates["is_troll"]
    if "is_blocked" in updates:
        customer.is_blocked = updates["is_blocked"]
    if "notes" in updates:
        customer.notes = updates["notes"]
        
    db.commit()
    return {"status": "updated"}


# --- Trade-In Policies Endpoints ---

@router.get("/trade-in-policies", response_model=List[TradeInPolicyResponse])
def list_trade_in_policies(db: Session = Depends(get_db)):
    """Lista todas las políticas de retoma"""
    return db.query(TradeInPolicy).order_by(TradeInPolicy.created_at.desc()).all()

@router.post("/trade-in-policies", response_model=TradeInPolicyResponse)
def create_trade_in_policy(policy: TradeInPolicyCreate, db: Session = Depends(get_db)):
    """Crea una nueva política de retoma"""
    new_policy = TradeInPolicy(**policy.dict())
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)
    return new_policy

@router.delete("/trade-in-policies/{policy_id}")
def delete_trade_in_policy(policy_id: int, db: Session = Depends(get_db)):
    """Elimina una política de retoma"""
    policy = db.query(TradeInPolicy).filter(TradeInPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    db.delete(policy)
    db.commit()
    return {"status": "deleted"}

class LinkOrderRequest(BaseModel):
    customer_phone: str
    order_id: int

@router.post("/link-order")
def link_order_to_interaction(request: LinkOrderRequest, db: Session = Depends(get_db)):
    """Vincula la última interacción de un cliente con una orden creada (Atribución de Venta)"""
    customer = db.query(Customer).filter(Customer.phone_number == request.customer_phone).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    # Buscar la última interacción del cliente
    last_interaction = db.query(InteractionLog).filter(
        InteractionLog.customer_id == customer.id
    ).order_by(InteractionLog.created_at.desc()).first()
    
    if last_interaction:
        last_interaction.converted_order_id = request.order_id
        db.commit()
        return {"status": "linked", "interaction_id": last_interaction.id}
        
    return {"status": "no_interaction_found"}
    db.refresh(new_policy)
    return new_policy

@router.delete("/trade-in-policies/{policy_id}")
def delete_trade_in_policy(policy_id: int, db: Session = Depends(get_db)):
    """Elimina una política de retoma"""
    policy = db.query(TradeInPolicy).filter(TradeInPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    db.delete(policy)
    db.commit()
    return {"status": "deleted"}
