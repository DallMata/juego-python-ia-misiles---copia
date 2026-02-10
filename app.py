# app.py
#from spaceEvation.spaceEvation import Game
from plataformJump.plataformJump import Game as plataformJump
from spaceEvation.spaceEvation import Game as spaceEvation
from login import Login
from gameMenu import Menu


def _safe_int(v, default=None):
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except (ValueError, TypeError):
        return default


def _clamp_difficulty(title, dif):
    if dif is None:
        return None
    if title == "Space Evation":
        return max(1, min(5, dif))
    if title == "Plataform Jump":
        return max(1, min(3, dif))
    return dif  # fallback


def _start_game(title, GameClass, paciente, asignacion):
    # Leer dificultad desde la asignación (si viene)
    dificultad = None
    if isinstance(asignacion, dict):
        dificultad = _safe_int(asignacion.get("dificultad"), None)

    dificultad = _clamp_difficulty(title, dificultad)

    # Intentar distintas firmas para no romper compatibilidad
    game = None
    try:
        # Preferido: pasar toda la asignación y la dificultad explícita
        if dificultad is not None:
            game = GameClass(paciente, asignacion=asignacion, dificultad=dificultad)
        else:
            game = GameClass(paciente, asignacion=asignacion)
    except TypeError:
        try:
            # Plan B: sólo dificultad
            if dificultad is not None:
                game = GameClass(paciente, dificultad=dificultad)
            else:
                game = GameClass(paciente)
        except TypeError:
            # Plan C: compat total (sólo paciente)
            game = GameClass(paciente)

    if dificultad is not None:
        print(f"[{title}] Dificultad aplicada:", dificultad)

    game.loop()


def main():
    # Autenticación
    login = Login()
    login.run()
    paciente = login.get_paciente()

    if paciente:
        print("Paciente listo para el juego 2:", paciente)

        while True:
            menu = Menu(paciente)
            selected = menu.run()  # Puede ser None o (title, asignacion_row)

            if selected is None:
                print("Volviendo al login...")
                break

            # Compat: aceptar string viejo o tupla nueva
            if isinstance(selected, tuple):
                title, asignacion = selected
            else:
                title, asignacion = selected, None

            # Iniciar juego según selección
            if title == "Space Evation":
                _start_game(title, spaceEvation, paciente, asignacion)
            elif title == "Plataform Jump":
                _start_game(title, plataformJump, paciente, asignacion)

        # Si querés volver a loguear tras salir del menú, podés volver a llamar main()
        # main()


if __name__ == "__main__":
    main()
