#!/bin/bash
# Instalador del brief diario. Corré esto una sola vez, en tu Mac.
#
#   ./instalar.sh [ruta-al-repo-pm-assistant]
#
# Ejemplo:  ./instalar.sh ~/projects/pm-assistant
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PM_REPO="${1:-}"
HORA="${HORA_BRIEF:-7}"
LABEL="personal.kraken.brief"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

[[ "$(uname)" == "Darwin" ]] || { echo "Esto es solo para macOS."; exit 1; }

# ── Python ≥3.12 ────────────────────────────────────────────────────────────
# El `python3` del sistema en macOS suele ser 3.9, y NO alcanza: brief.py usa
# tomllib (3.11+) y pm-assistant exige >=3.12. Se busca uno válido ANTES de
# construir nada, para no dejar un venv roto a medio armar.
sirve() {
  command -v "$1" >/dev/null 2>&1 &&
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null
}

PY=""
if [[ -n "${PYTHON:-}" ]]; then
  sirve "$PYTHON" && PY="$PYTHON" || {
    echo "ERROR: PYTHON=$PYTHON no es 3.12+ o no existe."; exit 1; }
else
  for cand in python3.14 python3.13 python3.12 \
              /opt/homebrew/bin/python3.14 /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 \
              /usr/local/bin/python3.13 /usr/local/bin/python3.12 \
              python3; do
    if sirve "$cand"; then PY="$cand"; break; fi
  done
fi

if [[ -z "$PY" ]]; then
  cat >&2 <<ERR

ERROR: no encontré Python 3.12 o superior.
  Tu python3 es: $(python3 -V 2>&1)

  Instalalo y volvé a correr esto:
      brew install python@3.12

  Si ya lo tenés en otra ruta:
      PYTHON=/ruta/a/python3.12 ./instalar.sh ${PM_REPO:-}
ERR
  exit 1
fi

echo "==> 1/6  Entorno virtual — $("$PY" -V) desde $(command -v "$PY")"
# Si quedó un venv con la versión equivocada de un intento anterior, se rehace.
if [[ -x "$AQUI/.venv/bin/python" ]] && \
   ! "$AQUI/.venv/bin/python" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null; then
  echo "    (había un venv con $("$AQUI/.venv/bin/python" -V 2>&1) — lo rehago)"
  rm -rf "$AQUI/.venv"
fi
"$PY" -m venv "$AQUI/.venv"
"$AQUI/.venv/bin/pip" install --quiet --upgrade pip

echo "==> 2/6  EventKit (PyObjC)"
"$AQUI/.venv/bin/pip" install --quiet pyobjc-framework-EventKit

if [[ -n "$PM_REPO" ]]; then
  echo "==> 3/6  Experto en dirección desde $PM_REPO"
  "$AQUI/.venv/bin/pip" install --quiet -e "$PM_REPO"
else
  echo "==> 3/6  (salteado: sin repo de pm-assistant; el brief irá sin la sección de dirección)"
fi

echo "==> 4/6  Primera corrida — macOS va a pedirte permisos AHORA."
echo "         Aceptá Calendarios y Recordatorios. Si no aparece el diálogo:"
echo "         Configuración del Sistema → Privacidad y seguridad → Calendarios."
echo
"$AQUI/.venv/bin/python" "$AQUI/brief.py" --dry-run || true
echo

read -r -p "¿Viste tu agenda real arriba? [s/N] " ok
[[ "$ok" =~ ^[sSyY]$ ]] || {
  echo
  echo "Frená acá. Si el brief no ve el calendario, programarlo no sirve."
  echo "Revisá los permisos y volvé a correr:  ./instalar.sh $PM_REPO"
  exit 1
}

echo "==> 5/6  Skill de Claude"
# La skill vive en el repo (se versiona con el código que invoca) pero se
# enlaza a ~/.claude/skills/ para poder hablarle a kraken desde cualquier
# sesión. Symlink, no copia: una sola fuente, sin drift.
mkdir -p "$HOME/.claude/skills"
if [[ -L "$HOME/.claude/skills/kraken" || ! -e "$HOME/.claude/skills/kraken" ]]; then
  ln -sfn "$AQUI/.claude/skills/kraken" "$HOME/.claude/skills/kraken"
  echo "    enlazada — ahora podés pedirle el brief desde cualquier chat"
else
  echo "    ya hay algo en ~/.claude/skills/kraken que no es un enlace — lo dejo"
fi

echo "==> 6/6  Programando para las ${HORA}:00, de lunes a viernes"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$AQUI/.venv/bin/python</string>
    <string>$AQUI/brief.py</string>
  </array>
  <key>WorkingDirectory</key><string>$AQUI</string>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>$HORA</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>$HORA</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>$HORA</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>$HORA</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>$HORA</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>StandardOutPath</key><string>$AQUI/brief.log</string>
  <key>StandardErrorPath</key><string>$AQUI/brief.log</string>
</dict>
</plist>
PLISTEOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo
echo "Listo. El brief sale a las ${HORA}:00 de lunes a viernes."
echo
echo "  Probarlo ahora     : launchctl start $LABEL  &&  cat $AQUI/brief.log"
echo "  Verlo sin entregar : $AQUI/.venv/bin/python $AQUI/brief.py --dry-run"
echo "  Apagarlo           : launchctl unload $PLIST"
echo "  Cambiar la hora    : HORA_BRIEF=8 ./instalar.sh $PM_REPO"
