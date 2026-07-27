# Kraken

La capa de arriba del ecosistema. Lee tu tiempo, le pregunta a los expertos, y es
**lo único con permiso de interrumpirte**.

Empezá por **[CONTEXTO.md](CONTEXTO.md)** si venís nuevo, y **[PLAN.md](PLAN.md)** para saber qué sigue.

Acá vive también el **[ROUTER.md](ROUTER.md)**: el contrato de fronteras del
ecosistema — quién posee qué y, sobre todo, **qué no posee cada uno**. Si no sabés
dónde va algo, se resuelve ahí.

| Pieza | Qué hace |
|---|---|
| `brief.py` | El brief de la mañana: agenda, huecos libres, recordatorios, qué necesita decisión, qué falta comprar |
| `compras.py` | Lista de compras: diff entre las recetas de hoy y Recordatorios |
| `experts.sh` | Arma `~/experts/` con un repo por experto + vault de Obsidian encima |
| `ROUTER.md` | Fronteras del ecosistema |

## Instalación

**Requiere Python 3.12+.** El `python3` del sistema en macOS es 3.9 y no sirve:
`brief.py` usa `tomllib` (3.11+) y `pm-assistant` exige 3.12. `instalar.sh` busca uno
válido solo y falla con instrucciones si no lo encuentra (`brew install python@3.12`,
o pasale `PYTHON=/ruta/a/python3.12`).

```bash
# 1. Los expertos y el vault de Obsidian
chmod +x experts.sh instalar.sh
./experts.sh

# 2. El brief diario
./instalar.sh ~/projects/pm-assistant     # la ruta es opcional
```

## Obsidian sobre `~/experts/`

`experts.sh` deja un vault listo sobre la carpeta madre. Abrí Obsidian →
*Open folder as vault* → `~/experts`.

Qué te da, sin escribir una línea de código: búsqueda y **backlinks entre expertos**
(una regla de fitness citando una receta, una decisión docente citando una fecha del
plan), vista de grafo del ecosistema, y edición desde el iPhone sobre el mismo
archivo que versiona git.

**Por qué Obsidian no necesita la decisión de gobernanza que Notion sí necesitó:**
Obsidian *abre el archivo*, Notion *lo copia*. No hay segunda versión que gobernar.
Un conflicto acá es un archivo sin commitear, no una verdad paralela.

**Dónde no va:** el estado de dirección (`~/projects/direction-state`) queda **fuera
del vault**. Se valida contra `iniciativa.v1.json` y Obsidian te dejaría romperlo sin
avisar. Editor de conocimiento sí; editor de estado validado no.

El instalador te frena si la primera corrida no ve tu agenda real. Es a propósito:
un brief programado que no ve el calendario es peor que no tener brief.

Después, editá `config.toml` (calendarios a ignorar, cuáles son corporativos,
canales de entrega). **No edites `brief.py` para configurar.**

## Qué hace, en orden

| Paso | Qué | Dónde |
|---|---|---|
| 1. Leer | Calendario y Recordatorios de hoy, vía EventKit | `leer_calendario`, `leer_recordatorios` |
| 2. Preguntar | `pm-assistant`: compromisos vencidos, hitos, zombis, fechas próximas | `preguntar_direccion` |
| 2b. Preguntar | cocina: qué se cocina hoy y qué falta comprar | `preguntar_cocina` |
| 3. Componer | Texto plano, determinístico | `componer` |
| 4. Entregar | iCloud Drive + iMessage (default) | `entregar` |

## Compromisos fijos

Lo que estructura tu semana y **no vive como eventos en el calendario** —el horario
de oficina, las clases— se declara en `config.local.toml` y se descuenta de los huecos
libres igual que un evento. Sin esto el brief diría "13 h libres" todos los días.

```toml
[[fijos]]
nombre = "Oficina"
dias = ["lu", "ma", "mi", "ju", "vi"]
desde = "08:00"
hasta = "12:45"          # partido en dos para que el almuerzo sea hueco real
```

Para lo estacional —dar clase solo de marzo a junio— agregá `desde_fecha` y
`hasta_fecha`. Fuera de esa ventana el bloque no aplica y los huecos vuelven solos.

Esto es la **capacidad declarada** que el experto en dirección va a recibir cuando
exista la Spec 002: kraken la calcula, el planificador planifica sobre ella.

## Lista de compras (`compras.py`)

```bash
python compras.py falta               # qué falta para cocinar hoy
python compras.py sincronizar         # agrega a Recordatorios lo que falta
python compras.py tengo "leche"       # "ya tengo leche" → lo saca de la lista
python compras.py lista               # la lista tal cual está
```

**La lista canónica es Recordatorios de Apple** — es donde vas a mirar en el súper.
Cookidoo es de dónde salen los ingredientes, no dónde vive la lista.

