#!/usr/bin/env bash
set -euo pipefail

VENV_PATH="${1:-.venv}"

echo "======================================================================"
echo " TechCorp LATAM — Inicializador de Entorno Virtual Python 3.14"
echo "======================================================================"

if command -v python3.14 >/dev/null 2>&1; then
    PYTHON_CMD="python3.14"
    echo "[INFO] Python 3.14 detectado nativamente: $($PYTHON_CMD --version)"
elif command -v pyenv >/dev/null 2>&1 && pyenv versions | grep -q "3.14"; then
    PYTHON_CMD="$(pyenv which python3.14)"
    echo "[INFO] Python 3.14 detectado vía pyenv: $($PYTHON_CMD --version)"
elif command -v uv >/dev/null 2>&1; then
    echo "[INFO] Creando entorno virtual Python 3.14 mediante uv..."
    uv venv "$VENV_PATH" --python 3.14 || uv venv "$VENV_PATH"
    exit 0
else
    PYTHON_CMD="python3"
    echo "[WARN] Binario 'python3.14' no encontrado en PATH actual; usando $($PYTHON_CMD --version) compatible con PEP 695/701/749."
    echo "[TIP] Para instalar Python 3.14 estricto en Ubuntu/Debian o macOS:"
    echo "      pyenv install 3.14.0 && pyenv local 3.14.0"
fi

$PYTHON_CMD -m venv "$VENV_PATH"
echo "[OK] Entorno virtual creado exitosamente en: $VENV_PATH"
echo "     Para activarlo manualmente: source $VENV_PATH/bin/activate"
