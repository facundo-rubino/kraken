# Plan de reorganización — sistema de productividad

_Facundo · 28 jul 2026_

---

## 1. Diagnóstico

### Lo que encontré

**Notion — está bien, es tu sistema fuerte.**
Contiene todo el material del curso: `📊 PROGRAMACIÓN 1 2026`, semanas 1 a 12, `📝 Sistema de Evaluación`, `🎯 Proyectos Ejemplo`, `Main dashboard`. Estructura coherente y mantenida. No hay que tocar mucho acá.

**Google Drive — este es el desorden real.**
Todo vive en la raíz de Mi Unidad, mezclado:

- Instaladores y basura: `OBS Bridge-0.1.2-x64.exe`, `OBS Bridge-0.1.3-x64.exe`, `wetransfer_untitled-transfer_2026-07-06(1).zip`
- **Duplicados de finanzas**: `Registro gastos` y `Registro_gastos_Facundo` (dos planillas del mismo tema) + `Registro de gasto - Form`
- **Duplicados de dashboard**: `Dashboard_v2.xlsx` y `Dashboard_v2` (Sheet) — mismo archivo, dos formatos
- Material docente suelto en la raíz: `2026_LD_Programación_1.docx`, `2026_LD_Programación_1_Especial.docx`
- Lo único ordenado: carpeta `Correccion P1 2026` (rúbrica + parcial adentro) ✅

**Apple Notes + Recordatorios — sin auditar.**
Requiere permiso de Accesibilidad en Claude (Ajustes del sistema → Privacidad y seguridad → Accesibilidad). Si lo habilitás, completo esta sección.

### El problema de fondo

No es que tengas desorden dentro de cada app. Es que **no hay una regla que diga qué va en cada app**. Cuando aparece algo nuevo, lo tirás donde caiga. Eso explica los duplicados y la raíz de Drive.

---

## 2. Roles por app

Una regla por app. Si algo no encaja en ninguna, es señal de que sobra la app.

| App | Rol único | Ejemplo |
|---|---|---|
| **Recordatorios (Apple)** | **Acciones con fecha.** Todo lo que tiene un "hacer" y un "cuándo". | "Corregir parciales antes del 12/8" |
| **Notas (Apple)** | **Bandeja de entrada efímera.** Captura rápida en el celular. Se vacía semanalmente. | Idea suelta en el bus, número de teléfono |
| **Notion** | **Referencia y proyectos.** Lo que consultás o construís a lo largo del tiempo. | Curso, clases, plan de proyectos |
| **Drive** | **Archivos, no conocimiento.** Solo lo que tiene que ser un archivo (docx, xlsx, PDFs, entregas). | Rúbricas, planillas, entregas de alumnos |
| **Calendario** | **Compromisos con hora fija.** Solo cosas con horario. Nunca tareas. | Clases, reuniones |

**La regla de oro:** Notas es un buzón, no un archivo. Nada vive ahí más de 7 días.

---

## 3. Estructura a implementar

### Recordatorios — 4 listas, no más

```
📥 Inbox        → captura rápida, se procesa al vaciar Notas
🎓 Docencia     → corrección, preparación de clases, admin académica
💻 Proyectos    → OBS Bridge y otros dev
🏠 Personal     → finanzas, trámites, casa
```

Todo con fecha. Si no tiene fecha, no es un recordatorio: es una nota o un proyecto de Notion.

### Notas (Apple) — 1 carpeta

```
📥 Inbox        → única carpeta. Todo entra acá.
```

Semanalmente cada nota sale hacia: un recordatorio, una página de Notion, un archivo de Drive, o la basura. Sin excepción.

### Notion — dos áreas de nivel superior

```
🎓 Docencia
   └─ 📊 PROGRAMACIÓN 1 2026  (ya existe, dejar igual)
      ├─ SEMANA 1 … 12
      ├─ 📝 Sistema de Evaluación
      └─ 🎯 Proyectos Ejemplo

🧭 Personal
   ├─ Main dashboard  (mover acá)
   ├─ Proyectos activos
   └─ Notas de referencia
```

Cambio concreto: `Main dashboard` hoy está suelto. Que sea la portada de `🧭 Personal`.

### Drive — 5 carpetas y la raíz vacía

