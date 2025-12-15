# Prueba de Simulación n8n

He creado un script de Python que simula exactamente cómo n8n interactuará con tu sistema. Este script prueba todo el flujo de inteligencia artificial sin necesidad de configurar n8n todavía.

## Cómo ejecutar la prueba

1. Abre una terminal en VS Code.
2. Ejecuta el siguiente comando:

```bash
python3 test_n8n_simulation.py
```

## Qué hace esta prueba

1. **Busca un Bot**: Encuentra automáticamente el primer perfil de venta tipo "Bot IA" en tu base de datos.
2. **Simula un Cliente**: Crea un cliente ficticio ("Cliente de Prueba") con el número `50499998888`.
3. **Pide Contexto (`/api/ai/context`)**: Envía el mensaje "Hola, tienen iPhone 13 disponible?" y muestra lo que el "Cerebro" responde (Inventario, Prompt, etc.).
4. **Guarda Logs (`/api/ai/log`)**: Registra la conversación en la base de datos.
5. **Prueba Entrenamiento (`/api/ai/training/submit`)**: Envía una pregunta difícil ("¿Aceptan criptomonedas?") a la cola de revisión.

## Resultados Esperados

Si todo está bien, verás mensajes con ✅ verde indicando que cada paso funcionó.

Después de correr la prueba, puedes ir al **Centro de Entrenamiento** en la web y verás la pregunta sobre criptomonedas pendiente de revisión.
