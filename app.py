# app.py
from game import Game
from login import Login

def main():
    login = Login()
    login.run()
    Game().loop()

if __name__ == "__main__":
    main()
