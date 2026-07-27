# Orquestador personal — brief diario

Primera pieza de la capa de orquestación descrita en `ROUTER.md` (hoy en el repo
`pm-assistant`, se muda acá cuando esto crezca).

Hace **una sola cosa**: cada mañana lee tu tiempo, le pregunta a los expertos qué
detectaron, y te lo manda al teléfono. Nada más.

## Instalación

```bash
chmod +x instalar.sh
./instalar.sh ~/projects/pm-assistant     # la ruta es opcional
```

El instalador te frena si la primera corrida no ve tu agenda real. Es a propósito:
un brief programado que no ve el calendario es peor que no tener brief.

Después, editá `config.toml` (calendarios a ignorar, cuáles son corporativos,
canales de entrega). **No edites `brief.py` para configurar.**

## Qué hace, en orden

| Paso | Qué | Dónde |
|---|---|---|
| 1. Leer | Calendario y Recordatorios de hoy, vía EventKit | `leer_calendario`, `leer_recordatorios` |
| 2. Preguntar | `pm-assistant`: compromisos vencidos, hitos, zombis, fechas próximas | `preguntar_direccion` |
| 3. Componer | Texto plano, determinístico | `componer` |
| 4. Entregar | iCloud Drive + iMessage (default) | `entregar` |

**No llama a ningún modelo.** Es determinístico, instantáneo y gratis. Si algún día
querés prosa en vez de listas, eso es un paso aparte y opcional — no el default.

## Las reglas que este código hace cumplir

**El experto detecta; el orquestador avisa.** `preguntar_direccion` *le pregunta* a
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
| Lectura de EventKit (calendario y recordatorios) | **Sin probar** — necesita macOS |
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

## Lo que este orquestador NO hace, y no debería

- No decide nada. No aprueba nada. No escribe en ninguna fuente.
- No guarda estado de iniciativas: eso es del experto en dirección.
- No sabe de fitness, cocina ni pedagogía: eso es de cada experto.
- No tiene constitución ni specs. Si algún día las necesita, creció de más.
