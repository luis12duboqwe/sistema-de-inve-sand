import requests
import json
import sys

BASE_URL = "http://localhost:8000/api"

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
        resp = requests.post(f"{BASE_URL}/ai/context", json=payload_context)
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
    print_step(3, "n8n: Solicitando respuesta completa (/api/ai/reply)")
    payload_reply = {
        "sales_profile_slug": slug,
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "message_content": user_message
    }

    try:
        resp = requests.post(f"{BASE_URL}/ai/reply", json=payload_reply)
        if resp.status_code == 200:
            ai_data = resp.json()
            ai_response_text = ai_data["reply"]
            print("✅ Backend generó la respuesta con OpenAI:")
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
        })
        print("✅ Mensaje del usuario registrado.")
        
        # Log AI Response
        requests.post(f"{BASE_URL}/ai/log", json={
            "sales_profile_slug": slug,
            "customer_phone": customer_phone,
            "role": "assistant",
            "content": ai_response_text
        })
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
        })
        if resp.status_code == 200:
            print("✅ Pregunta enviada a revisión humana exitosamente.")
        else:
            print(f"❌ Error enviando a entrenamiento: {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_n8n_flow()