**El experto en cocina escribe el plan; este script solo hace el diff y escribe la
lista.** No elige recetas, no sustituye ingredientes, no opina de nutrición.
Contrato (`plan_comidas` en `config.toml`):

```yaml
2026-07-28:
  - receta: Risotto de hongos
    ingredientes: [arroz arborio, hongos, caldo de verduras, manteca, parmesano]
  - receta: Ensalada tibia
    ingredientes: [espinaca, nueces, queso de cabra]
```

**`tengo` nunca adivina.** Si "leche" coincide con un solo ítem, lo saca y te dice
cuál. Si coincide con varios, te los lista y pregunta. Si no coincide con nada, lo
dice y no toca nada. El matching es conservador a propósito: `leche` sí encuentra
`Leche entera 1 L` pero no `lechuga`; `ajo` **no** encuentra `ajos` (singular/plural
no se resuelve — preferible no borrar de más).

**No llama a ningún modelo.** Es determinístico, instantáneo y gratis. Si algún día
querés prosa en vez de listas, eso es un paso aparte y opcional — no el default.

## Las reglas que este código hace cumplir

**El experto detecta; kraken avisa.** `preguntar_direccion` *le pregunta* a
`pm-assistant` importando su API de Python. El experto nunca empuja ni notifica.
Cuando sumes el experto docente o el de fitness, se agregan como funciones
hermanas — no como agentes que te escriben por su cuenta.

**Perímetro (D29).** De calendarios y listas marcados `corporativos` en
`config.toml` se leen **solo título, horario y duración**. Notas, ubicación,
invitados, adjuntos y URL no se filtran después: no entran nunca al proceso.
El estado de dirección corporativo está deliberadamente fuera de alcance.

**Terceros.** Si activás `ntfy`, los títulos corporativos se redactan a
"Reunión (Trabajo)" antes de salir de Apple. D29 permite esos títulos *en el
brief*; que salgan del ecosistema es otra decisión, y su default es "no".
Se cambia con `perimetro_en_push = true`, a sabiendas.

**Degradación honesta.** Si una fuente falla, el brief sale igual con una sección
`EL BRIEF NO PUDO VER TODO`. Nunca te muestra un día vacío fingiendo que no pasa nada.

## Entrega

| Canal | Llega a | Terceros |
|---|---|---|
| `archivo_icloud` | app Archivos del iPhone (`hoy.md`) | no |
| `imessage` | notificación en iPhone, Watch y Mac | no |
| `notificacion_mac` | solo el Mac, solo el resumen | no |
| `ntfy` | push vía ntfy.sh | **sí** |

Default: `["archivo_icloud", "imessage"]` — todo dentro de Apple.

## Probar sin macOS

```bash
python prueba_sin_mac.py --state-dir ~/projects/direction-state
```

Ejercita composición, cálculo de huecos, redacción de perímetro y la consulta al
experto con datos de ejemplo. **No toca EventKit**, así que corre en cualquier lado.

## Estado de verificación

| Parte | Estado |
|---|---|
| Composición, huecos libres, redacción de perímetro | **Probado** |
| Consulta al experto en dirección | **Probado** contra el estado real de `pm-assistant` |
| Matching de ingredientes, parser del plan, diff de compras | **Probado** (9 casos de matching + parser + dedup) |
| Sección COCINA dentro del brief | **Probado** con la lista mockeada |
| Lectura de EventKit (calendario y recordatorios) | **Sin probar** — necesita macOS |
| Escritura en Recordatorios (agregar / quitar) | **Sin probar** — necesita macOS |
| Entrega (iMessage, iCloud, notificación) | **Sin probar** — necesita macOS |
| launchd | **Sin probar** — necesita macOS |

Lo de EventKit y la entrega se escribió a ciegas contra la API de Apple. La
primera corrida de `./instalar.sh` es la prueba real, y por eso te obliga a
confirmar que viste tu agenda antes de programar nada.

## Fricción conocida de macOS

**TCC y launchd.** Correrlo a mano desde Terminal concede permisos a Terminal.
Cuando launchd lo dispara, el proceso responsable es otro y macOS puede volver a
pedir acceso — sin nadie para aceptar. Si el brief de la mañana llega con
`EL BRIEF NO PUDO VER TODO`, es esto. Solución: Configuración del Sistema →
Privacidad y seguridad → Calendarios / Recordatorios, y habilitá el binario
`.venv/bin/python` de esta carpeta. Vale la pena saberlo antes de que pase.

**El Mac tiene que estar despierto.** launchd con `StartCalendarInterval` dispara
al despertar si la hora pasó dormido, así que el brief puede llegarte tarde pero
no se pierde.

## Lo que este kraken NO hace, y no debería

- No decide nada. No aprueba nada. No escribe en ninguna fuente.
- No guarda estado de iniciativas: eso es del experto en dirección.
- No sabe de fitness, cocina ni pedagogía: eso es de cada experto.
- No tiene constitución ni specs. Si algún día las necesita, creció de más.
