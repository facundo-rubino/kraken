# El mapa

Un **asistente personal** para la vida. Cuando el tema es de un especialista, le pregunta al especialista.

```
        vos
         │
   asistente personal ──── lee tu calendario y recordatorios
         │                 arma el brief de la mañana
         │                 es el ÚNICO que te interrumpe
         │
    ┌────┴────┬──────────┬─────────┐
    │         │          │         │
 project    coach      chef     docente
 manager   fitness
```

Eso es todo. El resto de este archivo existe solo para resolver dudas de "¿esto de quién es?".

---

## Quién sabe de qué

| | Sabe de | NO sabe de |
|---|---|---|
| **Asistente personal** | Tu tiempo, tu día, qué necesita tu atención | Nada de ningún dominio. No decide, no opina |
| **Project manager** | Planificar, fechas, dependencias, replanificar cuando algo se cae, cerrar bien | El contenido de nada |
| **Coach fitness** | Mesociclos, cargas, RPE, progresión | Cuándo entrenás — eso es tu calendario |
| **Chef** | Recetas, Cookidoo, qué cocinar, qué falta comprar | Nutrición prescriptiva: es del coach |
| **Docente** | Temario, clases, evaluaciones | Fechas del semestre: son del PM |

## La única regla que necesitás

> **¿Esto sería verdad para cualquier tema, o solo para éste?**
>
> Para cualquiera → **project manager**. Solo para éste → **el especialista**.

- "El mesociclo dura 6 semanas y la 4ª es descarga" → la *forma* es del PM, la *plantilla* es del coach.
- "El parcial es el 15 de junio" → PM. "Qué se enseña en la semana 7" → docente.

## Tres límites que no se tocan

1. **Solo el asistente personal te interrumpe.** Si cada especialista te notifica, volvés a tener cinco lugares donde mirar.
2. **Nadie prescribe donde puede hacer daño.** Ni consejo financiero ni prescripción médica. El coach de verdad es una persona, no el sistema.
3. **Del calendario del trabajo se lee título y horario. Nada más.** Ni cuerpos, ni invitados, ni adjuntos.

## Dónde vive cada cosa

```
~/experts/                  teaching-kb · fitness-kb · cooking-kb   (un repo cada uno)
~/projects/orquestador      este repo — el asistente personal
~/projects/pm-assistant     el project manager
~/projects/direction-state  tus iniciativas reales (fuera del vault de Obsidian)
```

Obsidian abierto sobre `~/experts/` te deja leerlos y editarlos como un todo, desde el iPhone también.

## Reglas para no volver a marear

1. **Un especialista nuevo recién cuando dos cosas reales lo pidan.** Doce carpetas vacías es el fracaso, no el objetivo.
2. **Un especialista arranca siendo notas.** Se vuelve programa solo cuando tiene que *hacer* algo.
3. **Esto no lleva constitución, ni specs, ni ADRs.** Si necesita eso, creció de más.
4. **Una capa nueva que no le saca trabajo a lo que ya existe es una capa de más.**

---

*El detalle de por qué el project manager no lee ni avisa está en `pm-assistant/DECISIONS.md` (D29, D30). No hace falta leerlo para usar esto.*
