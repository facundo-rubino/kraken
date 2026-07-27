#!/usr/bin/env python3
"""Prueba la lógica que NO depende de macOS: composición, huecos y la consulta
al experto en dirección. EventKit no se toca acá.

    python prueba_sin_mac.py [--state-dir RUTA]
"""
import argparse
import tomllib
from datetime import date, datetime, time
from pathlib import Path

import brief as B

ap = argparse.ArgumentParser()
ap.add_argument("--state-dir", default="")
args = ap.parse_args()

cfg = tomllib.loads((Path(__file__).parent / "config.toml").read_text())
if args.state_dir:
    cfg["direccion"]["state_dir"] = args.state_dir

HOY = date(2026, 7, 27)


def ev(t, h1, m1, h2, m2, cal="Personal", corp=False, todo=False):
    return B.Evento(
        titulo=t,
        inicio=None if todo else datetime.combine(HOY, time(h1, m1)),
        fin=None if todo else datetime.combine(HOY, time(h2, m2)),
        todo_el_dia=todo, calendario=cal, corporativo=corp)


b = B.Brief(hoy=HOY)
b.eventos = [
    ev("Daily del equipo", 9, 0, 9, 30, "Trabajo", corp=True),
    ev("Revisión de arquitectura con el decano", 10, 0, 11, 30, "Universidad", corp=True),
    ev("Gimnasio", 13, 0, 14, 15),
    ev("Clase Programación 1", 18, 0, 21, 0, "Universidad", corp=True),
    ev("Feriado puente", 0, 0, 0, 0, "Personal", todo=True),
]
b.recordatorios = [
    B.Recordatorio("Pagar la matrícula", date(2026, 7, 27), "Personal"),
    B.Recordatorio("Mandarle el temario a Nico", date(2026, 7, 20), "Trabajo", corporativo=True),
    B.Recordatorio("Renovar el seguro", date(2026, 7, 25), "Personal"),
]

print("=" * 68)
print("A) BRIEF NORMAL (Apple: iCloud / iMessage)")
print("=" * 68)
print(B.componer(b, cfg))

print("=" * 68)
print("B) MISMO BRIEF HACIA UN TERCERO (ntfy) — títulos corporativos redactados")
print("=" * 68)
print(B.componer(b, cfg, para_terceros=True))

print("=" * 68)
print("C) HUECOS LIBRES")
print("=" * 68)
for i, f in B.huecos_libres(b.eventos, cfg, HOY):
    print(f"  {i:%H:%M}–{f:%H:%M}")

print()
print("=" * 68)
print("D) CONSULTA AL EXPERTO EN DIRECCIÓN")
print("=" * 68)
dets, avisos = B.preguntar_direccion(cfg, HOY)
for d in dets:
    print(f"  {d.iniciativa}: [{d.tipo}] {d.detalle}")
for a in avisos:
    print(f"  aviso: {a}")
if not dets and not avisos:
    print("  (sin estado configurado)")

print()
print("E) RESUMEN (notificación):", B.resumen(b))
print("F) DÍA VACÍO:")
print(B.componer(B.Brief(hoy=HOY), cfg))
