#!/usr/bin/env python3
"""Pruebas de kraken. Sin dependencias: corre con cualquier Python 3.12+.

    python pruebas.py                    # todo
    python pruebas.py --ver              # además imprime los briefs

No toca EventKit ni Recordatorios: prueba la lógica que decide qué te muestra
el brief. Lo de macOS solo se puede probar en la Mac.
"""
from __future__ import annotations

import sys
import tomllib
from datetime import date, datetime, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brief as B          # noqa: E402
import compras as C        # noqa: E402

VER = "--ver" in sys.argv
CFG = tomllib.loads((Path(__file__).parent / "config.toml").read_text(encoding="utf-8"))

fallos: list[str] = []
corridas = 0


def check(nombre: str, condicion: bool, detalle: str = "") -> None:
    global corridas
    corridas += 1
    if not condicion:
        fallos.append(f"{nombre}{' — ' + detalle if detalle else ''}")


def ev(t, h1, m1, h2, m2, dia=date(2026, 7, 28), cal="Personal", corp=False, todo=False,
       fin_dia=None):
    return B.Evento(
        titulo=t,
        inicio=None if todo else datetime.combine(dia, time(h1, m1)),
        fin=None if todo else datetime.combine(fin_dia or dia, time(h2, m2)),
        todo_el_dia=todo, calendario=cal, corporativo=corp)


