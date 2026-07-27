#!/usr/bin/env python3
"""Lista de compras — puente entre el experto en cocina y Recordatorios.

    python compras.py falta                 # qué falta para cocinar hoy
    python compras.py sincronizar           # agrega a Recordatorios lo que falta
    python compras.py tengo "leche"         # "ya tengo leche" → lo saca de la lista
    python compras.py tengo "leche" --si    # sin preguntar (para uso no interactivo)
    python compras.py lista                 # muestra la lista tal cual está

La lista canónica es **Recordatorios de Apple** (es donde mirás en el súper).
Cookidoo es de dónde salen los ingredientes, no dónde vive la lista — una sola
fuente de verdad por tipo de contenido.

CONTRATO CON EL EXPERTO EN COCINA
---------------------------------
El experto escribe un archivo con lo que se cocina hoy. Este script lo lee y
NO decide nada de cocina: no elige recetas, no sustituye ingredientes, no opina
de nutrición. Solo hace el diff contra la lista y escribe.

    # plan-comidas.yaml  (lo produce el asistente de cocina)
    2026-07-28:
      - receta: Risotto de hongos
        ingredientes: [arroz arborio, hongos, caldo de verduras, manteca, parmesano]
      - receta: Ensalada tibia
        ingredientes: [espinaca, nueces, queso de cabra]

No hace falta YAML real: se parsea con el formato de arriba y nada más.
"""
from __future__ import annotations

import argparse
import re
import sys
import threading
import tomllib
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def config_por_defecto() -> Path:
    """`config.local.toml` si existe (tu config real, fuera de git); si no, la plantilla."""
    local = AQUI / "config.local.toml"
    return local if local.is_file() else AQUI / "config.toml"


# ─────────────────────────────────────────────────────────────── normalizar ──

def norm(s: str) -> str:
    """Para comparar 'Leche entera 1L' con 'leche' sin volverse loco."""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def coincide(consulta: str, item: str) -> bool:
    """'leche' coincide con 'leche entera 1 L'. 'leche' NO coincide con 'lechuga'."""
    c, i = norm(consulta), norm(item)
    if c == i:
        return True
    return c in i.split() or i.startswith(c + " ")


# ──────────────────────────────────────────────── plan de comidas (cocina) ──

@dataclass
class Comida:
    receta: str
    ingredientes: list[str]


def leer_plan(ruta: Path, dia: date) -> tuple[list[Comida], list[str]]:
    """Lee el archivo que produce el experto en cocina. Formato mínimo, sin dependencias."""
    if not ruta.is_file():
        return [], [f"no hay plan de comidas en {ruta}"]

    comidas: list[Comida] = []
    dia_actual, receta = None, None
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2}:", linea.strip()):
            dia_actual = linea.strip().rstrip(":")
            continue
        if dia_actual != dia.isoformat():
            continue
        m = re.match(r"^\s*-\s*receta:\s*(.+)$", linea)
        if m:
            receta = m.group(1).strip()
            continue
        m = re.match(r"^\s*ingredientes:\s*\[(.*)\]\s*$", linea)
        if m and receta:
            ing = [x.strip() for x in m.group(1).split(",") if x.strip()]
            comidas.append(Comida(receta=receta, ingredientes=ing))
            receta = None
    if not comidas:
        return [], [f"el plan no tiene comidas para {dia.isoformat()}"]
    return comidas, []


# ────────────────────────────────────────── Recordatorios (lista canónica) ──

def _esperar(fn, timeout=20.0):
    hecho = threading.Event()
    caja = {}

    def cb(*args):
        caja["args"] = args
        hecho.set()

    fn(cb)
    if not hecho.wait(timeout):
        raise TimeoutError("EventKit no respondió a tiempo")
    return caja.get("args", ())


def _store():
    from EventKit import EKEventStore
    st = EKEventStore.alloc().init()
    if hasattr(st, "requestFullAccessToRemindersWithCompletion_"):
        args = _esperar(st.requestFullAccessToRemindersWithCompletion_)
    else:
        from EventKit import EKEntityTypeReminder
        args = _esperar(lambda cb: st.requestAccessToEntityType_completion_(EKEntityTypeReminder, cb))
    if not (args and args[0]):
        raise PermissionError(
            "macOS no dio acceso a Recordatorios. Configuración del Sistema → "
            "Privacidad y seguridad → Recordatorios.")
    return st


def _lista(store, nombre: str):
    from EventKit import EKEntityTypeReminder
    for cal in store.calendarsForEntityType_(EKEntityTypeReminder) or []:
        if norm(cal.title()) == norm(nombre):
            return cal
    disponibles = [c.title() for c in store.calendarsForEntityType_(EKEntityTypeReminder) or []]
    raise LookupError(f"no existe la lista '{nombre}'. Tenés: {', '.join(disponibles)}")


