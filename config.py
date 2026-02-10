# config.py

# =========================================
# Elegí dónde apuntar: local o remoto
# =========================================
USE_LOCAL = True   # poné False para usar el remoto

# =========================================
# Carpeta base donde viven tus PHP
#   - Si tus PHP están en /usuarios -> "http://localhost/usuarios"
#   - Si están en /phpmyadmin     -> "http://localhost/phpmyadmin"
# Ajustá SOLO estas dos líneas y el resto se arma solo.
# =========================================
LOCAL_API_BASE  = "http://localhost/usuarios"   # <-- tu caso actual (usuarios/usuarios.php)
REMOTE_API_BASE = "http://ec2-34-202-72-75.compute-1.amazonaws.com/phpmyadmin"

# Base efectiva
API_BASE = LOCAL_API_BASE if USE_LOCAL else REMOTE_API_BASE

# =========================================
# Endpoints (derivados de la misma base)
# =========================================
USUARIOS_URL       = f"{API_BASE}/usuarios.php"
ASIGNACIONES_URL   = f"{API_BASE}/asignaciones.php"
PACIENTES_URL      = f"{API_BASE}/pacientes.php"   # por si lo usás en otros flujos
JUEGOS_URL = f"{API_BASE}/juegos.php"


# URL principal que usa login.py
URL = f"{USUARIOS_URL}?login=true"

# =========================================
# (Opcional) headers/timeout comunes
# =========================================
REQUEST_TIMEOUT = 10
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
}

# =========================================
# Debug rápido al ejecutar directo
# =========================================
if __name__ == "__main__":
    print("USE_LOCAL:", USE_LOCAL)
    print("API_BASE:", API_BASE)
    print("USUARIOS_URL:", USUARIOS_URL)
    print("ASIGNACIONES_URL:", ASIGNACIONES_URL)
    print("PACIENTES_URL:", PACIENTES_URL)
    print("URL (login):", URL)
