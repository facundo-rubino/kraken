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

echo "==> 1/5  Entorno virtual"
python3 -m venv "$AQUI/.venv"
"$AQUI/.venv/bin/pip" install --quiet --upgrade pip

echo "==> 2/5  EventKit (PyObjC)"
"$AQUI/.venv/bin/pip" install --quiet pyobjc-framework-EventKit

if [[ -n "$PM_REPO" ]]; then
  echo "==> 3/5  Experto en dirección desde $PM_REPO"
  "$AQUI/.venv/bin/pip" install --quiet -e "$PM_REPO"
else
  echo "==> 3/5  (salteado: sin repo de pm-assistant; el brief irá sin la sección de dirección)"
fi

echo "==> 4/5  Primera corrida — macOS va a pedirte permisos AHORA."
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

echo "==> 5/5  Programando para las ${HORA}:00, de lunes a viernes"
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