def leer_lista(cfg) -> list[tuple[str, object]]:
    """[(título, objeto EKReminder)] de lo pendiente en la lista de compras."""
    store = _store()
    cal = _lista(store, cfg["compras"]["lista"])
    pred = store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(
        None, None, [cal])
    args = _esperar(lambda cb: store.fetchRemindersMatchingPredicate_completion_(pred, cb))
    return [(r.title() or "", r) for r in (args[0] if args else []) or []]


def agregar(cfg, titulos: list[str]) -> None:
    from EventKit import EKReminder
    store = _store()
    cal = _lista(store, cfg["compras"]["lista"])
    for t in titulos:
        rem = EKReminder.reminderWithEventStore_(store)
        rem.setTitle_(t)
        rem.setCalendar_(cal)
        ok, err = store.saveReminder_commit_error_(rem, True, None)
        if not ok:
            raise RuntimeError(f"no pude agregar '{t}': {err}")


def quitar(cfg, objetos: list) -> None:
    store = _store()
    for rem in objetos:
        ok, err = store.removeReminder_commit_error_(rem, True, None)
        if not ok:
            raise RuntimeError(f"no pude quitar '{rem.title()}': {err}")


# ─────────────────────────────────────────────────────────────── comandos ────

def ingredientes_de_hoy(cfg, dia: date):
    ruta = Path(cfg["compras"]["plan_comidas"]).expanduser()
    comidas, avisos = leer_plan(ruta, dia)
    ing = []
    for c in comidas:
        for i in c.ingredientes:
            if not any(coincide(i, x) for x in ing):
                ing.append(i)
    return comidas, ing, avisos


def cmd_falta(cfg, dia: date, *, imprimir=True) -> list[str]:
    comidas, ing, avisos = ingredientes_de_hoy(cfg, dia)
    for a in avisos:
        print(f"· {a}", file=sys.stderr)
    if not ing:
        return []

    en_lista = [t for t, _ in leer_lista(cfg)]
    faltan = [i for i in ing if not any(coincide(i, t) for t in en_lista)]

    if imprimir:
        for c in comidas:
            print(f"  {c.receta}")
        print()
        if faltan:
            print(f"FALTA COMPRAR ({len(faltan)} de {len(ing)}):")
            for f in faltan:
                print(f"  · {f}")
        else:
            print("No falta nada: todo lo de hoy ya está en la lista.")
    return faltan


def cmd_sincronizar(cfg, dia: date) -> int:
    faltan = cmd_falta(cfg, dia, imprimir=False)
    if not faltan:
        print("Nada que agregar.")
        return 0
    agregar(cfg, faltan)
    print(f"Agregué a '{cfg['compras']['lista']}':")
    for f in faltan:
        print(f"  + {f}")
    return 0


def cmd_tengo(cfg, consulta: str, auto: bool) -> int:
    """'ya tengo leche' → lo saca. Nunca adivina en silencio (P10)."""
    candidatos = [(t, o) for t, o in leer_lista(cfg) if coincide(consulta, t)]

    if not candidatos:
        print(f"No encontré '{consulta}' en la lista. No toqué nada.")
        return 1

    if len(candidatos) > 1 and not auto:
        print(f"'{consulta}' coincide con {len(candidatos)} ítems:")
        for n, (t, _) in enumerate(candidatos, 1):
            print(f"  {n}. {t}")
        print("  a. todos")
        resp = input("¿Cuál saco? [número/a/enter=cancelar] ").strip().lower()
        if resp == "a":
            pass
        elif resp.isdigit() and 1 <= int(resp) <= len(candidatos):
            candidatos = [candidatos[int(resp) - 1]]
        else:
            print("Cancelado. No toqué nada.")
            return 1

    quitar(cfg, [o for _, o in candidatos])
    for t, _ in candidatos:
        print(f"  − {t}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="compras")
    ap.add_argument("cmd", choices=["falta", "sincronizar", "tengo", "lista"])
    ap.add_argument("texto", nargs="?", default="")
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument("--hoy", default=None)
    ap.add_argument("--si", action="store_true", help="no preguntar ante ambigüedad")
    a = ap.parse_args(argv)

    cfg = tomllib.loads((a.config or config_por_defecto()).read_text(encoding="utf-8"))
    dia = date.fromisoformat(a.hoy) if a.hoy else date.today()

    try:
        if a.cmd == "falta":
            cmd_falta(cfg, dia)
            return 0
        if a.cmd == "sincronizar":
            return cmd_sincronizar(cfg, dia)
        if a.cmd == "lista":
            for t, _ in leer_lista(cfg):
                print(f"  · {t}")
            return 0
        if a.cmd == "tengo":
            if not a.texto:
                print("Decime qué tenés:  compras.py tengo \"leche\"", file=sys.stderr)
                return 2
            return cmd_tengo(cfg, a.texto, a.si)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
