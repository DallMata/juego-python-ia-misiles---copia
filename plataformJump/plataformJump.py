import pygame
from pygame.locals import *
import random
from plataformJump.player import Player
from plataformJump.constants import *
from plataformJump.background import Background
from plataformJump.events import *
from plataformJump.gameplatform import GamePlatform
from plataformJump.money import Money
from plataformJump.enemy import Enemy
from plataformJump.shield import Shield
import globals
import math

import requests

import json
from datetime import datetime

import cv2
import mediapipe as mp
import math
from plataformJump.webcam import Webcam


class Game:
    def __init__(self, paciente):
        self.screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT])
        self.clock = pygame.time.Clock()
        self.running = True
        #self.background_image = pygame.image.load("sprites/KINEPLAY.png")  # Asegúrate de tener la imagen en el directorio
        self.pause_image = pygame.image.load('plataformJump/sprites/hand.png').convert_alpha()
        self.pause_image = pygame.transform.scale(self.pause_image, (200, 200))  # Ajusta el tamaño si es necesario
        #self.started = False

        #self.mp_face_mesh = mp.solutions.face_mesh
        #self.mp_drawing = mp.solutions.drawing_utils
        #self.mp_drawing_styles = mp.solutions.drawing_styles
        # Hand Landmarks
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        pygame.init()
        pygame.display.set_caption("Plataformas")

        # Tiempo de impresion de ángulos
        self.last_angle_print_time = 0

        # 2 fondos para manejar el paralaje. El detalle puedes leerlo
        # en background.py
        self.background1 = Background(True, .05, "2", 0)
        self.background2 = Background(False, .2, "3", 40)

        self.font = pygame.font.Font('freesansbold.ttf', 32)
        self.smaller_font = pygame.font.Font('freesansbold.ttf', 22)

        # Sonidillos
        self.powerup_sound = pygame.mixer.Sound("plataformJump/sound/powerup.wav")
        self.powerup_sound.set_volume(.1)
        self.death_sound = pygame.mixer.Sound("plataformJump/sound/grunt2.wav")

        self.paciente = paciente
        print(f'PACIENTE: {paciente}')
        self.dni = self.paciente.get('dni')
        print(f"DNI EN GAME:  {self.dni}")

        self.angle_trace_3 = []  # Lista para almacenar el rastro de los ángulos
        self.angle_trace_2 = []  # Lista para almacenar el rastro de los ángulos
        self.angle_trace_1 = []  # Lista para almacenar el rastro de los ángulos

        self.angle_trace_7 = []  # Lista para almacenar el rastro de los ángulos
        self.angle_trace_6 = []  # Lista para almacenar el rastro de los ángulos
        self.angle_trace_5 = []  # Lista para almacenar el rastro de los ángulos

        self.angle_trace_11 = []  # Lista para almacenar el rastro de los ángulos
        self.angle_trace_10 = []  # Lista para almacenar el rastro de los ángulos
        self.angle_trace_9 = []  # Lista para almacenar el rastro de los ángulos

        self.angle_trace_15 = []  # Lista para almacenar el rastro de los ángulos
        self.angle_trace_14 = []  # Lista para almacenar el rastro de los ángulos
        self.angle_trace_13 = []  # Lista para almacenar el rastro de los ángulos

        self.angle_trace_19 = []  # Lista para almacenar el rastro de los ángulos
        self.angle_trace_18 = []  # Lista para almacenar el rastro de los ángulos
        self.angle_trace_17 = []  # Lista para almacenar el rastro de los ángulos




        self.initialize()

    def initialize(self):
        self.player = Player()
        self.no_hand = False
        self.dead = False
        self.hand_turned = False
        self.paused = False

        self.prev_distance = None

        self.webcam = Webcam().start()

        self.handWasClosed=False

        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.1, min_tracking_confidence=0.1)

        self.platforms = []

        # La primera plataforma grande
        # Descomentar para tener una gigante inicial y probar cosas
        # platform = GamePlatform(2000, 0)
        platform = GamePlatform(20, 0)
        self.platforms.append(platform)
        self.difficulty = 1
        self.group_platforms = pygame.sprite.Group()
        self.group_platforms.add(platform)
        self.platformWillBeCreated = False

        self.start_time = pygame.time.get_ticks()
        self.last_frame_time = -1

        self.score = 0
        self.text_score = None
        self.text_score_rect = None

        # powerups = el dinero. se llama asi porque segun yo iba a agregar mas pero nunca lo hice
        self.powerups = []
        self.group_powerups = pygame.sprite.Group()
        pygame.time.set_timer(CREATE_NEW_MONEY, 1000)

        self.enemies = []
        self.group_enemies = pygame.sprite.Group()
        pygame.time.set_timer(CREATE_NEW_ENEMY, 15000)

        self.shields = []
        self.group_shields = pygame.sprite.Group()
        pygame.time.set_timer(CREATE_NEW_SHIELD, 10000)

        # Este tiene mas detalles de webcam para mostrar solo la boca en el cuadrito
        self.max_hand_surf_height = 0
        self.hand_left_x = 0
        self.hand_right_x = 0
        self.hand_top_y = 0
        self.hand_bottom_y = 0
    def save_game_data(self, tipo, angle_trace):
       # if not self.started:
       #     print("El juego no ha comenzado. No se guardarán los datos.")
       #     return

        # Calcular el tiempo total jugado en segundos
        tiempo_total = (pygame.time.get_ticks() - self.start_time) / 1000

        # Obtener la fecha y hora de inicio en el formato deseado
        fecha_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Generar un nombre de archivo único basado en la fecha y hora actual
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'game_data_{timestamp}.json'

        # Crear la estructura de datos a guardar
        data = {
            "tiempo": tiempo_total,
            "fecha": fecha_inicio,
            "puntaje": round(self.score / 1000),  # Puntaje redondeado
            "datos": [
                {"tiempo": i * 100,
                 "angulo": angle,
                 "tipo": tipo
                 }  # Suponiendo que imprimes ángulos cada 100ms
                for i, angle in enumerate(angle_trace)
            ],
            "dni": self.dni,
        }

        # Enviar data a la BD
        url = 'http://localhost/usuarios/juegos.php'
        response = requests.post(url, json=data)

        # Verificar la respuesta del servidor
        if response.status_code == 201:
            print("Juego creado correctamente")
        else:
            print(f"Error al crear el juego: {response.text}")
    def update(self, delta_time):
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False

        if self.dead:
            #self.save_game_data()
            for event in events:
               if event.type == KEYDOWN and (event.key == K_RETURN or event.key == K_ESCAPE):
                   # indice
                    self.save_game_data(29, self.angle_trace_7)
                    self.save_game_data(28, self.angle_trace_6)
                    self.save_game_data(27, self.angle_trace_5)

                   # medio
                    self.save_game_data(33, self.angle_trace_11)
                    self.save_game_data(32, self.angle_trace_10)
                    self.save_game_data(31, self.angle_trace_9)

                   # anular
                    self.save_game_data(37, self.angle_trace_15)
                    self.save_game_data(36, self.angle_trace_14)
                    self.save_game_data(35, self.angle_trace_13)

                   # meñique
                    self.save_game_data(41, self.angle_trace_19)
                    self.save_game_data(40, self.angle_trace_18)
                    self.save_game_data(39, self.angle_trace_17)

                   # pulgar
                    self.save_game_data(25, self.angle_trace_3)
                    self.save_game_data(24, self.angle_trace_2)
                    self.save_game_data(23, self.angle_trace_1)

                    self.initialize()
               elif event.type == pygame.QUIT:
                   # indice
                   self.save_game_data(29, self.angle_trace_7)
                   self.save_game_data(28, self.angle_trace_6)
                   self.save_game_data(27, self.angle_trace_5)

                   # medio
                   self.save_game_data(33, self.angle_trace_11)
                   self.save_game_data(32, self.angle_trace_10)
                   self.save_game_data(31, self.angle_trace_9)

                   # anular
                   self.save_game_data(37, self.angle_trace_15)
                   self.save_game_data(36, self.angle_trace_14)
                   self.save_game_data(35, self.angle_trace_13)

                   # meñique
                   self.save_game_data(41, self.angle_trace_19)
                   self.save_game_data(40, self.angle_trace_18)
                   self.save_game_data(39, self.angle_trace_17)

                   # pulgar
                   self.save_game_data(25, self.angle_trace_3)
                   self.save_game_data(24, self.angle_trace_2)
                   self.save_game_data(23, self.angle_trace_1)
                   self.running = False


        if self.dead or self.no_hand or self.hand_turned:
            return

        for event in events:
            # Descomentar estos primeros 2 si quieres que la barra
            # espaciadora NO brinque
            if event.type == KEYDOWN:
                if event.key == K_SPACE:
                    self.player.jump()
            elif event.type == KEYUP:
                if event.key == K_SPACE:
                    self.player.cancel_jump()
            elif event.type == HAND_CLOSED:
                self.player.jump()
            elif event.type == HAND_OPENED:
                self.player.cancel_jump()
            elif event.type == CREATE_NEW_PLATFORM:
                self.platformWillBeCreated = False
                # Basar el tamano en la dificultad
                min = 1
                if self.difficulty <= 3:
                    min = 3
                max = 12 - self.difficulty
                if max < 4:
                    max = 4
                tileNumber = random.randrange(min, max)

                # Basar el espacio entre plataformas en la dificultad
                min_space = 90 + (self.difficulty * 2)
                if min_space > 150:
                    min_space = 150
                max_space = 200 + (self.difficulty * 2)
                if max_space > 350:
                    max_space = 350

                space = random.randrange(min_space, max_space)

                platform = GamePlatform(tileNumber, SCREEN_WIDTH + space)
                self.platforms.append(platform)
                self.group_platforms.add(platform)
            elif event.type == CREATE_NEW_MONEY:
                money = Money()
                self.powerups.append(money)
                self.group_powerups.add(money)

                # Calculos para ver cuando crear mas dinero, segun la dificultad
                min_time = 4000 - self.difficulty * 500
                if min_time < 2000:
                    min_time = 2000
                max_time = 10000 - self.difficulty * 500
                if max_time < 4000:
                    max_time = 4000

                # TODO al final ni los use HOHOH revisar
                pygame.time.set_timer(CREATE_NEW_MONEY, random.randint(3000, 10000))
            elif event.type == CREATE_NEW_ENEMY:
                enemy = Enemy()
                self.enemies.append(enemy)
                self.group_enemies.add(enemy)

                # Cuando crear un nuevo enemigo? Basado en la dificultad
                min_time = 4000 - self.difficulty * 500
                if min_time < 2000:
                    min_time = 2000
                max_time = 10000 - self.difficulty * 500
                if max_time < 4000:
                    max_time = 4000
                pygame.time.set_timer(CREATE_NEW_ENEMY, random.randint(min_time, max_time))
            elif event.type == CREATE_NEW_SHIELD:
                shield = Shield()
                self.shields.append(shield)
                self.group_shields.add(shield)
                min_time = 4000 - self.difficulty * 500
                if min_time < 2000:
                    min_time = 2000
                max_time = 10000 - self.difficulty * 500
                if max_time < 4000:
                    max_time = 4000

                # TODO usar min_time y max_time, ajustarlos XD
                pygame.time.set_timer(CREATE_NEW_SHIELD, random.randint(10000, 20000))

        if not self.player.dead:
            self.background1.update(delta_time)
            self.background2.update(delta_time)
            self.player.update(delta_time, self.group_platforms, self.group_powerups, self.group_enemies,
                               self.group_shields)
            if self.player.dead or self.player.rect.top > SCREEN_HEIGHT:
                if self.player.shield:
                    # Moriste pero tienes escudo? No morir!
                    self.player.shield_save()
                else:
                    # No tenias escudo. Dead
                    self.dead = True
                    pygame.mixer.Sound.play(self.death_sound)

            if self.player.addScore > 0:
                self.score += (self.player.addScore * 1000)
                self.player.addScore = 0
                pygame.mixer.Sound.play(self.powerup_sound)

            for platform in self.platforms:
                platform.update(delta_time)

            self.group_powerups.update(delta_time)
            self.group_enemies.update(delta_time)
            self.group_shields.update(delta_time)

            # Generar nueva plataforma?
            if (SCREEN_WIDTH - self.platforms[-1].rect.right > 0) and not self.platformWillBeCreated:
                self.platformWillBeCreated = True
                pygame.event.post(pygame.event.Event(CREATE_NEW_PLATFORM))

            # Hacer mas dificil
            seconds = int((pygame.time.get_ticks() - self.start_time) / 1000)
            self.difficulty = int(1 + (seconds / 10))
            globals.game_speed = 1 + (self.difficulty * .2)

            # Score
            self.score += globals.game_speed * delta_time
            self.text_score = self.font.render('Score: ' + str(int(self.score / 1000)), True, (255, 255, 255))
            self.text_score_rect = self.text_score.get_rect()
            self.text_score_rect.y = 10
            self.text_score_rect.x = (SCREEN_WIDTH // 2) - (self.text_score_rect.width // 2)

    def render(self):
        self.screen.fill((92, 89, 92))

        # Fondo
        self.background1.render(self.screen)
        self.background2.render(self.screen)

        if self.webcam.lastFrame is not None:
            self.render_camera()

        # Plataformas
        for platform in self.platforms:
            self.screen.blit(platform.surf, platform.rect)

        self.screen.blit(self.player.surf, self.player.rect)
        if (self.player.shield):
            self.screen.blit(self.player.shieldSurf, self.player.shieldRect)

        for powerup in self.group_powerups:
            self.screen.blit(powerup.surf, powerup.rect)
        for enemy in self.group_enemies.sprites():
            self.screen.blit(enemy.surf, enemy.rect)
        for shield in self.group_shields:
            self.screen.blit(shield.surf, shield.rect)

        if self.text_score is not None:
            self.screen.blit(self.text_score, self.text_score_rect)

        if self.dead:
            self.dead = self.font.render('GAME OVER :(', True, (255, 255, 255), (0, 0, 0))
            dead_rect = self.dead.get_rect()
            dead_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            self.screen.blit(self.dead, dead_rect)
            self.retry = self.smaller_font.render('Presiona enter para reintentar', True, (200, 200, 200), (0, 0, 0))
            retry_rect = self.retry.get_rect()
            retry_rect.center = (SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 40)
            self.screen.blit(self.retry, retry_rect)
        elif self.hand_turned:
            # Mostrar mensaje de pausa si la mano está girada
            paused_text = self.font.render('Juego Pausado', True, (255, 255, 255), (0, 0, 0))
            paused_rect = paused_text.get_rect()
            paused_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            self.screen.blit(paused_text, paused_rect)

            resume_text = self.smaller_font.render('Endereza la mano para continuar', True, (200, 200, 200), (0, 0, 0))
            resume_rect = resume_text.get_rect()
            resume_rect.center = (SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 40)
            self.screen.blit(resume_text, resume_rect)

            # Posición de la imagen de pausa
            pause_image_rect = self.pause_image.get_rect(center=((SCREEN_WIDTH // 2), (SCREEN_HEIGHT // 2) - 150))
            self.screen.blit(self.pause_image, pause_image_rect)

        elif self.no_hand:
            # Mostrar mensaje de pausa si la mano está girada
            paused_text = self.font.render('Juego Pausado', True, (255, 255, 255), (0, 0, 0))
            paused_rect = paused_text.get_rect()
            paused_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            self.screen.blit(paused_text, paused_rect)

            resume_text = self.smaller_font.render('Muestra tu mano a la cámara continuar', True, (200, 200, 200), (0, 0, 0))
            resume_rect = resume_text.get_rect()
            resume_rect.center = (SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 40)
            self.screen.blit(resume_text, resume_rect)

        pygame.display.flip()

    def render_camera(self):
        # Limpiar coordenadas del cuadro de la cara
        if self.hand_left_x < 0: self.hand_left_x = 0
        if self.hand_right_x > 1: self.hand_right_x = 1
        if self.hand_top_y < 0: self.hand_top_y = 0
        if self.hand_bottom_y > 1: self.hand_bottom_y = 1

        if self.webcam_image is not None:
            # Convertir coordenadas de la mano a píxeles
            hand_center_x = int(self.webcam.width() * self.hand_left_x + (
                    self.hand_right_x - self.hand_left_x) * self.webcam.width() / 2)
            hand_center_y = int(self.webcam.height() * self.hand_top_y + (
                    self.hand_bottom_y - self.hand_top_y) * self.webcam.height() / 2)

            # Definir el tamaño del recorte
            crop_size = 200  # Tamaño del recorte en píxeles
            half_crop_size = crop_size // 2

            # Calcular las coordenadas del recorte
            x1 = max(hand_center_x - half_crop_size, 0)
            x2 = min(hand_center_x + half_crop_size, self.webcam_image.shape[1])
            y1 = max(hand_center_y - half_crop_size, 0)
            y2 = min(hand_center_y + half_crop_size, self.webcam_image.shape[0])

            # Ajustar el tamaño del recorte si el recorte está en los bordes de la imagen
            if x2 - x1 < crop_size:
                if x1 == 0:
                    x2 = min(crop_size, self.webcam_image.shape[1])
                elif x2 == self.webcam_image.shape[1]:
                    x1 = max(self.webcam_image.shape[1] - crop_size, 0)
            if y2 - y1 < crop_size:
                if y1 == 0:
                    y2 = min(crop_size, self.webcam_image.shape[0])
                elif y2 == self.webcam_image.shape[0]:
                    y1 = max(self.webcam_image.shape[0] - crop_size, 0)

            # Extraer la región de interés (ROI)
            roi = self.webcam_image[y1:y2, x1:x2]

            # Crear una superficie de Pygame a partir de la ROI
            hand_surf = pygame.image.frombuffer(roi.tobytes(), roi.shape[1::-1], "BGR")

            # Crear un rectángulo para posicionar la imagen de la mano
            hand_rect = pygame.Rect(0, 0, crop_size, crop_size)

            # Mostrar la imagen de la mano en la pantalla
            self.screen.blit(hand_surf, (0, 0))

    def loop(self):
        with self.mp_hands.Hands(
                max_num_hands=1
            #static_image_mode=False,
            #max_num_faces=1,
            #min_detection_confidence=0.5,
            #refine_landmarks=True
        ) as self.hands:
            while self.running:
                while self.running:
                    if not self.webcam.ready():
                        continue
                    time = pygame.time.get_ticks()
                    if self.last_frame_time == -1:
                        delta_time = 1
                    else:
                        delta_time = time - self.last_frame_time

                    self.last_frame_time = time
                    self.process_camera()
                    self.update(delta_time)
                    self.render()
                    self.clock.tick(60)
            pygame.quit()

    def process_camera(self):
        image = self.webcam.read()
        if image is not None:
            image.flags.writeable = False
            image = cv2.flip(image, 1)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            results = self.hands.process(image)
            self.webcam_image = image
            if results.multi_hand_landmarks is not None:
                self.no_hand = False
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(
                        image,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=1, circle_radius=1),
                        self.mp_drawing.DrawingSpec(color=(150, 150, 150), thickness=1)
                    )

                    # Obtener las coordenadas de los landmarks
                    # muñeca
                    landmark_0 = (hand_landmarks.landmark[0].x, hand_landmarks.landmark[0].y)

                    # Indice
                    landmark_8 = (hand_landmarks.landmark[8].x, hand_landmarks.landmark[8].y)
                    landmark_7 = (hand_landmarks.landmark[7].x, hand_landmarks.landmark[7].y)
                    landmark_6 = (hand_landmarks.landmark[6].x, hand_landmarks.landmark[6].y)
                    landmark_5 = (hand_landmarks.landmark[5].x, hand_landmarks.landmark[5].y)

                    # Medio
                    landmark_12 = (hand_landmarks.landmark[12].x, hand_landmarks.landmark[12].y)
                    landmark_11 = (hand_landmarks.landmark[11].x, hand_landmarks.landmark[11].y)
                    landmark_10 = (hand_landmarks.landmark[10].x, hand_landmarks.landmark[10].y)
                    landmark_9 = (hand_landmarks.landmark[9].x, hand_landmarks.landmark[9].y)

                    # Anular
                    landmark_16 = (hand_landmarks.landmark[16].x, hand_landmarks.landmark[16].y)
                    landmark_15 = (hand_landmarks.landmark[15].x, hand_landmarks.landmark[15].y)
                    landmark_14 = (hand_landmarks.landmark[14].x, hand_landmarks.landmark[14].y)
                    landmark_13 = (hand_landmarks.landmark[13].x, hand_landmarks.landmark[13].y)

                    # Meñique
                    landmark_20 = (hand_landmarks.landmark[20].x, hand_landmarks.landmark[20].y)
                    landmark_19 = (hand_landmarks.landmark[19].x, hand_landmarks.landmark[19].y)
                    landmark_18 = (hand_landmarks.landmark[18].x, hand_landmarks.landmark[18].y)
                    landmark_17 = (hand_landmarks.landmark[17].x, hand_landmarks.landmark[17].y)

                    # Pulgar
                    landmark_4 = (hand_landmarks.landmark[4].x, hand_landmarks.landmark[4].y)
                    landmark_3 = (hand_landmarks.landmark[3].x, hand_landmarks.landmark[3].y)
                    landmark_2 = (hand_landmarks.landmark[2].x, hand_landmarks.landmark[2].y)
                    landmark_1 = (hand_landmarks.landmark[1].x, hand_landmarks.landmark[1].y)


                    # Convertir las coordenadas a píxeles
                    # Muñeca
                    landmark_0_pixel = (
                        int(landmark_0[0] * self.webcam.width()), int(landmark_0[1] * self.webcam.height()))

                    # Indice
                    landmark_8_pixel = (
                        int(landmark_8[0] * self.webcam.width()), int(landmark_8[1] * self.webcam.height()))
                    landmark_7_pixel = (
                        int(landmark_7[0] * self.webcam.width()), int(landmark_7[1] * self.webcam.height()))
                    landmark_6_pixel = (
                        int(landmark_6[0] * self.webcam.width()), int(landmark_6[1] * self.webcam.height()))
                    landmark_5_pixel = (
                        int(landmark_5[0] * self.webcam.width()), int(landmark_5[1] * self.webcam.height()))

                    # Medio
                    landmark_12_pixel = (
                        int(landmark_12[0] * self.webcam.width()), int(landmark_12[1] * self.webcam.height()))
                    landmark_11_pixel = (
                        int(landmark_11[0] * self.webcam.width()), int(landmark_11[1] * self.webcam.height()))
                    landmark_10_pixel = (
                        int(landmark_10[0] * self.webcam.width()), int(landmark_10[1] * self.webcam.height()))
                    landmark_9_pixel = (
                        int(landmark_9[0] * self.webcam.width()), int(landmark_9[1] * self.webcam.height()))

                    # Anular
                    landmark_16_pixel = (
                        int(landmark_16[0] * self.webcam.width()), int(landmark_16[1] * self.webcam.height()))
                    landmark_15_pixel = (
                        int(landmark_15[0] * self.webcam.width()), int(landmark_15[1] * self.webcam.height()))
                    landmark_14_pixel = (
                        int(landmark_14[0] * self.webcam.width()), int(landmark_14[1] * self.webcam.height()))
                    landmark_13_pixel = (
                        int(landmark_13[0] * self.webcam.width()), int(landmark_13[1] * self.webcam.height()))

                    # Meñique
                    landmark_20_pixel = (
                        int(landmark_20[0] * self.webcam.width()), int(landmark_20[1] * self.webcam.height()))
                    landmark_19_pixel = (
                        int(landmark_19[0] * self.webcam.width()), int(landmark_19[1] * self.webcam.height()))
                    landmark_18_pixel = (
                        int(landmark_18[0] * self.webcam.width()), int(landmark_18[1] * self.webcam.height()))
                    landmark_17_pixel = (
                        int(landmark_17[0] * self.webcam.width()), int(landmark_17[1] * self.webcam.height()))

                    # Pulgar
                    landmark_4_pixel = (
                        int(landmark_4[0] * self.webcam.width()), int(landmark_4[1] * self.webcam.height()))
                    landmark_3_pixel = (
                        int(landmark_3[0] * self.webcam.width()), int(landmark_3[1] * self.webcam.height()))
                    landmark_2_pixel = (
                        int(landmark_2[0] * self.webcam.width()), int(landmark_2[1] * self.webcam.height()))
                    landmark_1_pixel = (
                        int(landmark_1[0] * self.webcam.width()), int(landmark_1[1] * self.webcam.height()))

                    # Obtener coordenadas del 'cuadrado' de la mano para poder mostrarlo en la pantalla después
                    self.hand_left_x = hand_landmarks.landmark[5].x
                    self.hand_right_x = hand_landmarks.landmark[17].x
                    self.hand_top_y = hand_landmarks.landmark[9].y
                    self.hand_bottom_y = hand_landmarks.landmark[0].y

                    # Dejar algo de espacio alrededor
                    self.hand_left_x = self.hand_left_x - .3
                    self.hand_right_x = self.hand_right_x + .3
                    self.hand_top_y = self.hand_top_y - .3
                    self.hand_bottom_y = self.hand_bottom_y + .3

                    # Calculo de ángulos del dedo Indice
                    angle_index_finger_7 = self.calculate_angle(landmark_6_pixel, landmark_7_pixel, landmark_8_pixel)
                    angle_index_finger_6 = self.calculate_angle(landmark_5_pixel, landmark_6_pixel, landmark_7_pixel)
                    angle_index_finger_5 = self.calculate_angle(landmark_0_pixel, landmark_5_pixel, landmark_6_pixel)

                    # Calculo de ángulos del dedo Medio
                    angle_index_finger_11 = self.calculate_angle(landmark_10_pixel, landmark_11_pixel, landmark_12_pixel)
                    angle_index_finger_10 = self.calculate_angle(landmark_9_pixel, landmark_10_pixel, landmark_11_pixel)
                    angle_index_finger_9 = self.calculate_angle(landmark_0_pixel, landmark_9_pixel, landmark_10_pixel)

                    # Calculo de ángulos del dedo Anular
                    angle_index_finger_15 = self.calculate_angle(landmark_14_pixel, landmark_15_pixel, landmark_16_pixel)
                    angle_index_finger_14 = self.calculate_angle(landmark_13_pixel, landmark_14_pixel, landmark_15_pixel)
                    angle_index_finger_13 = self.calculate_angle(landmark_0_pixel, landmark_13_pixel, landmark_17_pixel)

                    # Calculo de ángulos del dedo Meñique
                    angle_index_finger_19 = self.calculate_angle(landmark_18_pixel, landmark_19_pixel, landmark_20_pixel)
                    angle_index_finger_18 = self.calculate_angle(landmark_17_pixel, landmark_18_pixel, landmark_19_pixel)
                    angle_index_finger_17 = self.calculate_angle(landmark_0_pixel, landmark_17_pixel, landmark_18_pixel)

                    # Calculo de ángulos del dedo Pulgar
                    angle_index_finger_3 = self.calculate_angle(landmark_2_pixel, landmark_3_pixel, landmark_4_pixel)
                    angle_index_finger_2 = self.calculate_angle(landmark_1_pixel, landmark_2_pixel, landmark_3_pixel)
                    angle_index_finger_1 = self.calculate_angle(landmark_0_pixel, landmark_1_pixel, landmark_2_pixel)

                    if self.check_hand_orientation(hand_landmarks):
                        self.hand_turned = True  # Frenar juego si la mano no está de frente
                    elif not self.dead:

                        # Solo imprimir el ángulo si se detecta la mano y no está de costado y no estoy muerto
                        current_time = pygame.time.get_ticks()
                        if current_time - self.last_angle_print_time >= 200:
                            #print(f"Ángulo formado: {angle_index_finger_7} grados")
                            self.last_angle_print_time = current_time

                            # Agregar la posición actual del ángulo al rastro
                            self.angle_trace_7.append(angle_index_finger_7)
                            self.angle_trace_6.append(angle_index_finger_6)
                            self.angle_trace_5.append(angle_index_finger_5)

                            self.angle_trace_11.append(angle_index_finger_11)
                            self.angle_trace_10.append(angle_index_finger_10)
                            self.angle_trace_9.append(angle_index_finger_9)

                            self.angle_trace_15.append(angle_index_finger_15)
                            self.angle_trace_14.append(angle_index_finger_14)
                            self.angle_trace_13.append(angle_index_finger_13)

                            self.angle_trace_19.append(angle_index_finger_19)
                            self.angle_trace_18.append(angle_index_finger_18)
                            self.angle_trace_17.append(angle_index_finger_17)

                            self.angle_trace_3.append(angle_index_finger_3)
                            self.angle_trace_2.append(angle_index_finger_2)
                            self.angle_trace_1.append(angle_index_finger_1)

                    self.hand_turned = False


                    if ((not self.handWasClosed and landmark_8_pixel[1] < landmark_5_pixel[1])
                            and (landmark_12_pixel[1] < landmark_9_pixel[1])
                           and (landmark_16_pixel[1] < landmark_13_pixel[1])
                           and (landmark_20_pixel[1] < landmark_17_pixel[1])):#Es verdadero cuando cierro todos los dedos

                        pygame.event.post(pygame.event.Event(HAND_CLOSED))
                        #print("SALTO CIERRO")
                        self.handWasClosed = True
                    elif ((self.handWasClosed and landmark_8_pixel[1] > landmark_6_pixel[1])
                            and (landmark_12_pixel[1] > landmark_9_pixel[1])
                           and (landmark_16_pixel[1] > landmark_13_pixel[1])
                           and (landmark_20_pixel[1] > landmark_17_pixel[1])):#Es verdadero cuando abro todos los dedos
                        pygame.event.post(pygame.event.Event(HAND_CLOSED))
                        #print("CANCELO SALTO ABRO")
                        self.handWasClosed = False

            else:
                self.no_hand = True

            k = cv2.waitKey(1) & 0xFF


    def calculate_angle(self, point_a, point_b, point_c):
        # Calcula los vectores AB y BC
        vector_ab = (point_b[0] - point_a[0], point_b[1] - point_a[1])
        vector_bc = (point_c[0] - point_b[0], point_c[1] - point_b[1])

        # Producto punto de los vectores AB y BC
        dot_product = vector_ab[0] * vector_bc[0] + vector_ab[1] * vector_bc[1]

        # Magnitudes de los vectores AB y BC
        magnitude_ab = math.sqrt(vector_ab[0] ** 2 + vector_ab[1] ** 2)
        magnitude_bc = math.sqrt(vector_bc[0] ** 2 + vector_bc[1] ** 2)

        # Evita la división por cero
        if magnitude_ab == 0 or magnitude_bc == 0:
            return None

        # Condición para un ángulo de cero cuando la punta del dedo está alineada o más atrás que la base
        if point_c[0] <= point_a[0]:  # Ajusta según el eje y si la cámara está orientada diferente
            return 0.0

        # Limita el valor del coseno al rango [-1, 1]
        cos_angle = max(-1, min(1, dot_product / (magnitude_ab * magnitude_bc)))

        # Calcula el ángulo en radianes
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)

        return angle_deg

    def check_hand_orientation(self, landmarks):
        # Landmarks base del índice y del meñique
        index_base = landmarks.landmark[5]
        pinky_base = landmarks.landmark[17]

        # Calcula la diferencia en el eje X entre la base del índice y la base del meñique
        x_difference = abs(index_base.x - pinky_base.x)

        # Define un umbral para la alineación "de frente" (ajusta según sea necesario)

        if x_difference < 0.03:  # Umbral pequeño significa alineación
            return True
        else:
            return False

