# Contexto — dónde estamos

> Escrito el 2026-07-27 al cerrar la sesión donde nació kraken.
> **Leé esto primero.** Es autosuficiente: no necesitás la conversación anterior.

---

## De dónde viene esto

Existía `pm-assistant`: un asistente de project management que fue absorbiendo todo
lo que no tenía otro lugar — conocimiento docente, plantillas de entrenamiento,
ambiciones de leer calendarios. Terminó con **84 documentos y 8.653 líneas** de
documentación para lo que en el fondo era un asistente personal.

El diagnóstico: el problema **no era pm-assistant**. Su propia constitución ya
prohibía todo eso (P0, P1, P5, P12). El problema era que **no había vecinos** donde
poner las otras cosas, y el único contenedor bien construido se comía todo.

**Kraken es el vecino que faltaba.**

## Qué es kraken

Tu asistente personal. Lee tu tiempo, le pregunta a los especialistas, y es lo
único con permiso de interrumpirte. El mapa completo está en [ROUTER.md](ROUTER.md)
— una página, se lee en un minuto.

## Estado real, sin maquillaje

| Pieza | Dónde | Estado |
|---|---|---|
| **Kraken** (asistente personal) | este repo | Código escrito y probado hasta donde se puede sin macOS. **Nunca corrió en la Mac.** |
| **Project manager** | `pm-assistant` | Funciona. 138 tests. **Congelado a propósito** |
| **Docente** | `teaching-kb` | Existe. Skills adentro (`.claude/skills/`) |
| **Coach fitness** | — | **No existe.** Vive dentro de AnkoFit |
| **Chef** | asistente Cookidoo | Existe como asistente; sin KB propio |

## El único paso siguiente

**Poner el brief a andar en la Mac y usarlo una semana.** Nada más.

```bash
cd ~/projects/kraken
cp config.toml config.local.toml     # editá config.local.toml, no config.toml
./experts.sh
./instalar.sh ~/projects/pm-assistant
```

`instalar.sh` te frena si la primera corrida no ve tu agenda real. Es a propósito.

Si el brief te despierta con tu día bien armado cinco mañanas seguidas, el
ecosistema está vivo y recién ahí se decide qué sigue. Si no lo usás, nada de lo
demás importaba.

## Qué está deliberadamente parado

No son pendientes olvidados: son decisiones de **no hacer** hasta que el brief se use.

- **Spec 002 de pm-assistant** (planificación / replanificación). Iba a ser otro
  ciclo de premisas, schemas y evals. Parado.
- **Migrar `GOAL.md` + `project/` de teaching-kb** a `direction-state`. Ese repo
  tiene una segunda implementación completa de la capa de dirección, hecha por
  Codex. Es evidencia de que la arquitectura es correcta, no un incendio. Se migra
  **después** de que exista Spec 002, no antes.
- **Separar el coach de AnkoFit.** Cuando pase: se parte en `reglas/` (lo posee el
  entrenador, es compartible) y `datos/` (tu salud, nunca sale). Sin esa partición
  no se puede delegar.
- **Chef con Cookidoo.** `compras.py` ya está; falta que algo escriba el
  `plan-comidas.yaml`.

## Lo que no hay que volver a hacer

1. **Un especialista nuevo recién cuando dos cosas reales lo pidan.**
2. **Un especialista arranca siendo notas.** Programa solo cuando tiene que *hacer*.
3. **Kraken no lleva constitución, ni specs, ni ADRs.** Si los necesita, creció de más.
4. **Una capa que no le saca trabajo a lo que ya existe es una capa de más.**

## Cosas que hay que saber antes de tocar código

- **Este repo es público.** Tu configuración real va en `config.local.toml`, que
  está en `.gitignore`. `config.toml` es plantilla con placeholders.
- **Lo de EventKit nunca corrió.** Calendario, Recordatorios, iMessage, iCloud y
  launchd están escritos contra la API de Apple pero **sin probar** — este trabajo
  se hizo en Linux. Lo probado: composición del brief, huecos libres, redacción de
  perímetro, matching de ingredientes, parser del plan y la consulta a pm-assistant.
- **TCC + launchd te va a morder.** Correrlo a mano concede permisos a Terminal;
  cuando launchd lo dispara, macOS puede negarlos sin nadie para aceptar. Está
  documentado en el README con la solución.
- **`pm-assistant` es privado**, aunque `direction-state/README.md` diga lo
  contrario. Esa nota está desactualizada y justificaba que `direction-state` no
  tuviera remote.

## Decisiones que valen y dónde están

Las dos que explican por qué el project manager no lee ni avisa:

- **D29** — perímetro de kraken: del calendario corporativo solo título, horario y
  duración. Nada de cuerpos, invitados ni adjuntos.
- **D30** — `pm-assistant` es un especialista, no la capa transversal.

Están en `pm-assistant/DECISIONS.md`. **No hace falta leerlas para usar kraken.**
