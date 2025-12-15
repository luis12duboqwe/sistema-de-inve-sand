import requests
import json

BASE_URL = "http://localhost:8000/api"

def verify_learning():
    print("🔍 Verificando si la IA aprendió la nueva respuesta...")
    
    # 1. Obtener slug del perfil
    try:
        resp = requests.get(f"{BASE_URL}/sales-profiles")
        profiles = resp.json()
        bot_profile = next((p for p in profiles if p['tipo'] == 'bot_ia'), profiles[0])
        slug = bot_profile['slug']
    except:
        print("❌ Error obteniendo perfil")
        return

    # 2. Preguntar lo que acabamos de enseñar
    question = "¿Aceptan pago con criptomonedas?"
    payload = {
        "sales_profile_slug": slug,
        "customer_phone": "50499998888",
        "message_content": question
    }
    
    resp = requests.post(f"{BASE_URL}/ai/context", json=payload)
    if resp.status_code == 200:
        data = resp.json()
        faqs = data.get('relevant_faqs', '')
        print("\n📄 Contexto de FAQs devuelto por la API:")
        print("-" * 40)
        print(faqs)
        print("-" * 40)
        
        if "criptomonedas" in faqs.lower() or "bitcoin" in faqs.lower():
            print("\n✅ ¡ÉXITO! La IA ahora tiene la información en su contexto.")
        else:
            print("\n⚠️ ADVERTENCIA: La respuesta no aparece claramente en las FAQs devueltas.")
            print("Posible causa: La búsqueda de palabras clave no encontró coincidencia o la FAQ no está activa.")
    else:
        print(f"❌ Error API: {resp.status_code}")

if __name__ == "__main__":
    verify_learning()
