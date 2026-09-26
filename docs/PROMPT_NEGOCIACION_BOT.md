# Estrategia de Negociación para Bot IA (V3.0)

Este documento define la lógica de negociación que debe seguir el Agente de IA al interactuar con clientes. La prioridad es defender el precio publicado, explicar el valor de garantía/regalías y usar descuentos de forma gradual.

## 1. Principios fundamentales

1. **Defender el precio primero**: no ofrecer descuento de entrada.
2. **Números cerrados en celulares**: si se rebaja un celular, el precio final debe quedar en centenas cerradas (por ejemplo 9,800; 21,600; 35,200). Esta restricción no se fuerza sobre accesorios de bajo valor.
3. **Valor sobre precio**: antes de rebajar, explicar garantía, calidad, condición del equipo y accesorios/regalías incluidas.
4. **Regalías vs. descuento**: si el cliente exige una rebaja mayor al 2%, se deben retirar las regalías.
5. **No vender bajo costo**: el backend rechazará cualquier precio inferior al costo registrado del producto.
6. **No improvisar excepciones**: el bot nunca debe prometer una rebaja que requiera autorización humana antes de obtenerla.
7. **Una sola moneda para la venta**: las órdenes y pagos se contabilizan en HNL. Si un producto está catalogado en USD, catálogo y costo se convierten a HNL con la tasa del perfil antes de validar descuentos o margen.

## 2. Flujo de negociación

### Paso 0: precio de lista

- Dar el precio oficial del sistema.
- Explicar garantía y regalías estándar incluidas.
- Intentar cerrar la venta sin descuento.

Ejemplo:

> “El equipo está en L 10,000 e incluye garantía y las regalías disponibles para esa promoción.”

### Paso 1: primer ajuste — hasta 2%

Si el cliente pide una rebaja y hace falta negociar:

- el bot puede ofrecer hasta aproximadamente 2%;
- si se trata de un celular, debe redondear a una centena cerrada;
- puede mantener las regalías/promociones de accesorios.

Ejemplo: L 10,000 → L 9,800.

### Paso 2: oferta sin regalías — hasta 3%

Si el cliente insiste:

- retirar las regalías/promociones;
- el bot o vendedor puede negociar hasta 3%;
- en celulares, mantener siempre el precio final en centenas cerradas;
- intentar cerrar la venta antes de escalar.

Para celulares, el sistema debe escoger una centena que no exceda el 3% real. Por ejemplo, si el cálculo exacto cae entre dos centenas, usar la que mantenga el descuento dentro del límite.

### Paso 3: excepción del propietario — hasta 4%

Si la venta está a punto de perderse y el cliente todavía pide más:

- el bot **no** puede conceder el 4% por sí solo;
- debe consultar al propietario;
- la venta con ese tramo debe confirmarse desde una sesión Super Admin;
- no puede llevar regalías/promociones normales;
- si es un celular, el precio debe seguir siendo una centena cerrada;
- ningún precio puede quedar bajo costo.

Mensaje sugerido al cliente:

> “Ese precio ya requiere autorización. Déjame consultarlo antes de prometerte algo que el sistema no me permita respetar.”

### Paso 4: petición superior al 4%

El POS normal no admite descuentos superiores al 4%.

Si existe una razón comercial extraordinaria, primero debe revisarse/cambiarse el precio de catálogo mediante el proceso administrativo correspondiente. El bot no debe prometer la excepción ni intentar saltarse el límite enviando un precio manual.

## 3. Política de regalías

Las regalías normales son **accesorios**: por ejemplo funda, audífonos o cargador promocional.

- Con regalías: máximo 2% de descuento.
- Para llegar hasta 3%: retirar regalías.
- Para una excepción de hasta 4%: retirar regalías y obtener autorización del propietario.
- Un celular no puede marcarse como regalo/promoción por un usuario normal.
- Una excepción extraordinaria que marque un celular como regalo requiere Super Admin y queda registrada en la orden/inventario.
- No se permiten órdenes compuestas únicamente por regalos/promociones.

## 4. Moneda y tasa de cambio

Las órdenes se totalizan en HNL.

- Productos HNL/Lps: precio y costo se usan directamente.
- Productos USD: precio de catálogo y costo se convierten a HNL con `exchange_rate` del perfil de venta.
- Si el perfil no tiene una tasa válida, se conserva el fallback histórico de 25 HNL/USD.
- Un `precio_unitario` negociado se interpreta en HNL.
- El costo histórico guardado en la orden también queda en HNL para que margen y reportería comparen cantidades equivalentes.

Ejemplo: producto USD 400, costo USD 250, tasa 25.00 → catálogo HNL 10,000 y costo HNL 6,250. Un precio negociado de HNL 9,800 es un descuento válido de 2%.

## 5. Límites técnicos que debe respetar la IA

El backend es la fuente de verdad y debe rechazar cualquier orden que viole estas reglas:

- celular rebajado cuyo precio no sea una centena cerrada;
- descuento mayor al 2% cuando hay regalías;
- descuento mayor al 3% para vendedor o integración automática;
- descuento de hasta 4% sin una sesión Super Admin;
- descuento superior al 4%;
- precio inferior al costo registrado, después de normalizar moneda;
- precio manual superior al precio de catálogo, después de normalizar moneda;
- celular marcado como regalo por un usuario normal;
- manipulación de precio, costo o condición de regalo al editar una orden existente.

La integración autenticada del bot puede usar los tramos automáticos de hasta 2%/3%, pero **nunca recibe automáticamente la facultad reservada al propietario**.

La configuración de IA también está limitada técnicamente a un máximo automático de 3%. Las configuraciones históricas superiores se normalizan al iniciar el backend y se añade una regla canónica al final del contexto del bot. Esa regla prevalece sobre prompts antiguos o personalizados que pudieran mencionar porcentajes incompatibles.

## 6. Edición de órdenes existentes

Editar una orden no es un mecanismo para renegociar el precio:

- el cliente/API no puede inyectar un nuevo precio, costo o bandera de regalo;
- si el producto ya existía en la orden, se conserva su precio/regalía original hasta la cantidad que ya estaba pactada;
- si se aumenta la cantidad, las unidades adicionales entran a precio de catálogo y sin regalías heredadas;
- si se añade otro producto, entra a precio de catálogo y sin regalías heredadas.

Esto evita tanto perder una condición comercial ya acordada como multiplicarla mediante una edición.

## 7. Ejemplo de conversación

**Cliente:** ¿Cuánto el iPhone?

**Bot:** Está en L 10,000. Incluye garantía y las regalías disponibles para esta promoción.

**Cliente:** ¿Es lo menos?

**Bot:** Puedo hacerte un ajuste y dejártelo en **L 9,800**, manteniendo las regalías.

**Cliente:** Todavía está alto.

**Bot:** Puedo intentar bajarlo un poco más si lo llevas sin las regalías. Ese sería ya el último tramo que puedo manejar directamente.

**Cliente:** Déjamelo todavía más barato.

**Bot:** Para bajar de ese punto necesito autorización del propietario. Prefiero consultarlo antes de ofrecerte algo que no pueda respetar.

## 8. Fuente de verdad

Este documento describe el comportamiento esperado de negociación. La autorización final la impone el backend al crear la orden; una instrucción del prompt, del frontend o de una integración nunca puede sustituir esa validación.
