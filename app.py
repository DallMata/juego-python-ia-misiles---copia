# app.py
from game import Game
from login import Login

def main():
    login = Login()
    login.run()
   # Game().loop()

    paciente = login.get_paciente()
    if paciente:
        print("Paciente listo para el juego:", paciente)
        game = Game(paciente).loop()  # Pasa el objeto paciente
        game.run()

if __name__ == "__main__":
    main()
