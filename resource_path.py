from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def resource_path(relative_path: str) -> str:
    """
    Devuelve una ruta absoluta válida tanto ejecutando con Python
    como dentro de un paquete generado con PyInstaller.
    """
    return str(BASE_DIR / relative_path)