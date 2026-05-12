import requests
import json
import sys
import os

BASE_URL = "http://localhost:8000/api"
SERVICE_TOKEN = os.getenv("N8N_AUTH_TOKEN", "")


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if SERVICE_TOKEN:
        headers["X-N8N-Token"] = SERVICE_TOKEN
    return headers

def print_step(step, message):
    print(f"\n{'='*50}")
    print(f"📍 PASO {step}: {message}")
    print(f"{'='*50}")

def test_n8n_flow():
    # 1. Obtener un perfil válido
    print_step(1, "Obteniendo perfil de venta (Bot)")
    try:
        resp = requests.get(f"{BASE_URL}/sales-profiles")
        profiles = resp.json()
        if not profiles:
            print("❌ No hay perfiles de venta. Crea uno primero en el frontend.")
            return
        
        # Buscar uno de tipo bot_ia o usar el primero
        bot_profile = next((p for p in profiles if p['tipo'] == 'bot_ia'), profiles[0])
        slug = bot_profile['slug']
        print(f"✅ Usando perfil: {bot_profile['name']} (Slug: {slug})")
    except Exception as e:
        print(f"❌ Error conectando al backend: {e}")
        return

    # 2. Simular Webhook de WhatsApp (Usuario escribe)
    customer_phone = "50499998888"
    customer_name = "Cliente de Prueba"
    user_message = "Hola, tienen iPhone 13 disponible?"
    
    print_step(2, "n8n: Solicitando Contexto (/api/ai/context)")
    payload_context = {
        "sales_profile_slug": slug,
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "message_content": user_message
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/ai/context", json=payload_context, headers=_headers())
        if resp.status_code == 200:
            data = resp.json()
            print("✅ Contexto Recibido:")
            print(f"   - Cliente: {data['customer_info']['name']} (Reputación: {data['customer_info']['reputation']})")
            print(f"   - Config Bot: Modelo {data['bot_config']['model']}")
            print(f"   - Inventario Relevante (Extracto): {data['relevant_inventory'][:100]}...")
            
            ai_response_text = "Simulación: respuesta generada manualmente."
        else:
            print(f"❌ Error {resp.status_code}: {resp.text}")
            return
    except Exception as e:
        print(f"❌ Error en request: {e}")
        return

    # 3. Generar respuesta real usando el backend
    print_step(3, "Backend nativo: /api/ai/handle-message (sin orquestación n8n)")
    payload_reply = {
        "sales_profile_slug": slug,
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "message_content": user_message
    }

    try:
        resp = requests.post(f"{BASE_URL}/ai/handle-message", json=payload_reply, headers=_headers())
        if resp.status_code == 200:
            ai_data = resp.json()
            ai_response_text = ai_data["reply"]
            print("✅ Backend generó la respuesta con OpenAI (flujo unificado):")
            print(f"   > {ai_response_text}")
        else:
            print(f"⚠️ No se pudo generar respuesta (status {resp.status_code}). Se usará texto simulado.")
            print(f"   Detalle: {resp.text}")
    except Exception as e:
        print(f"⚠️ Error al llamar /api/ai/reply: {e}")

    # 4. Registrar Interacción (Log)
    print_step(4, "n8n: Guardando Logs (/api/ai/log)")
    
    # Log User Message
    try:
        requests.post(f"{BASE_URL}/ai/log", json={
            "sales_profile_slug": slug,
            "customer_phone": customer_phone,
            "role": "user",
            "content": user_message
        }, headers=_headers())
        print("✅ Mensaje del usuario registrado.")
        
        # Log AI Response
        requests.post(f"{BASE_URL}/ai/log", json={
            "sales_profile_slug": slug,
            "customer_phone": customer_phone,
            "role": "assistant",
            "content": ai_response_text
        }, headers=_headers())
        print("✅ Respuesta de la IA registrada.")
    except Exception as e:
        print(f"❌ Error guardando logs: {e}")

    # 5. Simular Pregunta Difícil (Training Queue)
    print_step(5, "n8n: Enviando a Cola de Entrenamiento (/api/ai/training/submit)")
    difficult_question = "¿Aceptan pago con criptomonedas?"
    ai_uncertain_answer = "Lo siento, no estoy seguro sobre esa forma de pago."
    
    try:
        resp = requests.post(f"{BASE_URL}/ai/training/submit", json={
            "sales_profile_slug": slug,
            "customer_question": difficult_question,
            "ai_proposed_answer": ai_uncertain_answer
        }, headers=_headers())
        if resp.status_code == 200:
            print("✅ Pregunta enviada a revisión humana exitosamente.")
        else:
            print(f"❌ Error enviando a entrenamiento: {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 6. Crear orden automática desde intención IA
    print_step(6, "Backend nativo: crear orden dentro de /api/ai/handle-message")
    try:
        products_resp = requests.get(f"{BASE_URL}/products", headers=_headers())
        if products_resp.status_code != 200:
            print(f"❌ No se pudieron listar productos: {products_resp.text}")
            return

        products_data = products_resp.json()
        products = products_data.get("items", []) if isinstance(products_data, dict) else products_data
        if not products:
            print("❌ No hay productos para probar creación de orden")
            return

        selected_product = products[0]
        product_id = selected_product.get("id")
        location_id = selected_product.get("stock_items", [{}])[0].get("location_id", 1)
        imeis_payload: list[str] = []

        if selected_product.get("is_serialized"):
            imeis_resp = requests.get(
                f"{BASE_URL}/products/{product_id}/imeis?location_id={location_id}",
                headers=_headers(),
            )
            if imeis_resp.status_code == 200:
                available_imeis = imeis_resp.json()
                if available_imeis:
                    imeis_payload = [str(available_imeis[0])]

        item_payload = {
            "product_id": product_id,
            "cantidad": 1,
        }
        if imeis_payload:
            item_payload["imeis"] = imeis_payload

        handle_message_payload = {
            "sales_profile_slug": slug,
            "customer_phone": customer_phone,
            "customer_name": customer_name,
            "message_content": "Listo, confírmame la compra",
            "order_intent": {
                "source_location_id": location_id,
                "canal": "whatsapp",
                "metodo_pago": "efectivo",
                "items": [item_payload],
                "notes": "Orden creada automáticamente por flujo IA nativo",
                "auto_create": True,
                "auto_link_interaction": True,
            },
        }

        order_res = requests.post(
            f"{BASE_URL}/ai/handle-message",
            json=handle_message_payload,
            headers=_headers(),
        )

        if order_res.status_code == 200:
            order_data = order_res.json().get("order") or {}
            print("✅ Orden creada por IA exitosamente")
            print(f"   - order_id: {order_data.get('order_id')}")
            print(f"   - linked_interaction: {order_data.get('linked_interaction')}")
        else:
            print(f"❌ Error creando orden IA: {order_res.text}")
    except Exception as e:
        print(f"❌ Error en creación de orden IA: {e}")

    # 7. Test Photo Request
    print_step(7, "Backend nativo: simular solicitud de fotos de cliente")
    photo_payload = {
        "sales_profile_slug": slug,
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "message_content": "Quiero ver fotos del iPhone 15 en gris por favor"
    }

    try:
        photo_res = requests.post(f"{BASE_URL}/ai/handle-message", json=photo_payload, headers=_headers())
        if photo_res.status_code == 200:
            resp_data = photo_res.json()
            print("✅ Solicitud de fotos procesada.")
            print(f"   - Respuesta IA: {resp_data.get('reply')}")
            if resp_data.get("photo_request_created"):
                 print("   📸 Solicitud interna de fotos CREA EXITOSAMENTE.")
        else:
            print(f"❌ Error creando solicitud de fotos: {photo_res.text}")
    except Exception as e:
        print(f"❌ Error en creación solicitud de fotos: {e}")

if __name__ == "__main__":
    test_n8n_flow()