```
Mi unidad/
├─ 01 Docencia/
│   ├─ Programación 1 2026/     → los .docx de programa
│   └─ Correccion P1 2026/      → ya existe, mover acá dentro
├─ 02 Finanzas/                 → registro de gastos + form
├─ 03 Proyectos/
│   └─ OBS Bridge/
├─ 04 Compartido conmigo/       → Planilla madre, Software entrenamiento
└─ 99 Archivo/                  → cosas viejas que no querés borrar
```

**Limpieza inmediata (mover a Papelera):**

- `OBS Bridge-0.1.2-x64.exe` — versión vieja, ya está la 0.1.3
- `wetransfer_untitled-transfer_2026-07-06(1).zip` — transferencia sin nombre
- `Dashboard_v2.xlsx` — quedate solo con la versión Google Sheet

**Decisión pendiente:** `Registro gastos` (2025) vs `Registro_gastos_Facundo` (2026). Consolidá en una sola y archivá la otra. Tener dos garantiza que ninguna esté al día.

---

## 4. Mantenimiento — lo hace kraken, no el calendario

La primera versión de este plan ponía una "revisión de los viernes" como evento
de calendario. Estaba mal, y lo dice tu propio `ROUTER.md`:

> **Solo el asistente personal te interrumpe.** Si cada especialista te notifica,
> volvés a tener cinco lugares donde mirar.

Un evento de calendario es una segunda fuente de avisos. Y encima te interrumpe
todos los viernes aunque no haya nada acumulado. Así que esto vive en el brief.

### Ya implementado en `brief.py`

Un lector nuevo (`mirar_buzones`) cuenta lo que se acumuló en tus bandejas de
entrada y lo muestra **solo si cruzó un umbral**:

```
BUZONES SIN VACIAR
   Recordatorios · 📥 Inbox: 14 ítem(s), el más viejo de hace 23 día(s)
   Notas · 📥 Inbox: 11 ítem(s), el más viejo de hace 9 día(s)
```

Se configura en `[higiene]` de `config.local.toml`. Umbrales por defecto: 10
ítems o 7 días. Debajo de eso, silencio — un aviso que aparece todos los días
deja de leerse a la semana.

**Los recordatorios vencidos ya los tenías.** `vencidos_dias = 14` en tu config
los muestra hace rato. Ese paso del plan original sobraba.

### La frontera que respeta

Kraken **cuenta**; no mira qué hay adentro ni sugiere qué hacer con cada ítem.

- ✅ "El Inbox tiene 14 ítems, el más viejo de hace 3 semanas" → tu atención, su trabajo
- ❌ "Consolidá las dos planillas de gastos" → decisión de dominio, `ROUTER.md` se lo prohíbe

### Lo que queda manual

**Drive no entra.** Alcanzarlo significa OAuth y una credencial nueva para
avisar de algo que se limpia una vez. Es tu regla 4: *una capa que no le saca
trabajo a lo que ya existe es una capa de más*. La limpieza de la sección 3 es
un trabajo único, no un aviso recurrente.

**Vaciar los buzones también es tuyo.** Cuando el brief te avise, cada ítem va
a un recordatorio con fecha, a una página de Notion, a un archivo de Drive, o a
la basura.

---

## 5. Orden de ejecución

| # | Acción | Tiempo | Por qué primero |
|---|---|---|---|
| 1 | Limpiar Drive: borrar los 3 archivos + crear las 5 carpetas | 20 min | Impacto visible inmediato |
| 2 | Consolidar las dos planillas de gastos en una | 30 min | Es el duplicado más costoso |
| 3 | Crear las 4 listas de Recordatorios y reasignar lo existente | 20 min | Define el flujo diario |
| 4 | Colapsar carpetas de Notas en un solo Inbox | 15 min | Depende del paso 3 |
| 5 | Mover `Main dashboard` bajo `🧭 Personal` en Notion | 5 min | Cosmético, va al final |
| 6 | Correr `python brief.py --dry-run` y verificar que ve los buzones | 5 min | Ya está el código; falta que existan las carpetas con ese nombre exacto |

---

## Nota sobre qué NO hacer

No migres todo a una sola app. Notion es malo para tareas con fecha y Recordatorios es malo para conocimiento. El problema nunca fue tener cuatro apps — fue no tener una regla de qué va en cada una.
