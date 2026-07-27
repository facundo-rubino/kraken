#!/bin/bash
# Arma ~/experts/ : un solo lugar donde viven todos los expertos, cada uno con su
# repo, y un vault de Obsidian encima para leerlos y editarlos como un todo.
#
#   ./experts.sh
#
# Idempotente: si un repo ya está clonado, lo deja como está.
set -euo pipefail

RAIZ="${EXPERTS_DIR:-$HOME/experts}"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GH="${GH_USER:-facundo-rubino}"

# Un repo por experto. Los permisos de GitHub son por repo, no por directorio:
# por eso NO es un monorepo — el KB de fitness tiene que poder delegarse al
# entrenador sin darle acceso a lo demás.
REPOS=(
  "teaching-kb"     # experto docente — existe
  # "fitness-kb"    # descomentá cuando lo separes de AnkoFit
  # "cooking-kb"    # descomentá cuando exista
)

echo "==> Carpeta madre: $RAIZ"
mkdir -p "$RAIZ"

fallidos=()
for repo in "${REPOS[@]}"; do
  if [[ -d "$RAIZ/$repo/.git" ]]; then
    echo "    $repo ya está — lo dejo"
  else
    echo "    clonando $repo"
    # Un repo inaccesible NO puede voltear el resto del setup.
    if ! git clone --quiet "https://github.com/$GH/$repo.git" "$RAIZ/$repo" 2>/dev/null; then
      echo "    ! no pude clonar $repo — sigo"
      rmdir "$RAIZ/$repo" 2>/dev/null || true
      fallidos+=("$repo")
    fi
  fi
done

echo "==> Vault de Obsidian"
if [[ -d "$RAIZ/.obsidian" ]]; then
  echo "    ya existe — no lo piso (tu configuración manda)"
else
  cp -R "$AQUI/vault-template/.obsidian" "$RAIZ/.obsidian"
  echo "    configuración inicial escrita"
fi

if [[ ! -f "$RAIZ/INDICE.md" ]]; then
  cat > "$RAIZ/INDICE.md" <<'EOF'
# Expertos

Cada carpeta es un experto con dueño declarado y su propio repo git.
Las fronteras están en el `ROUTER.md` dkraken.

## Quién es quién

- **teaching-kb** — experto docente. Temario, progresión, dictados, evaluaciones.
  No posee fechas del semestre ni criterios de recorte: eso es del experto en dirección.
- **fitness-kb** *(pendiente)* — plantillas de mesociclo, progresión, cargas, RPE.
  Se parte en `reglas/` (lo posee el entrenador) y `datos/` (nunca sale).
- **cooking-kb** *(pendiente)* — recetas, Cookidoo, plan de comidas, lista de compras.

## Lo que NO vive acá

- El **estado de dirección** (`~/projects/direction-state`): se valida contra schema
  y Obsidian lo dejaría romper sin avisar.
- El **motor** de dirección (`pm-assistant`): es código, no conocimiento.

## Por qué Obsidian y no Notion

Obsidian **abre el archivo**; Notion **lo copia**. Por eso Notion necesitó una
decisión de gobernanza (ADR-001 de teaching-kb) y esto no: no hay segunda versión
que gobernar. Un conflicto acá es un archivo sin commitear, no una verdad paralela.
EOF
  echo "    INDICE.md creado"
fi

echo
if (( ${#fallidos[@]} )); then
  echo "OJO: no pude clonar: ${fallidos[*]}"
  echo "     (¿el repo existe? ¿tenés acceso? ¿estás autenticado en GitHub?)"
  echo "     El resto quedó armado igual."
  echo
fi
echo "Listo."
echo
echo "  Abrí Obsidian → 'Open folder as vault' → $RAIZ"
echo "  Vas a tener búsqueda y backlinks ENTRE expertos, y edición desde el iPhone."
echo
echo "  Ojo: Obsidian edita los mismos archivos que versiona git."
echo "  Commiteá seguido; un cambio sin commitear no es un conflicto, pero se pierde."
