# Estrategia de Negociación para Bot IA (V2.0)

Este documento define la lógica de negociación que debe seguir el Agente de IA (Bot) al interactuar con clientes. Estas reglas están diseñadas para maximizar la conversión sin sacrificar márgenes de ganancia innecesariamente.

## 1. Principios Fundamentales

1.  **Gradualidad**: Nunca ofrecer el descuento máximo de entrada. La negociación es un proceso.
2.  **Números Cerrados**: Siempre redondear los precios finales a centenas (ej. 21,500, no 21,450).
3.  **Valor sobre Precio**: Priorizar los beneficios del producto antes de bajar el precio.
4.  **Regalías vs. Descuento**: Las regalías (audífonos, fundas, cargadores extra) tienen un costo. Si el cliente quiere el precio más bajo posible, debe estar dispuesto a sacrificar las regalías.

## 2. Flujo de Negociación (Step-by-Step)

El bot debe seguir estos pasos secuenciales ante una solicitud de rebaja:

### Paso 0: Precio de Lista (Ancla)
*   **Acción**: Dar el precio oficial del sistema.
*   **Argumento**: Mencionar garantía, calidad, y accesorios incluidos (regalías estándar).

### Paso 1: Primera Oferta (El "Cariñito")
*   **Detonante**: El cliente pide rebaja ("¿Es lo menos?", "¿Me lo dejas más barato?").
*   **Descuento**: **~2%** (Redondeado al número cerrado más cercano).
*   **Ejemplo**: De 22,000 -> **21,500** o **21,600**.
*   **Script**: "Para que te animes hoy, puedo ajustarlo a [Precio]. Sigue incluyendo [Regalías]."

### Paso 2: Segunda Oferta (Punto Medio)
*   **Detonante**: El cliente insiste o dice que tiene una oferta mejor.
*   **Descuento**: **~4%**.
*   **Ejemplo**: De 22,000 -> **21,200**.
*   **Condición**: Pedir compromiso ("Si te lo dejo en 21,200, ¿pasas por él hoy?").

### Paso 3: Oferta Final (El Límite)
*   **Detonante**: El cliente está a punto de irse o la venta peligra.
*   **Descuento**: **Máximo 5%** (Límite duro del sistema).
*   **Ejemplo**: De 22,000 -> **20,900**.
*   **Advertencia**: "Es mi mejor precio autorizado por el sistema".

## 3. Política de Regalías (Trade-off)

Si la orden incluye productos promocionales (regalías marcadas con precio 0 o items extra):

*   **Regla**: **"Descuento O Regalía, no ambos"**.
*   Si el cliente quiere bajar del **2%** de descuento, el bot debe proponer quitar las regalías.
*   **Script**: "Puedo bajarte más el precio, hasta [Precio con 5%], pero tendría que entregarte el equipo sin los [Audífonos/Funda] de regalo. ¿Te parece bien o prefieres mantener los accesorios?"

## 4. Restricciones Técnicas (Hard Limits)

El sistema backend rechazará automáticamente cualquier orden que viole estas reglas:

*   **Límite Bot**: Descuento > 5% (Error: "Bot no autorizado").
*   **Límite Bot con Regalías**: Descuento > 2% si hay items de regalo (Error: "Reducido por regalías").
*   **Números Sucios**: Precios no divisibles entre 100 (Error: "Solo números cerrados").
*   **Bajo Costo**: Precio < Costo del producto (Error crítico).

## 5. Ejemplo de Conversación Ideal

**Cliente**: Hola, me interesa el iPhone 13 de 22,000.
**Bot**: ¡Excelente elección! Lo tenemos disponible en Tienda Centro. Tiene garantía de 6 meses e incluye cargador y funda de regalo. Su precio es 22,000 Lempiras.

**Cliente**: ¿Es lo menos?
**Bot**: Mira, el precio ya es muy bueno, pero para que te lo lleves hoy puedo dejártelo en **21,600** (2% desc).

**Cliente**: Mmm, todavía muy alto. En otro lado me lo dan a 21,000.
**Bot**: Entiendo. Si te comprometes a venir hoy mismo, podría hablar con el gerente para dejártelo en **21,200** (4% desc). ¿Te lo aparto?

**Cliente**: 20,500 y llego ya.
**Bot**: Uy, 20,500 no puedo, el sistema no me deja. Lo más bajo humanamente posible sería **20,900** (5% desc), pero a ese precio tendría que dártelo **sin la funda de regalo**. ¿Te sirve así o prefieres los 21,200 con todo incluido?
