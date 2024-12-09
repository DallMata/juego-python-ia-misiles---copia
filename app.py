# app.py
#from spaceEvation.spaceEvation import Game
from plataformJump.plataformJump import Game as plataformJump
from spaceEvation.spaceEvation import Game as spaceEvation
from login import Login
from gameMenu import Menu


def main():
    # Inicia el proceso de autenticación del paciente
    login = Login()
    login.run()
    paciente = login.get_paciente()

    # Verifica si el paciente se ha autenticado correctamente
    if paciente:
        print("Paciente listo para el juego 2:", paciente)

        while True:
            menu = Menu(paciente)
            selected_app = menu.run()  # Devuelve la aplicación seleccionada o None

            if selected_app is None:  # Volver al login
                print("Volviendo al login...")
                break  # Salir del bucle del menú y volver al login

            # Inicia el juego seleccionado
            if selected_app == "Space Evation":
                game = spaceEvation(paciente)
                game.loop()  # Inicia el juego
            elif selected_app == "Plataform Jump":
                game = plataformJump(paciente)
                game.loop()  # Inicia el juego
        main()

if __name__ == "__main__":
    main()

