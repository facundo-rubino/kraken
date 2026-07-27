---
name: kraken
description: Habla con kraken, el asistente personal del usuario — su día, tiempo libre, compromisos, qué necesita decisión y la lista de compras. Usala cuando pregunten por su agenda, sus huecos, cuánto tiempo tienen, qué falta comprar, o cuando digan que ya tienen un ingrediente. También para revisar el brief de la mañana o el de otro día.
---

# Kraken

El asistente personal del usuario. Vive en `~/projects/kraken` y **ya sabe leer su
calendario, sus recordatorios y consultar a los especialistas**. Tu trabajo acá es
traducir lo que te pide a los comandos que ya existen — no reimplementes nada.

## Antes que nada

```bash
cd ~/projects/kraken
```

Todos los comandos se corren con `.venv/bin/python` (el venv tiene EventKit y
`pm_assistant` instalados; el `python3` del sistema **no sirve**, es 3.9).

## Qué te puede pedir y qué correr

| Te dice | Corré |
|---|---|
| "¿qué tengo hoy?", "¿cómo viene el día?" | `.venv/bin/python brief.py --dry-run` |
| "¿cuánto tiempo libre tengo?" | lo mismo — la línea `LIBRE` lo dice |
| "¿qué tengo el lunes?" | `.venv/bin/python brief.py --dry-run --hoy AAAA-MM-DD` |
| "¿qué falta comprar?" | `.venv/bin/python compras.py falta` |
| "agregá lo que falta a la lista" | `.venv/bin/python compras.py sincronizar` |
| "ya tengo leche" / "compré el arroz" | `.venv/bin/python compras.py tengo "leche"` |
| "mostrame la lista de compras" | `.venv/bin/python compras.py lista` |
| "¿por qué no me llegó el brief?" | `cat brief.log` |
| "mandámelo ahora" | `launchctl start personal.kraken.brief` |

`--dry-run` imprime y **no entrega nada** — usalo siempre para consultas. Sin esa
bandera, `brief.py` le manda un iMessage al usuario, cosa que no querés al responder
una pregunta.

## Cómo contestar

**Leé la salida y contestá en lenguaje normal.** No pegues el brief crudo si te
preguntaron una sola cosa: si preguntó cuánto tiempo libre tiene, contestale las
horas y los bloques, no las seis secciones.

Secciones del brief y qué significan:

| Sección | Qué es |
|---|---|
| `AGENDA` | Eventos del calendario. El `·` marca calendario corporativo |
| `FIJO` | Oficina y clases — no son eventos, están declarados en el config |
| `SIN OFICINA` | Un feriado o licencia canceló los fijos de ese día |
| `LIBRE` | Lo que queda después de descontar eventos **y** fijos |
| `MAÑANA` | Solo aparece si mañana hay algo; avisa si arranca más temprano de lo habitual |
| `NECESITA DECISIÓN` | Lo detectó el project manager (`pm-assistant`), no kraken |
| `COCINA` | Del chef. Hoy suele estar apagada |
| `EL BRIEF NO PUDO VER TODO` | **Una fuente falló.** Decíselo, no lo escondas |

## Reglas

1. **Nunca inventes su agenda.** Si un comando falla o no devuelve nada, decilo.
   Un brief vacío puede ser un día libre o un permiso de macOS denegado, y no es lo
   mismo: mirá si apareció `EL BRIEF NO PUDO VER TODO`.
2. **`compras.py tengo` es interactivo si hay ambigüedad.** Si "leche" coincide con
   varios ítems, pregunta cuál. Pasale la respuesta o usá `--si` para que saque todos.
   Si no coincide con nada, **no toca nada** — avisale.
3. **Kraken no decide nada.** Si te pide una opinión de un dominio —qué entrenar, qué
   cocinar, cómo planificar un proyecto— eso es del especialista, no de kraken. El
   mapa está en `ROUTER.md`.
4. **La config real es `config.local.toml`**, no `config.toml` (que es plantilla y
   está versionada en un repo público). Si te pide cambiar horarios, calendarios
   corporativos o compromisos fijos, editá la local.
5. **Después de tocar `brief.py` o `compras.py`**, corré `.venv/bin/python pruebas.py`.

## Cambios que te va a pedir seguido

**Horarios fijos** (oficina, clases) → `config.local.toml`, sección `[[fijos]]`:

```toml
[[fijos]]
nombre = "Clases"
dias = ["lu", "mi"]
desde = "18:00"
hasta = "21:30"
desde_fecha = "2027-03-01"    # opcional, para lo estacional
hasta_fecha = "2027-06-30"
```

**Hora del brief** → `HORA_BRIEF=8 ./instalar.sh ~/projects/pm-assistant`

**Canales de entrega** → `[entrega] canales` en `config.local.toml`.
`ntfy` es un servicio de terceros: los títulos de calendarios corporativos se
redactan antes de salir, salvo que `perimetro_en_push = true`.
