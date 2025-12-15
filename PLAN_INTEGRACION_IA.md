# Plan de Integración de Inteligencia Artificial (Sistema Multi-Agente)

Este documento sirve como hoja de ruta para transformar el sistema de inventario en una Central de Inteligencia de Ventas capaz de gestionar múltiples perfiles de IA (Bots) conectados vía n8n.

## 1. Fase 1: Cimientos de Datos (Backend)
El objetivo es preparar la base de datos para soportar clientes, configuraciones de IA y aprendizaje, sin afectar el funcionamiento actual.

- [x] **Crear Script de Migración (`backend/migrate_add_ai_intelligence.py`)**
    - [x] Tabla `customers`: Para gestión avanzada de clientes (detectar trolls, reputación, notas).
    - [x] Tabla `ai_profile_configs`: Para guardar la personalidad, prompt y reglas de cada Bot (vinculado a `SalesProfile`).
    - [x] Tabla `interaction_logs`: Para guardar el historial de conversaciones y medir desempeño.
    - [x] Tabla `training_queue`: Para guardar las preguntas que la IA no supo responder (Human-in-the-loop).
- [x] **Actualizar Modelos ORM (`backend/app/models.py`)**
    - [x] Definir clases `Customer`, `AIProfileConfig`, `InteractionLog`, `TrainingQueue`.
    - [x] Establecer relaciones con `SalesProfile` y `Order`.
- [x] **Definir Schemas Pydantic (`backend/app/schemas.py`)**
    - [x] Schemas para configuración de IA (Prompt, Temperatura, Modelo).
    - [x] Schemas para interacción con n8n (Input/Output de chat).

## 2. Fase 2: API de Inteligencia (Endpoints para n8n)
Creación de los "nervios" que conectarán n8n con el cerebro del sistema.

- [x] **Crear Router `backend/app/routers/ai_intelligence.py`**
    - [x] `GET /api/ai/config/{sales_profile_id}`: Endpoint para que n8n descargue la personalidad del bot actual.
    - [x] `POST /api/ai/context`: El "Cerebro". Recibe la pregunta del cliente y devuelve:
        - Inventario relevante (filtrado y resumido).
        - FAQs relacionadas.
        - Historial del cliente (si existe).
    - [x] `POST /api/ai/log`: Para que n8n guarde lo que se habló (memoria).
    - [x] `POST /api/ai/flag`: Para marcar automáticamente a un cliente como "Troll" o "VIP".
    - [x] `POST /api/ai/training/submit`: Para que n8n envíe preguntas desconocidas a la cola de revisión.

## 3. Fase 3: Gestión de Perfiles IA (Frontend)
Interfaz visual para que puedas crear y editar tus bots sin tocar código ni n8n.

- [x] **Componente `AIProfilesList`**
    - [x] Ver lista de perfiles de venta que tienen IA activada (Integrado en `SalesProfilesList`).
- [x] **Editor de Personalidad (`AIProfileDialog`)**
    - [x] Campo para **System Prompt** (Instrucciones base).
    - [x] Selectores para **Tono de Voz** (Formal, Jovial, Agresivo).
    - [x] Configuración de **Modelo** (GPT-4o, GPT-3.5, etc.).
    - [x] Configuración de **Reglas de Inventario** (¿Qué tiendas puede ver este bot?).
- [x] **Integración en `SalesProfiles`**
    - [x] Agregar pestaña "Configuración IA" en el diálogo de edición de perfiles existente.

## 4. Fase 4: Centro de Entrenamiento (Frontend)
El módulo donde tú le enseñas al sistema a ser mejor.

- [x] **Vista `AITrainingCenter`**
    - [x] Tabla de "Preguntas Pendientes" (desde `training_queue`).
    - [x] Formulario para responder la pregunta.
    - [x] **Acción Mágica**: "Responder y Crear FAQ". Al guardar, actualiza la IA y crea una entrada en la base de conocimientos automáticamente.
- [x] **Vista de Clientes (`CustomerInsights`)**
    - [x] Ver lista de clientes capturados.
    - [x] Ver historial de chats de un cliente.
    - [x] Botón manual para bloquear/desbloquear (Troll management).

## 5. Fase 5: Documentación y Conexión
- [x] **Guía de Integración n8n**
    - [x] Crear un JSON de ejemplo de un flujo de n8n que usa estos endpoints.
    - [x] Documentar los payloads de entrada/salida.
- [x] **Pruebas de Flujo**
    - [x] Simular una conversación completa desde Postman/Curl.

---
**Estado Actual:** ✅ Proyecto Completado
**Siguiente Paso:** Despliegue y Conexión con n8n.
