from app.database import SessionLocal
from app.models import FAQEntry

db = SessionLocal()
faqs = db.query(FAQEntry).all()

print(f"Total FAQs: {len(faqs)}")
for faq in faqs:
    print(f"ID: {faq.id}, Pregunta: {faq.pregunta_clave}, Respuesta: {faq.respuesta}, Activa: {faq.activa}")

db.close()
