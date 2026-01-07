import requests
import json

BASE_URL = "http://localhost:8000/api"

def simulate_whatsapp_admin_flow():
    print("\n📱 SIMULACIÓN: Flujo de Entrenamiento vía WhatsApp")
    print("=================================================")

    # 1. Obtener Perfil y Configurar Teléfono Admin
    print("\n1️⃣ Configurando teléfono del administrador...")
    try:
        resp = requests.get(f"{BASE_URL}/sales-profiles")
        profiles = resp.json()
        bot_profile = next((p for p in profiles if p['tipo'] == 'bot_ia'), profiles[0])
        
        # Actualizar config con teléfono
        config_payload = {
            "sales_profile_id": bot_profile['id'],
            "system_prompt": "Eres un asistente útil.",
            "admin_notification_phone": "50499991111"  # Tu número
        }
        requests.post(f"{BASE_URL}/ai/config/{bot_profile['id']}", json=config_payload)
        print(f"✅ Teléfono de notificación configurado: 50499991111")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # 2. Probar respuesta automática del bot
    print("\n2️⃣ Probando /api/ai/reply con un mensaje real...")
    reply_payload = {
        "sales_profile_slug": bot_profile['slug'],
        "customer_phone": "50433334444",
        "customer_name": "Cliente Demo",
        "message_content": "Hola, ¿tienen iPhone 15 Pro Max?"
    }

    try:
        reply_res = requests.post(f"{BASE_URL}/ai/reply", json=reply_payload)
        if reply_res.status_code == 200:
            data = reply_res.json()
            print("✅ Backend respondió:")
            print(f"   -> {data['reply']}")
        else:
            print(f"⚠️ No fue posible obtener respuesta automática: {reply_res.text}")
    except Exception as err:
        print(f"⚠️ Error llamando /api/ai/reply: {err}")

    # 3. Cliente hace pregunta difícil
    question = "¿Tienen garantía extendida para pantallas rotas?"
    print(f"\n3️⃣ Cliente pregunta: '{question}'")
    
    # 4. Bot no sabe y envía a cola (n8n hace esto)
    print("🤖 Bot: No estoy seguro -> Enviando a revisión...")
    submit_resp = requests.post(f"{BASE_URL}/ai/training/submit", json={
        "sales_profile_slug": bot_profile['slug'],
        "customer_question": question,
        "ai_proposed_answer": "No tengo información sobre eso."
    })
    
    # En un caso real, el endpoint devuelve el ID, pero aquí lo simulamos buscando el último
    queue_resp = requests.get(f"{BASE_URL}/ai/training-queue")
    pending_items = queue_resp.json()
    if not pending_items:
        print("❌ Error: No se encontró el item en la cola.")
        return
        
    item_id = pending_items[0]['id']
    print(f"✅ Item creado en cola con ID: {item_id}")

    # 4. Simular Notificación a WhatsApp (n8n leería 'admin_phone' del contexto)
    print(f"\n📨 [WhatsApp a 50499991111]:")
    print(f"   '⚠️ Pregunta sin respuesta (ID {item_id}): {question}'")
    print(f"   'Responde con la solución.'")

    # 5. Admin responde por WhatsApp
    admin_response = "Sí, cubrimos 50% del costo si es en los primeros 3 meses."
    print(f"\n👤 Admin responde: '{admin_response}'")

    # 6. n8n recibe respuesta y llama a la API
    print(f"\n🔄 n8n procesando respuesta -> Llamando a API Resolve...")
    resolve_payload = {
        "action": "convert_to_faq",
        "correction": admin_response
    }
    
    res = requests.post(f"{BASE_URL}/ai/training-queue/{item_id}/resolve", json=resolve_payload)
    
    if res.status_code == 200:
        print("✅ ¡ÉXITO! La respuesta se guardó y se creó la FAQ automáticamente.")
        print("   Ahora el bot sabrá responder esto en el futuro.")
    else:
        print(f"❌ Error al resolver: {res.text}")

if __name__ == "__main__":
    simulate_whatsapp_admin_flow()
