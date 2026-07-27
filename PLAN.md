# Plan — qué sigue después de instalar kraken

## Contexto

El ecosistema está construido pero **nunca corrió**. `kraken` (asistente personal),
`pm-assistant` (project manager) y `teaching-kb` (docente) existen y están pusheados;
el coach y el chef todavía no. Todo lo que toca macOS —EventKit, iMessage, iCloud,
launchd— se escribió a ciegas desde Linux y está **sin probar**.

El modo de falla histórico de este proyecto está documentado (D26): diseñar entero
antes de usar nada. H1 de `pm-assistant` salió *invalidado* al primer uso real, después
de ~30 documentos de fundación. Este plan existe para no repetirlo: **una sola cosa a la
vez, con una puerta de decisión entre cada una.**

El criterio de éxito no es que el código funcione. Es que **lo uses**.

---

## Fase 0 — Día de instalación (~30 min)

```bash
cd ~/projects/kraken
cp config.toml config.local.toml     # editá ESTA, no config.toml
./experts.sh
./instalar.sh ~/projects/pm-assistant
```

**Editar en `config.local.toml` antes de instalar:**

| Campo | Qué poner |
|---|---|
| `identidad.apple_id` | Tu Apple ID real (el repo es público; `config.local.toml` está en `.gitignore`) |
| `calendario.corporativos` | Los nombres **exactos** de tus calendarios de trabajo |
| `calendario.ignorar` | Cumpleaños, feriados, sugerencias de Siri |
| `recordatorios.listas` | Vacío = todas |
| **`compras.en_brief = false`** | **Importante.** El chef no existe todavía; si lo dejás en `true`, cada brief va a traer un aviso de "no hay plan de comidas". Se prende en la Fase 2 |
| `direccion.state_dir` | `~/projects/direction-state` |

**Requisito: Python 3.12+.** El `python3` del sistema en macOS es 3.9 y no alcanza —
`brief.py` usa `tomllib` (3.11+) y `pm-assistant` exige 3.12. `instalar.sh` lo busca solo
(prueba `python3.14/13/12`, rutas de Homebrew, y `python3`) y **falla temprano con
instrucciones** si no hay ninguno, en vez de dejar un venv roto:

```bash
brew install python@3.12          # si no lo tenés
PYTHON=/ruta/a/python3.12 ./instalar.sh ~/projects/pm-assistant   # si está en otro lado
```

Si de un intento anterior quedó un venv con la versión equivocada, lo detecta y lo rehace.

`instalar.sh` corre un `--dry-run` y **te frena** si no confirmás que viste tu agenda
real. Es a propósito: un brief programado que no ve el calendario es peor que no tenerlo.

**Si el dry-run no ve nada:** es TCC. Configuración del Sistema → Privacidad y
seguridad → Calendarios / Recordatorios → habilitar Terminal. Volvé a correr.

---

## Fase 1 — La semana (7 días, cero trabajo)

Usalo. No lo toques. Lo único a observar, sin anotar nada:

1. **¿Llegó?** Si algún día no llegó, mirá `~/projects/kraken/brief.log`.
2. **¿Lo leíste?** No "lo abriste": lo leíste.
3. **¿Decía la verdad?** Especialmente los huecos libres y la sección `NECESITA DECISIÓN`.
4. **¿Apareció `EL BRIEF NO PUDO VER TODO`?** Eso es una fuente caída, no un bug del brief.

**Lo más probable que falle: TCC + launchd.** Correr a mano concede permisos a Terminal;
cuando launchd dispara, el proceso responsable es otro y macOS puede negar el acceso sin
nadie para aceptar. Síntoma: el brief llega pero con la sección de avisos. Solución en el
README — habilitar el binario `.venv/bin/python` de la carpeta en Privacidad y seguridad.

**Arreglos permitidos durante la semana:** solo los que impiden que el brief llegue o
que diga la verdad. Nada de features.

---

## La puerta — día 7

| Qué pasó | Qué significa | Qué hacer |
|---|---|---|
| Lo leíste ≥5 mañanas | El ecosistema está vivo | Seguir a Fase 2 |
| Llegaba pero no lo leías | El formato o el horario están mal, no la idea | Una iteración de contenido/hora. **No** agregar especialistas |
| No llegaba | Problema técnico | Arreglar entrega. Nada más hasta que llegue |
| Llegaba, lo leías, no servía | La hipótesis está mal | **Parar todo.** Discutir qué sí servía antes de construir nada |

El cuarto caso es el importante y es el que pasó con H1. Si aparece, la respuesta correcta
es parar, no arreglar.

---

## Fase 2 — El chef (recomendado; ~2 días)

**Por qué éste primero:** `compras.py` ya está escrito y probado. Solo falta que algo
produzca `~/experts/cooking-kb/plan-comidas.yaml`. Es la pieza más barata del ecosistema
y completa una sección del brief que hoy sale apagada.

