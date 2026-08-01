#!/usr/bin/env python3
"""Brief diario — asistente personal.

    python brief.py                 # arma el brief y lo entrega
    python brief.py --dry-run       # lo imprime, no entrega nada
    python brief.py --hoy 2026-08-03

Cuatro pasos, en este orden y sin mezclarse:

  1. LEER      fuentes de tiempo (Calendario y Recordatorios vía EventKit)
  2. PREGUNTAR al experto en dirección (pm-assistant) qué detectó
  2b. MIRAR    los buzones de captura — cuánto se acumuló sin clasificar
  3. COMPONER  el texto — determinístico, sin modelo, sin costo
  4. ENTREGAR  por los canales configurados

Reglas que este archivo hace cumplir (ROUTER.md):
  · El experto DETECTA; kraken AVISA. Acá se le pregunta, nunca se le ordena.
  · De calendarios corporativos se leen SOLO título, horario y duración (D29).
  · Kraken no decide nada ni escribe en ninguna fuente. Solo lee y cuenta.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def config_por_defecto() -> Path:
    """`config.local.toml` si existe (tu config real, fuera de git); si no, la plantilla."""
    local = AQUI / "config.local.toml"
    return local if local.is_file() else AQUI / "config.toml"


DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ─────────────────────────────────────────────────────────── modelo interno ──

@dataclass
class Evento:
    titulo: str
    inicio: datetime | None      # None si es de día completo
    fin: datetime | None
    todo_el_dia: bool
    calendario: str
    corporativo: bool

    def franja(self, hoy: date | None = None) -> str:
        if self.todo_el_dia or not self.inicio or not self.fin:
            return "todo el día"
        # Un evento que empieza ayer o termina mañana no puede mostrarse como
        # "22:00–09:00": eso se lee como un disparate. Se marca el cruce.
        ini = f"{self.inicio:%H:%M}" if not hoy or self.inicio.date() == hoy else "←"
        fin = f"{self.fin:%H:%M}" if not hoy or self.fin.date() == hoy else "→"
        return f"{ini}–{fin}"

    def duracion_min(self) -> int:
        if self.todo_el_dia or not self.inicio or not self.fin:
            return 0
        return int((self.fin - self.inicio).total_seconds() // 60)


@dataclass
class Recordatorio:
    titulo: str
    vence: date | None
    lista: str
    corporativo: bool = False

    def dias_vencido(self, hoy: date) -> int:
        return (hoy - self.vence).days if self.vence and self.vence < hoy else 0


@dataclass
class Bloque:
    """Compromiso fijo y recurrente que no vive en el calendario."""
    nombre: str
    inicio: datetime
    fin: datetime

    def franja(self) -> str:
        return f"{self.inicio:%H:%M}–{self.fin:%H:%M}"


@dataclass
class Deteccion:
    iniciativa: str
    tipo: str
    detalle: str


@dataclass
class Buzon:
    """Una bandeja de entrada que se está llenando.

    Kraken CUENTA lo que hay adentro; nunca mira qué es ni sugiere qué hacer
    con cada ítem. "Tenés 14 sin clasificar" es tu atención, y es su trabajo.
    "Consolidá esas dos planillas" es una decisión de dominio, y ROUTER.md se
    lo prohíbe.
    """
    nombre: str
    items: int
    dias_mas_viejo: int | None = None

    def merece_aviso(self, umbral_items: int, umbral_dias: int) -> bool:
        """Solo habla si cruzó un umbral. Un aviso diario es ruido, no señal."""
        if self.items == 0:
            return False
        if umbral_items and self.items >= umbral_items:
            return True
        return bool(umbral_dias
                    and self.dias_mas_viejo is not None
                    and self.dias_mas_viejo >= umbral_dias)


@dataclass
class Brief:
    hoy: date
    eventos: list[Evento] = field(default_factory=list)
    recordatorios: list[Recordatorio] = field(default_factory=list)
    detecciones: list[Deteccion] = field(default_factory=list)
    buzones: list[Buzon] = field(default_factory=list)  # inboxes sin vaciar
    fijos: list[Bloque] = field(default_factory=list)  # trabajo, clases…
    anula_fijos: str | None = None                     # feriado que los cancela
    manana: list[Evento] = field(default_factory=list)  # eventos de mañana
    manana_arranca: datetime | None = None              # primer compromiso de mañana
    comidas: list[str] = field(default_factory=list)   # recetas de hoy
    falta_comprar: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)   # fallos honestos, no se ocultan


# ───────────────────────────────────────────── 1. LEER — Apple vía EventKit ──

def _esperar(fn, timeout=20.0):
    """EventKit responde por callback; acá lo volvemos síncrono."""
    hecho = threading.Event()
    caja = {}

    def cb(*args):
        caja["args"] = args
        hecho.set()

    fn(cb)
    if not hecho.wait(timeout):
        raise TimeoutError("EventKit no respondió a tiempo")
    return caja.get("args", ())


def _store_con_permiso(tipo_entidad, kind: str):
    """Devuelve un EKEventStore con acceso concedido, o levanta.

    macOS 14+ usa requestFullAccessTo…; versiones previas, requestAccessToEntityType_.
    """
    from EventKit import EKEventStore

    store = EKEventStore.alloc().init()
    if kind == "eventos" and hasattr(store, "requestFullAccessToEventsWithCompletion_"):
        args = _esperar(store.requestFullAccessToEventsWithCompletion_)
    elif kind == "recordatorios" and hasattr(store, "requestFullAccessToRemindersWithCompletion_"):
        args = _esperar(store.requestFullAccessToRemindersWithCompletion_)
    else:
        args = _esperar(lambda cb: store.requestAccessToEntityType_completion_(tipo_entidad, cb))

    concedido = bool(args[0]) if args else False
    if not concedido:
        raise PermissionError(
            f"macOS no dio acceso a {kind}. Ajustá Configuración del Sistema → "
            f"Privacidad y seguridad → {'Calendarios' if kind == 'eventos' else 'Recordatorios'} "
            f"y habilitá la app desde la que corrés esto (Terminal, o launchd)."
        )
    return store


def _nsdate(dt: datetime):
    from Foundation import NSDate
    return NSDate.dateWithTimeIntervalSince1970_(dt.timestamp())


def _dt(nsdate) -> datetime | None:
    if nsdate is None:
        return None
    return datetime.fromtimestamp(nsdate.timeIntervalSince1970())


def leer_calendario(cfg: dict, hoy: date) -> tuple[list[Evento], list[str]]:
    """Eventos de hoy.

    PERÍMETRO (D29): de cada evento se toman título, horario, duración y nombre
    del calendario. Nada más. Notas, ubicación, invitados, adjuntos y URL no se
    leen — no es que se filtren después: no entran nunca a este proceso.
    """
    from EventKit import EKEntityTypeEvent

    store = _store_con_permiso(EKEntityTypeEvent, "eventos")
    inicio = datetime.combine(hoy, time.min)
    fin = datetime.combine(hoy, time.max)

    pred = store.predicateForEventsWithStartDate_endDate_calendars_(
        _nsdate(inicio), _nsdate(fin), None)

    ignorar = {c.lower() for c in cfg["calendario"].get("ignorar", [])}
    corp = {c.lower() for c in cfg["calendario"].get("corporativos", [])}

    out: list[Evento] = []
    for ev in store.eventsMatchingPredicate_(pred) or []:
        cal = ev.calendar().title() if ev.calendar() else ""
        if cal.lower() in ignorar:
            continue
        out.append(Evento(
            titulo=(ev.title() or "(sin título)"),
            inicio=_dt(ev.startDate()),
            fin=_dt(ev.endDate()),
            todo_el_dia=bool(ev.isAllDay()),
            calendario=cal,
            corporativo=cal.lower() in corp,
        ))
    out.sort(key=lambda e: (not e.todo_el_dia, e.inicio or datetime.min))
    return out, []


def leer_recordatorios(cfg: dict, hoy: date) -> tuple[list[Recordatorio], list[str]]:
    """Recordatorios incompletos que vencen hoy o antes."""
    from EventKit import EKEntityTypeReminder

    store = _store_con_permiso(EKEntityTypeReminder, "recordatorios")
    desde = datetime.combine(hoy - timedelta(days=cfg["recordatorios"]["vencidos_dias"]), time.min)
    hasta = datetime.combine(hoy, time.max)

    solo = {l.lower() for l in cfg["recordatorios"].get("listas", [])}
    corp = {c.lower() for c in cfg["calendario"].get("corporativos", [])}
    cals = None
    if solo:
        cals = [c for c in store.calendarsForEntityType_(EKEntityTypeReminder) or []
                if c.title().lower() in solo] or None

    pred = store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(
        _nsdate(desde), _nsdate(hasta), cals)
    args = _esperar(lambda cb: store.fetchRemindersMatchingPredicate_completion_(pred, cb))
    crudos = args[0] if args else []

    out: list[Recordatorio] = []
    for r in crudos or []:
        comp = r.dueDateComponents()
        vence = None
        if comp:
            try:
                vence = date(comp.year(), comp.month(), comp.day())
            except Exception:
                vence = None
        lista = r.calendar().title() if r.calendar() else ""
        out.append(Recordatorio(
            titulo=(r.title() or "(sin título)"),
            vence=vence,
            lista=lista,
            corporativo=lista.lower() in corp,
        ))
    out.sort(key=lambda r: (r.vence or date.max))
    return out, []


# ──────────────────────────── 2. PREGUNTAR al experto en dirección ──────────

def preguntar_direccion(cfg: dict, hoy: date) -> tuple[list[Deteccion], list[str]]:
    """Le pregunta a pm-assistant qué detectó. Read-only, determinístico, sin modelo.

    Es el patrón de ROUTER.md §6 en su primer uso real: el experto responde
    cuando le preguntan y nunca empuja. Si no está instalado, el brief sigue
    andando sin esta sección — degradación, no fallo.
    """
    ruta = (cfg.get("direccion", {}).get("state_dir") or "").strip()
    if not ruta:
        return [], []

    state_dir = Path(ruta).expanduser()
    if not state_dir.is_dir():
        return [], [f"estado de dirección no encontrado en {state_dir}"]

    try:
        from pm_assistant import session
    except ImportError:
        return [], ["pm_assistant no está instalado en este entorno; "
                    "el brief va sin la sección de dirección"]

    inis, errores = session.load_all(state_dir)
    avisos = [f"iniciativa inválida: {Path(f).name}" for f in errores]

    out: list[Deteccion] = []
    for ini in inis:
        nombre = ini.get("titulo") or ini.get("id", "?")
        _flags, dets = session.flags_for(ini, hoy)
        for d in dets:
            out.append(Deteccion(iniciativa=nombre, tipo=d.tipo, detalle=d.detalle))
    return out, avisos


def preguntar_cocina(cfg: dict, hoy: date) -> tuple[list[str], list[str], list[str]]:
    """Le pregunta al experto en cocina qué se cocina hoy y qué falta comprar.

    Mismo patrón que `preguntar_direccion`: kraken pregunta, el experto
    responde. Kraken no elige recetas ni opina de comida.
    """
    if not cfg.get("compras", {}).get("en_brief", False):
        return [], [], []
    try:
        import compras
    except ImportError:
        return [], [], ["compras.py no está junto a brief.py"]
    try:
        comidas, _ing, avisos = compras.ingredientes_de_hoy(cfg, hoy)
        if not comidas:
            return [], [], avisos
        faltan = compras.cmd_falta(cfg, hoy, imprimir=False)
        return [c.receta for c in comidas], faltan, avisos
    except Exception as exc:
        return [], [], [f"cocina: {exc}"]


# ─────────────────────────────────── 2b. MIRAR los buzones de captura ────────

_AS_NOTAS = '''
tell application "Notes"
    set fs to every folder whose name is "%s"
    if fs is {} then return "NOFOLDER"
    set f to item 1 of fs
    set total to count of notes of f
    if total is 0 then return "0|-"
    set fechas to modification date of every note of f
    set vieja to item 1 of fechas
    repeat with d in fechas
        if (contents of d) < vieja then set vieja to (contents of d)
    end repeat
    return (total as text) & "|" & ((round (((current date) - vieja) / days)) as text)
end tell
'''


def _buzon_recordatorios(nombre: str, hoy: date) -> tuple[Buzon | None, str | None]:
    """Cuenta los incompletos de una lista, tengan fecha o no.

    `leer_recordatorios` solo trae lo que vence pronto — que es lo correcto para
    la agenda del día. Un buzón sin vaciar es justo lo contrario: lo que entró y
    nunca recibió fecha. Por eso el predicado va sin ventana temporal.
    """
    from EventKit import EKEntityTypeReminder

    store = _store_con_permiso(EKEntityTypeReminder, "recordatorios")
    cals = [c for c in store.calendarsForEntityType_(EKEntityTypeReminder) or []
            if c.title().lower() == nombre.lower()]
    if not cals:
        return None, f"no existe la lista de Recordatorios «{nombre}»"

    pred = store.predicateForIncompleteRemindersWithDueDateStarting_ending_calendars_(
        None, None, cals)
    args = _esperar(lambda cb: store.fetchRemindersMatchingPredicate_completion_(pred, cb))
    crudos = args[0] if args else []

    fechas = [d for d in (_dt(r.creationDate()) for r in crudos or []) if d]
    dias = (hoy - min(fechas).date()).days if fechas else None
    return Buzon(nombre=f"Recordatorios · {nombre}", items=len(crudos or []),
                 dias_mas_viejo=dias), None


def _buzon_notas(nombre: str) -> tuple[Buzon | None, str | None]:
    """Cuenta las notas de una carpeta vía AppleScript.

    Notas no tiene EventKit ni nada parecido: AppleScript es la única puerta, y
    abre la app al preguntarle. Es lectura pura — no crea, no mueve, no borra.
    """
    salida = subprocess.run(
        ["osascript", "-e", _AS_NOTAS % nombre.replace('\\', '\\\\').replace('"', '\\"')],
        capture_output=True, timeout=60, text=True)
    if salida.returncode != 0:
        detalle = ((salida.stderr or "").strip().splitlines() or ["?"])[-1]
        return None, f"no se pudo leer Notas: {detalle}"

    crudo = (salida.stdout or "").strip()
    if crudo == "NOFOLDER":
        return None, f"no existe la carpeta de Notas «{nombre}»"

    total, _, edad = crudo.partition("|")
    try:
        items = int(total)
    except ValueError:
        return None, f"Notas devolvió algo inesperado: {crudo!r}"
    try:
        dias = int(edad)
    except ValueError:
        dias = None
    return Buzon(nombre=f"Notas · {nombre}", items=items, dias_mas_viejo=dias), None


def mirar_buzones(cfg: dict, hoy: date) -> tuple[list[Buzon], list[str]]:
    """Los inboxes que se llenan solos, si cruzaron un umbral.

    Reemplaza la "revisión de los viernes" agendada. Un evento de calendario te
    interrumpe todos los viernes aunque no haya nada que hacer, y encima nace de
    una segunda fuente de avisos — que es exactamente lo que ROUTER.md §1
    prohíbe. Esto aparece cuando hay motivo y calla cuando no.
    """
    h = cfg.get("higiene")
    if not h or not h.get("en_brief", False):
        return [], []

    umbral_items = int(h.get("umbral_items", 10) or 0)
    umbral_dias = int(h.get("umbral_dias", 7) or 0)

    crudos: list[Buzon] = []
    avisos: list[str] = []
    fuentes = (
        ((h.get("inbox_recordatorios") or "").strip(),
         lambda n: _buzon_recordatorios(n, hoy)),
        ((h.get("inbox_notas") or "").strip(), _buzon_notas),
    )
    for nombre, leer in fuentes:
        if not nombre:
            continue
        try:
            buzon, aviso = leer(nombre)
        except Exception as exc:
            # Un buzón ilegible degrada el brief; no lo voltea. Y se dice.
            buzon, aviso = None, f"buzón «{nombre}»: {exc}"
        if buzon:
            crudos.append(buzon)
        if aviso:
            avisos.append(aviso)

    return [z for z in crudos if z.merece_aviso(umbral_items, umbral_dias)], avisos


# ────────────────────────────────── compromisos fijos (no están en el calendario) ──

DIAS_CORTOS = ["lu", "ma", "mi", "ju", "vi", "sa", "do"]


def _hora(txt: str) -> time:
    h, m = txt.split(":")
    return time(int(h), int(m))


def anulan_fijos(cfg: dict, eventos: list[Evento]) -> str | None:
    """¿Hay un evento de día completo que cancela los compromisos fijos?

    Un feriado o un día de licencia no te saca del calendario: te saca de la
    oficina. Sin esto el brief informa 6 h libres un día que tenés 14 — y se
    equivoca justo en los días que más querés usar.
    """
    patrones = [p.lower() for p in cfg.get("calendario", {}).get("anula_fijos", [])]
    if not patrones:
        return None
    for e in eventos:
        if not e.todo_el_dia:
            continue
        titulo = e.titulo.lower()
        for p in patrones:
            if p in titulo:
                return e.titulo
    return None


def bloques_fijos(cfg: dict, hoy: date) -> list[Bloque]:
    """Compromisos recurrentes declarados a mano, que NO viven en el calendario.

    El trabajo de oficina y las clases no son eventos: son la estructura fija de
    la semana. Sin esto el brief diría "13 h libres" todos los días, que es
    falso y hace inútil el cálculo de huecos.

    Cada bloque puede tener una ventana de fechas (`desde_fecha`/`hasta_fecha`)
    para lo estacional — dar clase solo de marzo a junio, por ejemplo.
    """
    hoy_corto = DIAS_CORTOS[hoy.weekday()]
    out: list[Bloque] = []
    for f in cfg.get("fijos", []):
        dias = [d.strip().lower()[:2] for d in f.get("dias", [])]
        if hoy_corto not in dias:
            continue
        d1, d2 = f.get("desde_fecha"), f.get("hasta_fecha")
        if d1 and hoy < date.fromisoformat(str(d1)):
            continue
        if d2 and hoy > date.fromisoformat(str(d2)):
            continue
        out.append(Bloque(
            nombre=f.get("nombre", "(sin nombre)"),
            inicio=datetime.combine(hoy, _hora(f["desde"])),
            fin=datetime.combine(hoy, _hora(f["hasta"])),
        ))
    out.sort(key=lambda b: b.inicio)
    return out


# ──────────────────────────────────────────────── 3. COMPONER — sin modelo ──

def ocupado_fusionado(eventos: list[Evento], cfg: dict, hoy: date,
                      fijos: list[Bloque] | None = None) -> list[tuple[datetime, datetime]]:
    """Tiempo realmente ocupado, con los solapamientos fusionados.

    Un mandado de 1 h DENTRO del horario de trabajo no te ocupa una hora más:
    ya estabas ocupado. Sumar duraciones sueltas informa 9 h en un día de 8.
    """
    dia_ini = datetime.combine(hoy, time(cfg["calendario"]["hora_inicio"]))
    dia_fin = datetime.combine(hoy, time(cfg["calendario"]["hora_fin"]))

    tramos = [(e.inicio, e.fin) for e in eventos
              if not e.todo_el_dia and e.inicio and e.fin]
    tramos += [(b.inicio, b.fin) for b in (fijos or [])]

    recortado = sorted((max(i, dia_ini), min(f, dia_fin))
                       for i, f in tramos if f > dia_ini and i < dia_fin)

    fusionado: list[list[datetime]] = []
    for ini, fin in recortado:
        if fusionado and ini <= fusionado[-1][1]:
            fusionado[-1][1] = max(fusionado[-1][1], fin)
        else:
            fusionado.append([ini, fin])
    return [(i, f) for i, f in fusionado]


def huecos_libres(eventos: list[Evento], cfg: dict, hoy: date,
                  fijos: list[Bloque] | None = None) -> list[tuple[datetime, datetime]]:
    """Bloques libres dentro de tu día, descontando eventos Y compromisos fijos.

    Determinístico a propósito. A futuro esto es lo que se le entrega al experto
    en dirección como CAPACIDAD DECLARADA (Q-S3 de la Spec 002) — por eso vive
    acá y no allá: el experto planifica sobre la capacidad, no la calcula.
    """
    dia_ini = datetime.combine(hoy, time(cfg["calendario"]["hora_inicio"]))
    dia_fin = datetime.combine(hoy, time(cfg["calendario"]["hora_fin"]))

    fusionado = ocupado_fusionado(eventos, cfg, hoy, fijos)

    libres, cursor = [], dia_ini
    for ini, fin in fusionado:
        if ini - cursor >= timedelta(minutes=45):
            libres.append((cursor, ini))
        cursor = max(cursor, fin)
    if dia_fin - cursor >= timedelta(minutes=45):
        libres.append((cursor, dia_fin))
    return libres


def _hhmm(minutos: int) -> str:
    h, m = divmod(minutos, 60)
    if h and m:
        return f"{h} h {m:02d}"
    return f"{h} h" if h else f"{m} min"


def componer(b: Brief, cfg: dict, *, para_terceros: bool = False) -> str:
    """Arma el texto. `para_terceros` redacta títulos corporativos (D29 + P7)."""
    d = b.hoy
    L = [f"{DIAS[d.weekday()].capitalize()} {d.day} de {MESES[d.month - 1]}", ""]

    redactar = para_terceros and not cfg["entrega"].get("perimetro_en_push", False)

    def titulo_de(e: Evento) -> str:
        return f"Reunión ({e.calendario})" if (redactar and e.corporativo) else e.titulo

    def titulo_rec(r: Recordatorio) -> str:
        return f"(pendiente de {r.lista})" if (redactar and r.corporativo) else r.titulo

    if b.eventos:
        L.append("AGENDA")
        for e in b.eventos:
            marca = " ·" if e.corporativo else "  "
            L.append(f" {e.franja(b.hoy):>12}{marca} {titulo_de(e)}")
        comprometido = sum(int((f - i).total_seconds() // 60)
                           for i, f in ocupado_fusionado(b.eventos, cfg, b.hoy, b.fijos))
        if comprometido:
            L.append(f"{'':>14}  ({_hhmm(comprometido)} comprometidas)")
    elif not b.fijos:
        L.append("AGENDA — el día está vacío.")
    if b.eventos or not b.fijos:
        L.append("")

    if b.anula_fijos:
        L += [f"SIN OFICINA — {b.anula_fijos}", ""]

    if b.fijos:
        porNombre: dict[str, list[str]] = {}
        for bl in b.fijos:
            porNombre.setdefault(bl.nombre, []).append(bl.franja())
        for nombre, franjas in porNombre.items():
            L.append(f"FIJO   {nombre}: " + " · ".join(franjas))
        L.append("")

    libres = huecos_libres(b.eventos, cfg, b.hoy, b.fijos)
    if libres:
        trozos = [f"{i:%H:%M}–{f:%H:%M}" for i, f in libres]
        total = sum(int((f - i).total_seconds() // 60) for i, f in libres)
        L += [f"LIBRE — {_hhmm(total)} en {len(libres)} bloque(s): " + ", ".join(trozos), ""]

    vencidos = [r for r in b.recordatorios if r.dias_vencido(b.hoy) > 0]
    hoy_vence = [r for r in b.recordatorios if r.vence == b.hoy]
    if vencidos or hoy_vence:
        L.append("RECORDATORIOS")
        for r in hoy_vence:
            L.append(f" {'hoy':>12}   {titulo_rec(r)}")
        for r in sorted(vencidos, key=lambda r: -r.dias_vencido(b.hoy)):
            L.append(f" {str(r.dias_vencido(b.hoy)) + 'd tarde':>12}   {titulo_rec(r)}")
        L.append("")

    if b.comidas:
        L.append("COCINA")
        for c in b.comidas:
            L.append(f"   {c}")
        if b.falta_comprar:
            L.append(f"   falta comprar: {', '.join(b.falta_comprar)}")
        else:
            L.append("   ya tenés todo en la lista")
        L.append("")

    if b.manana or b.manana_arranca:
        cab = "MAÑANA"
        # Solo se avisa la hora de arranque si es MÁS TEMPRANO que lo habitual.
        # Decir "arranca 08:00" todos los días es ruido, no información.
        if b.manana_arranca and b.manana_arranca.hour < cfg["calendario"]["hora_inicio"]:
            cab += f" — arrancás {b.manana_arranca:%H:%M}, más temprano que de costumbre"
        L.append(cab)
        for e in b.manana[:4]:
            L.append(f" {e.franja(b.hoy + timedelta(days=1)):>12}   {titulo_de(e)}")
        if len(b.manana) > 4:
            L.append(f"{'':>14}   (+{len(b.manana) - 4} más)")
        L.append("")

    if b.detecciones:
        L.append("NECESITA DECISIÓN  (lo detectó el experto en dirección)")
        for det in b.detecciones:
            L.append(f"   {det.iniciativa}: {det.detalle}")
        L.append("")

    if b.buzones:
        L.append("BUZONES SIN VACIAR")
        for z in b.buzones:
            detalle = f"{z.items} ítem(s)"
            if z.dias_mas_viejo is not None:
                detalle += f", el más viejo de hace {z.dias_mas_viejo} día(s)"
            L.append(f"   {z.nombre}: {detalle}")
        L.append("")

    if b.avisos:
        L.append("EL BRIEF NO PUDO VER TODO")
        for a in b.avisos:
            L.append(f"   · {a}")
        L.append("")

    return "\n".join(L).rstrip() + "\n"


def resumen(b: Brief) -> str:
    """Una línea para la notificación."""
    partes = []
    if b.eventos:
        partes.append(f"{len(b.eventos)} evento(s)")
    pend = len([r for r in b.recordatorios if r.vence and r.vence <= b.hoy])
    if pend:
        partes.append(f"{pend} recordatorio(s)")
    if b.detecciones:
        partes.append(f"{len(b.detecciones)} para decidir")
    if b.buzones:
        partes.append(f"{sum(z.items for z in b.buzones)} sin clasificar")
    if b.falta_comprar:
        partes.append(f"{len(b.falta_comprar)} de compras")
    return " · ".join(partes) if partes else "Día despejado"


# ─────────────────────────────────────────────────────────── 4. ENTREGAR ────

def _osascript(script: str) -> None:
    subprocess.run(["osascript", "-e", script], check=True,
                   capture_output=True, timeout=30)


def entregar(b: Brief, cfg: dict, texto: str) -> list[str]:
    fallos = []
    for canal in cfg["entrega"]["canales"]:
        try:
            if canal == "archivo_icloud":
                dest = Path(cfg["entrega"]["ruta_icloud"]).expanduser()
                dest.mkdir(parents=True, exist_ok=True)
                (dest / f"{b.hoy:%Y-%m-%d}.md").write_text(texto, encoding="utf-8")
                (dest / "hoy.md").write_text(texto, encoding="utf-8")

            elif canal == "imessage":
                destino = cfg["identidad"]["apple_id"]
                cuerpo = texto.replace("\\", "\\\\").replace('"', '\\"')
                _osascript(
                    'tell application "Messages" to send "%s" to '
                    'buddy "%s" of (1st service whose service type = iMessage)'
                    % (cuerpo, destino))

            elif canal == "notificacion_mac":
                _osascript('display notification "%s" with title "Brief de hoy"'
                           % resumen(b).replace('"', "'"))

            elif canal == "ntfy":
                topic = cfg["entrega"].get("ntfy_topic", "").strip()
                if not topic:
                    fallos.append("ntfy activado sin topic configurado")
                    continue
                # Canal de TERCEROS: se recompone con redacción de perímetro.
                cuerpo = componer(b, cfg, para_terceros=True)
                subprocess.run(
                    ["curl", "-fsS", "-d", cuerpo, f"https://ntfy.sh/{topic}"],
                    check=True, capture_output=True, timeout=30)
            else:
                fallos.append(f"canal desconocido: {canal}")
        except Exception as exc:
            fallos.append(f"{canal}: {exc}")
    return fallos


# ──────────────────────────────────────────────────────────────── main ──────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="brief")
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument("--hoy", default=None, help="YYYY-MM-DD (default: hoy)")
    ap.add_argument("--dry-run", action="store_true", help="imprime, no entrega")
    args = ap.parse_args(argv)

    cfg = tomllib.loads((args.config or config_por_defecto()).read_text(encoding="utf-8"))
    hoy = date.fromisoformat(args.hoy) if args.hoy else date.today()
    b = Brief(hoy=hoy)

    for nombre, fn in (("calendario", leer_calendario), ("recordatorios", leer_recordatorios)):
        try:
            datos, avisos = fn(cfg, hoy)
            setattr(b, "eventos" if nombre == "calendario" else "recordatorios", datos)
            b.avisos += avisos
        except Exception as exc:
            # Una fuente caída degrada el brief; no lo cancela. Y se dice.
            b.avisos.append(f"{nombre}: {exc}")

    try:
        motivo = anulan_fijos(cfg, b.eventos)
        b.fijos = [] if motivo else bloques_fijos(cfg, hoy)
        if motivo:
            b.anula_fijos = motivo
    except Exception as exc:
        b.avisos.append(f"compromisos fijos mal configurados: {exc}")

    # Mañana: solo para saber si algo te espera temprano. Falla en silencio —
    # es un extra, no puede voltear el brief de hoy.
    try:
        man = hoy + timedelta(days=1)
        evs, _ = leer_calendario(cfg, man)
        b.manana = [e for e in evs if not e.todo_el_dia and e.inicio]
        candidatos = [e.inicio for e in b.manana]
        if not anulan_fijos(cfg, evs):
            candidatos += [f.inicio for f in bloques_fijos(cfg, man)]
        b.manana_arranca = min(candidatos) if candidatos else None
    except Exception:
        pass

    dets, avisos = preguntar_direccion(cfg, hoy)
    b.detecciones, b.avisos = dets, b.avisos + avisos

    b.comidas, b.falta_comprar, avisos_cocina = preguntar_cocina(cfg, hoy)
    b.avisos += avisos_cocina

    try:
        b.buzones, avisos_buzones = mirar_buzones(cfg, hoy)
        b.avisos += avisos_buzones
    except Exception as exc:
        b.avisos.append(f"buzones: {exc}")

    texto = componer(b, cfg)

    if args.dry_run:
        print(texto)
        return 0

    fallos = entregar(b, cfg, texto)
    for f in fallos:
        print(f"[entrega] {f}", file=sys.stderr)
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
