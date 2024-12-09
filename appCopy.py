# app.py
from login import Login
from gameMenu import Menu

def main():
    login = Login()
    login.run()

    #Game().loop()

    paciente = login.get_paciente()
    if paciente:
        print("Paciente listo para el juego:", paciente)
        menu = Menu(paciente)
        #game = Game(paciente).loop()  # Pasa el objeto paciente
        #game.run()

if __name__ == "__main__":
    main()

"""
def main():
    # Inicia el proceso de autenticación del paciente
    login = Login()
    login.run()
    paciente = login.get_paciente()

    # Verifica si el paciente se ha autenticado correctamente
    if paciente:
        print("Paciente listo para el juego:", paciente)

        # Inicia el menú con el paciente autenticado
        menu = Menu(paciente)
        selected_app = menu.run()  # Obtiene la aplicación seleccionada

        # Si el usuario selecciona una aplicación, inicia el juego correspondiente
        if selected_app:
            if selected_app == "Space Evation":
                from spaceEvation.spaceEvation import Game as SpaceEvationGame
                game = SpaceEvationGame(paciente)
            elif selected_app == "Platform Jump":
                from plataformJump.plataformJump import Game as PlatformJumpGame
                game = PlatformJumpGame(paciente)

            game.loop()  # Inicia el juego

if __name__ == "__main__":
    main()

"""