1. Crear el repo `cooking-kb` y clonarlo en `~/experts/` (agregarlo a `REPOS` en `experts.sh`).
2. Que el asistente de Cookidoo escriba el plan semanal en el formato que `compras.py`
   ya parsea (documentado en su docstring):
   ```yaml
   2026-08-03:
     - receta: Risotto de hongos
       ingredientes: [arroz arborio, hongos, caldo de verduras]
   ```
3. Poner `compras.en_brief = true`.
4. Probar el ciclo completo: `compras.py falta` → `sincronizar` → `tengo "leche"`.

**Riesgo conocido:** el matching de ingredientes es conservador — `ajo` no encuentra
`ajos`. Prefiere no borrar de más. Si molesta en uso real, ahí se ajusta.

**Frontera:** el chef sabe de recetas. La nutrición prescriptiva es del coach. El plan de
comidas se queda en el chef y **no va al project manager** (P3, proporcionalidad).

---

## Fase 3 — El coach fitness (~1-2 semanas, involucra a otra persona)

Es la mejor razón de toda la arquitectura, y por eso es la que no hay que apurar.

1. **Separar de AnkoFit** a un repo `fitness-kb`.
2. **Partirlo en dos, sin excepción:**
   - `reglas/` — plantillas de mesociclo, progresiones, criterios, contraindicaciones.
     Genérico, compartible. **Lo posee el entrenador.**
   - `datos/` — tu peso, lesiones, marcas, historial. **Nunca sale.**
   Sin esta partición no se puede delegar sin entregar tu historial de salud.
3. **Camino de edición que el entrenador use de verdad.** No va a mandar un PR. Obsidian
   sobre una carpeta compartida, o Notion, y vos sincronizás. Si el camino tiene fricción,
   el KB muere en la v1 y volvés al punto de partida.
4. **AnkoFit pasa a consultar** `reglas/` en vez de contenerlas. Acá sí se justifica un
   servidor MCP local: es el único caso donde el consumidor es una app y no una conversación.

---

## Fase 4 — Spec 002 en pm-assistant (lo más caro; solo si duele)

Planificación y replanificación: el curso y el mesociclo como planes con ventana,
bloques, dependencias, peso y colchón. Premisas ya ratificadas (D27) en
`07-specs/spec-002-planificacion/premisas.md`.

**Disparador para retomarla — que se cumpla alguno:**
- Se te comprime el curso o el mesociclo y replanificar a mano duele de verdad.
- El brief te muestra `NECESITA DECISIÓN` sobre algo que no podés resolver sin un plan.

**Si no duele, no se escribe.** Es exactamente el ciclo de specs/schemas/evals que causó
el mareo. `teaching-kb` ya tiene evidencia de lo que el schema necesita
(`courses/programacion-1/SCHEDULE.md` y su "Criterio de ajuste" piden en prosa justo la
ventana y la capacidad que la spec define) — usarla como insumo cuando llegue el momento.

La migración de `GOAL.md` + `project/` de `teaching-kb` a `direction-state` va **después**
de esto, nunca antes.

---

## Lo que NO hay que hacer

1. **No agregar un especialista hasta que dos cosas reales lo pidan.** Doce carpetas
   vacías es el fracaso.
2. **No escribir constitución, specs ni ADRs para kraken.** Si los necesita, creció de más.
3. **No saltear la puerta del día 7.** Construir la Fase 2 sin haber usado la Fase 1 es
   repetir D26.
4. **No agregar LLM al brief.** Hoy es determinístico, gratis e instantáneo. La prosa es
   un paso opcional posterior, no el default.
5. **No mover `direction-state` dentro del vault de Obsidian.** Se valida contra schema y
   Obsidian lo dejaría romper sin avisar.

---

## Verificación

**Fase 0 (en la Mac):**
```bash
.venv/bin/python brief.py --dry-run          # ¿aparece tu agenda real?
launchctl start personal.kraken.brief         # ¿llega al teléfono?
cat brief.log                                 # ¿algún error?
```

**Fase 1:** que el brief llegue 5 de 7 mañanas y que lo leas.

**Fase 2:**
```bash
.venv/bin/python compras.py falta            # lista los ingredientes que faltan
.venv/bin/python compras.py sincronizar      # aparecen en Recordatorios
.venv/bin/python compras.py tengo "leche"    # lo saca y te dice cuál sacó
.venv/bin/python brief.py --dry-run          # aparece la sección COCINA
```

**Sin macOS (cualquier momento):**
```bash
.venv/bin/python prueba_sin_mac.py --state-dir ~/projects/direction-state
cd ~/projects/pm-assistant && python -m pytest -q     # 138 tests
```

---

## Decisiones que tomé por vos (ajustables)

- **Orden Fase 2 → 3 → 4: chef, coach, Spec 002.** Por costo creciente. El coach vale más
  que el chef, pero involucra a otra persona y una partición de KB; el chef son dos días
  sobre código ya escrito.
- **Sin medición formal durante la semana.** Un ritual diario de anotar es justo lo que
  mata estas cosas. Al día 7 decidís por sensación: ¿lo leíste?, ¿te sirvió?, ¿lo
  extrañaste el día que falló?