def libre_min(b: B.Brief) -> int:
    return sum(int((f - i).total_seconds() // 60)
               for i, f in B.huecos_libres(b.eventos, CFG, b.hoy, b.fijos))


def brief_de(dia: date, eventos=None, cfg=CFG) -> B.Brief:
    b = B.Brief(hoy=dia)
    b.eventos = eventos or []
    motivo = B.anulan_fijos(cfg, b.eventos)
    b.anula_fijos = motivo
    b.fijos = [] if motivo else B.bloques_fijos(cfg, dia)
    if VER:
        print(B.componer(b, cfg))
    return b


# ── compromisos fijos ────────────────────────────────────────────────────────

MARTES, SABADO = date(2026, 7, 28), date(2026, 8, 1)

b = brief_de(MARTES)
check("martes: oficina en dos bloques", len(b.fijos) == 2, f"hay {len(b.fijos)}")
check("martes: 6 h libres (almuerzo + tarde)", libre_min(b) == 360, f"{libre_min(b)} min")

b = brief_de(SABADO)
check("sábado: sin fijos", b.fijos == [])
check("sábado: 14 h libres", libre_min(b) == 840, f"{libre_min(b)} min")

b = brief_de(MARTES, [ev("Daily", 9, 0, 9, 30, cal="Trabajo", corp=True)])
check("reunión dentro de oficina no descuenta dos veces", libre_min(b) == 360,
      f"{libre_min(b)} min")

b = brief_de(MARTES, [ev("Cena", 20, 0, 21, 0)])
check("evento fuera de oficina sí descuenta", libre_min(b) == 300, f"{libre_min(b)} min")

# ── solapamiento: un mandado dentro del trabajo no suma horas ────────────────

def comprometido(b, cfg=CFG):
    return sum(int((f - i).total_seconds() // 60)
               for i, f in B.ocupado_fusionado(b.eventos, cfg, b.hoy, b.fijos))

SIN_FIJOS = {**CFG, "fijos": []}
b = B.Brief(hoy=MARTES)
b.eventos = [ev("Trabajo", 8, 0, 16, 0, cal="Trabajo", corp=True),
             ev("Cambio de filtro", 12, 30, 13, 30)]
check("mandado dentro del trabajo no duplica", comprometido(b, SIN_FIJOS) == 480,
      f"{comprometido(b, SIN_FIJOS)} min")

b2 = B.Brief(hoy=MARTES)
b2.eventos = [ev("Trabajo", 8, 0, 16, 0), ev("Cena", 20, 0, 21, 0)]
check("evento fuera sí suma", comprometido(b2, SIN_FIJOS) == 540,
      f"{comprometido(b2, SIN_FIJOS)} min")

b3 = B.Brief(hoy=MARTES)
b3.eventos = [ev("A", 9, 0, 11, 0), ev("B", 10, 0, 12, 0)]
check("solapamiento parcial se fusiona", comprometido(b3, SIN_FIJOS) == 180,
      f"{comprometido(b3, SIN_FIJOS)} min")

# ── ventana estacional (clases marzo-junio) ──────────────────────────────────

CFG2 = tomllib.loads((Path(__file__).parent / "config.toml").read_text(encoding="utf-8"))
CFG2.setdefault("fijos", []).append({
    "nombre": "Clases", "dias": ["lu", "mi"], "desde": "18:00", "hasta": "21:30",
    "desde_fecha": "2027-03-01", "hasta_fecha": "2027-06-30"})

b = brief_de(date(2027, 5, 5), cfg=CFG2)          # miércoles de mayo
check("mayo 2027: clases activas", len(b.fijos) == 3, f"{len(b.fijos)} bloques")
check("mayo 2027: solo 2 h libres", libre_min(b) == 120, f"{libre_min(b)} min")

b = brief_de(date(2027, 2, 3), cfg=CFG2)          # miércoles de febrero
check("febrero 2027: fuera de temporada", len(b.fijos) == 2, f"{len(b.fijos)} bloques")
check("febrero 2027: vuelven las 6 h", libre_min(b) == 360, f"{libre_min(b)} min")

b = brief_de(date(2027, 5, 4), cfg=CFG2)          # martes: no hay clase
check("martes de mayo: sin clase", len(b.fijos) == 2, f"{len(b.fijos)} bloques")

# ── feriado anula los fijos ──────────────────────────────────────────────────

b = brief_de(MARTES, [ev("Feriado nacional", 0, 0, 0, 0, todo=True)])
check("feriado: sin oficina", b.fijos == [])
check("feriado: lo dice", b.anula_fijos == "Feriado nacional", str(b.anula_fijos))
check("feriado: 14 h libres", libre_min(b) == 840, f"{libre_min(b)} min")

b = brief_de(MARTES, [ev("Licencia anual", 0, 0, 0, 0, todo=True)])
check("licencia también anula", b.fijos == [])

b = brief_de(MARTES, [ev("Cumple de Ana", 0, 0, 0, 0, todo=True)])
check("un día completo cualquiera NO anula", len(b.fijos) == 2, f"{len(b.fijos)}")

# ── evento que cruza medianoche ──────────────────────────────────────────────

e = ev("Viaje", 22, 0, 9, 0, dia=date(2026, 8, 25), fin_dia=date(2026, 8, 26))
check("cruce de medianoche se marca", e.franja(date(2026, 8, 26)) == "←–09:00",
      e.franja(date(2026, 8, 26)))
check("evento normal se muestra igual",
      ev("X", 9, 0, 10, 0).franja(MARTES) == "09:00–10:00")

# ── perímetro corporativo (D29) ──────────────────────────────────────────────

b = brief_de(MARTES, [ev("Revisión con el decano", 10, 0, 11, 0,
                         cal="Universidad", corp=True)])
publico = B.componer(b, CFG, para_terceros=True)
check("hacia terceros se redacta el título", "decano" not in publico)
check("hacia terceros queda el horario", "10:00–11:00" in publico)
check("en el brief propio el título está", "decano" in B.componer(b, CFG))

# ── compras ──────────────────────────────────────────────────────────────────

check("leche encuentra 'Leche entera 1 L'", C.coincide("leche", "Leche entera 1 L"))
check("leche NO encuentra lechuga", not C.coincide("leche", "lechuga"))
check("acentos se ignoran", C.coincide("jamon", "Jamón cocido"))
check("ajo no encuentra ajos (conservador)", not C.coincide("ajo", "ajos"))

plan = Path("/tmp/_kraken_plan.yaml")
plan.write_text("2026-07-28:\n  - receta: Risotto\n    ingredientes: [arroz, hongos, arroz]\n",
                encoding="utf-8")
comidas, ing, avisos = C.ingredientes_de_hoy({"compras": {"plan_comidas": str(plan)}}, MARTES)
check("plan: lee la receta del día", len(comidas) == 1 and comidas[0].receta == "Risotto")
check("plan: deduplica ingredientes", ing == ["arroz", "hongos"], str(ing))
_, _, av = C.ingredientes_de_hoy({"compras": {"plan_comidas": "/tmp/no-existe.yaml"}}, MARTES)
check("plan ausente avisa, no explota", bool(av))
plan.unlink(missing_ok=True)

# ── buzones de captura ───────────────────────────────────────────────────────

def buzon(items, dias=None):
    return B.Buzon(nombre="X", items=items, dias_mas_viejo=dias)


check("buzón vacío nunca habla", not buzon(0).merece_aviso(10, 7))
check("buzón vacío calla aunque el umbral sea 0", not buzon(0, 99).merece_aviso(0, 7))
check("pocos ítems y recientes: silencio", not buzon(3, 2).merece_aviso(10, 7))
check("cruza por cantidad", buzon(10, 1).merece_aviso(10, 7))
check("cruza por antigüedad aunque haya poco", buzon(1, 7).merece_aviso(10, 7))
check("sin fecha del más viejo, decide la cantidad", buzon(12).merece_aviso(10, 7))
check("sin fecha y pocos ítems: silencio", not buzon(2).merece_aviso(10, 7))
check("umbral de días en 0 desactiva ese criterio",
      not buzon(2, 400).merece_aviso(10, 0))

# La sección no existe → la fuente no se mira y no se inventan avisos.
check("sin [higiene] no hace nada", B.mirar_buzones({}, MARTES) == ([], []))
check("[higiene] apagada no hace nada",
      B.mirar_buzones({"higiene": {"en_brief": False}}, MARTES) == ([], []))
check("[higiene] encendida sin fuentes no explota",
      B.mirar_buzones({"higiene": {"en_brief": True, "inbox_recordatorios": "",
                                   "inbox_notas": ""}}, MARTES) == ([], []))

b = brief_de(MARTES)
b.buzones = [buzon(14, 23)]
texto = B.componer(b, CFG)
check("el buzón se muestra con cantidad y antigüedad",
      "14 ítem(s), el más viejo de hace 23 día(s)" in texto)
check("el buzón entra en el resumen", "14 sin clasificar" in B.resumen(b))
check("sin buzones no aparece la sección",
      "BUZONES" not in B.componer(brief_de(MARTES), CFG))

# ── resultado ────────────────────────────────────────────────────────────────

print()
if fallos:
    print(f"FALLARON {len(fallos)} de {corridas}:")
    for f in fallos:
        print(f"  ✗ {f}")
    sys.exit(1)
print(f"OK — {corridas} pruebas")
