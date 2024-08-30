import math
import random
import requests


import json
from datetime import datetime

import cv2
import mediapipe as mp
from pygame.locals import *

import globals
from background import Background
from constants import *
from enemy import Enemy
from events import *
from player import Player
from webcam import Webcam


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT])
        self.clock = pygame.time.Clock()
        self.running = True
        self.started = False

        #Hand Landmarks
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # Tiempo de impresion de ángulos
        self.last_angle_print_time = 0

        self.top_point_trace = []  # Lista para almacenar el rastro del punto superior
        self.angle_trace = []  # Lista para almacenar el rastro de los ángulos

        pygame.init()
        pygame.display.set_caption("Misiles")

        self.font = pygame.font.Font('freesansbold.ttf', 32)
        self.smaller_font = pygame.font.Font('freesansbold.ttf', 22)
        self.background = Background()

        self.initialize()

    """def initialize(self):
        self.start_time = pygame.time.get_ticks()
        self.last_frame_time = self.start_time
        self.player = Player()
        self.movement = 0

        #Timers
        self.enemy_timer = 1000
        pygame.time.set_timer(ADD_ENEMY, self.enemy_timer)

        self.enemies = pygame.sprite.Group()

        self.lost = False
        self.score = 0

        self.webcam = Webcam().start()
        
        self.max_hand_surf_height=0
        self.hand_left_x = 0
        self.hand_right_x = 0
        self.hand_top_y = 0
        self.hand_bottom_y = 0"""

    def initialize(self):
        self.start_time = pygame.time.get_ticks()  # Inicia el temporizador aquí
        self.last_frame_time = self.start_time
        self.player = Player()
        self.movement = 0

        # Timers
        self.enemy_timer = 1000
        pygame.time.set_timer(ADD_ENEMY, self.enemy_timer)

        self.enemies = pygame.sprite.Group()

        self.lost = False
        self.score = 0

        self.webcam = Webcam().start()

        self.max_hand_surf_height = 0
        self.hand_left_x = 0
        self.hand_right_x = 0
        self.hand_top_y = 0
        self.hand_bottom_y = 0

    """def update(self, delta_time):
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False

        if self.lost or not self.started:
            for event in events:
                #Cuando perdimos o no hemos empezado, ENTER comienza el juego
                if event.type == KEYDOWN and event.key == K_RETURN:
                    self.initialize()
                    self.started = True
        else:
            #Aumentar la velocidad segun el tiempo qu ehemos durado
            globals.game_speed = 1 + ( (pygame.time.get_ticks() - self.start_time) / 1000) * .1
            self.score = self.score + (delta_time * globals.game_speed)
          #  print(f"SCORE: {self.score} ")

            for event in events:
                if event.type == ADD_ENEMY:
                    #Agregar 1 o 2 enemigos
                    num = random.randint(1,2)
                    for e in range(num):
                        enemy = Enemy()
                        self.enemies.add(enemy)

                    #Actualizar el timer que define cuando aparecera un nuevo enemigo
                    self.enemy_timer = 1000 - ((globals.game_speed - 1) * 100)
                    if self.enemy_timer < 50: self.enemy_timer = 50
                    pygame.time.set_timer(ADD_ENEMY, int(self.enemy_timer))

            self.player.update(self.movement, delta_time)
            self.enemies.update(delta_time)
            self.process_collisions()
            self.background.update(delta_time)"""

    def update(self, delta_time):
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                elif event.key == K_RETURN:
                    if self.lost:
                        self.initialize()  # Reinicia el juego si se perdió
                    else:
                        self.started = True

        if self.lost or not self.started:
            for event in events:
                if event.type == KEYDOWN and event.key == K_RETURN:
                    self.initialize()
                    self.started = True
        else:
            globals.game_speed = 1 + ((pygame.time.get_ticks() - self.start_time) / 1000) * .1
            self.score = self.score + (delta_time * globals.game_speed)

            for event in events:
                if event.type == ADD_ENEMY:
                    num = random.randint(1, 2)
                    for e in range(num):
                        enemy = Enemy()
                        self.enemies.add(enemy)

                    self.enemy_timer = 1000 - ((globals.game_speed - 1) * 100)
                    if self.enemy_timer < 50:
                        self.enemy_timer = 50
                    pygame.time.set_timer(ADD_ENEMY, int(self.enemy_timer))

            self.player.update(self.movement, delta_time)
            self.enemies.update(delta_time)
            self.process_collisions()
            self.background.update(delta_time)

    def process_collisions(self):
        #Colisiones para este juego los hacemos con mascaras
        collide = pygame.sprite.spritecollide(self.player, self.enemies, False, pygame.sprite.collide_mask)
        if collide:
            self.lost = True
            self.save_game_data()  # Guardar los datos cuando el juego termine

    """def save_game_data(self):
        # Calcular el tiempo total jugado en segundos
        tiempo_total = (pygame.time.get_ticks() - self.start_time) / 1000

        # Obtener la fecha y hora de inicio en el formato deseado
        fecha_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Crear la estructura de datos a guardar
        data = {
            "tiempo_total": tiempo_total,
            "Score": round(self.score / 1000),  # Puntaje redondeado
            "fecha_inicio": fecha_inicio,
            "datos": [
                {"Tiempo": i * 100, "Angulo": angle}  # Suponiendo que imprimes ángulos cada 100ms
                for i, angle in enumerate(self.angle_trace)
            ]
        }

        #enviar data a la BD
        url = 'http://localhost/usuarios/juegos.php'
        # Envía la solicitud POST con los datos del juego
        response = requests.post(url, json=data)

        # Verifica la respuesta del servidor
        if response.status_code == 201:
            print("Juego creado correctamente")
        else:
            print(f"Error al crear el juego: {response.text}")

        # Generar un nombre de archivo único basado en la fecha y hora actual
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'game_data_{timestamp}.json'

        # Guardar los datos en un archivo JSON
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)"""

    def save_game_data(self):
        if not self.started:
            print("El juego no ha comenzado. No se guardarán los datos.")
            return

        # Calcular el tiempo total jugado en segundos
        tiempo_total = (pygame.time.get_ticks() - self.start_time) / 1000

        # Obtener la fecha y hora de inicio en el formato deseado
        fecha_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Crear la estructura de datos a guardar
        data = {
            "tiempo_total": tiempo_total,
            "Score": round(self.score / 1000),  # Puntaje redondeado
            "fecha_inicio": fecha_inicio,
            "datos": [
                {"Tiempo": i * 100, "Angulo": angle}  # Suponiendo que imprimes ángulos cada 100ms
                for i, angle in enumerate(self.angle_trace)
            ]
        }

        # Enviar data a la BD
        url = 'http://localhost/usuarios/juegos.php'
        response = requests.post(url, json=data)

        # Verificar la respuesta del servidor
        if response.status_code == 201:
            print("Juego creado correctamente")
        else:
            print(f"Error al crear el juego: {response.text}")

        # Generar un nombre de archivo único basado en la fecha y hora actual
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'game_data_{timestamp}.json'

        # Guardar los datos en un archivo JSON
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)

    def render(self):
        self.screen.fill((0,0,0))

        self.background.render(self.screen)
        
        if self.webcam.lastFrame is not None:
            self.render_camera()

        self.screen.blit(self.player.surf, self.player.rect)

        for e in self.enemies:
            self.screen.blit(e.surf, e.rect)

        display_score = round(self.score/1000)
        text_score = self.font.render('Score: ' + str(display_score), True, (255,255,255))
        scoreTextRect = text_score.get_rect()
        scoreTextRect.bottom = SCREEN_HEIGHT-5
        scoreTextRect.left = 5
        self.screen.blit(text_score, scoreTextRect)

        if self.lost:
            game_over_text = self.font.render('GAME OVER :(', True, (255,255,255), (0,0,0))
            game_over_text_rect = game_over_text.get_rect()
            game_over_text_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            self.screen.blit(game_over_text, game_over_text_rect)

            retry_text = self.smaller_font.render('Presiona Enter para reintentar', True, (200,200,200), (0,0,0))
            retry_text_rect = retry_text.get_rect()
            retry_text_rect.center = (SCREEN_WIDTH // 2, (SCREEN_HEIGHT // 2) + 40)
            self.screen.blit(retry_text, retry_text_rect)

        if not self.started:
            game_over_text = self.font.render('Presiona Enter para comenzar', True, (255,255,255), (0,0,0))
            game_over_text_rect = game_over_text.get_rect()
            game_over_text_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            self.screen.blit(game_over_text, game_over_text_rect)

        pygame.display.flip()

    def loop(self):
        with self.mp_hands.Hands(
                max_num_hands=1
            #static_image_mode=False,
            #max_num_faces=1,
            #min_detection_confidence=0.5,
            #refine_landmarks=True
        ) as self.hands:
            while self.running:
                if not self.lost:
                    if not self.webcam.ready():
                        continue
                    self.process_camera()

                time = pygame.time.get_ticks()
                delta_time = time - self.last_frame_time
                self.last_frame_time = time
                self.update(delta_time)
                self.render()
                self.clock.tick(60)
            pygame.quit()

    """def process_camera(self):
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
                for hand_landmarks in results.multi_hand_landmarks:

                    # Coordenadas de la mano (arriba y abajo)
                    top = (hand_landmarks.landmark[9].x, hand_landmarks.landmark[9].y)
                    bottom = (hand_landmarks.landmark[0].x, hand_landmarks.landmark[0].y)

                    # Obtener coordenadas del 'cuadrado' de la mano para poder mostrarlo en la pantalla después
                    self.hand_left_x = hand_landmarks.landmark[4].x
                    self.hand_right_x = hand_landmarks.landmark[20].x
                    self.hand_top_y = hand_landmarks.landmark[12].y
                    self.hand_bottom_y = hand_landmarks.landmark[0].y

                    # Dejar algo de espacio alrededor
                    self.hand_left_x = self.hand_left_x - .1
                    self.hand_right_x = self.hand_right_x + .1
                    self.hand_top_y = self.hand_top_y - .1
                    self.hand_bottom_y = self.hand_bottom_y + .1

                    # Convertir coordenadas a píxeles
                    top_pixel = (int(top[0] * self.webcam.width()), int(top[1] * self.webcam.height()))
                    bottom_pixel = (int(bottom[0] * self.webcam.width()), int(bottom[1] * self.webcam.height()))

                    # Calcular el ángulo entre la línea vertical y la línea que conecta el punto superior e inferior
                    delta_x = top_pixel[0] - bottom_pixel[0]
                    delta_y = top_pixel[1] - bottom_pixel[1]
                    radians = math.atan2(delta_y, delta_x)
                    degrees = math.degrees(radians)

                    # Ajustar el ángulo para que sea respecto a la línea vertical
                   # if degrees > 90:
                   #     degrees = 180 - degrees
                   # elif degrees < -90:
                   #     degrees = -180 - degrees

                    # Calcular el ángulo respecto a la línea vertical (eje y)
                    delta_x = top_pixel[0] - bottom_pixel[0]
                    delta_y = top_pixel[1] - bottom_pixel[1]
                    radians = math.atan2(delta_x, delta_y)  # Intercambia delta_x y delta_y
                    degrees = math.degrees(radians)

                    # Asegurar que el ángulo esté en el rango de 0 a 180 grados
                    # Giro antihorario --> ángulo positivo
                    # Giro horario --> ángulo negativo
                    
                    if degrees < 0:
                        degrees = 180 + degrees
                    else:
                        degrees = -180 + degrees

                    # Imprimir el ángulo en la consola cada 100 milisegundos
                    current_time = pygame.time.get_ticks()
                    print(f"Current time: {current_time} ms")
                    print(f"Last angle print time: {self.last_angle_print_time} ms")
                    if current_time - self.last_angle_print_time >= 100 and self.started:
                        print(f"Ángulo formado: {degrees} grados")
                        self.last_angle_print_time = current_time

                    # Agregar la posición actual del punto superior y el ángulo al rastro
                    self.top_point_trace.append(top_pixel)
                    self.angle_trace.append(degrees)

                    # Limitar el rastro a las últimas 50 posiciones (ajustar según sea necesario)
                    #if len(self.top_point_trace) > 50:
                     #   self.top_point_trace.pop(0)
                      #  self.angle_trace.pop(0)

                    # Dibujar el rastro del punto superior y las líneas de ángulo
                    overlay = self.webcam_image.copy()
                    for i in range(1, len(self.top_point_trace)):
                        start_point = self.top_point_trace[i - 1]
                        end_point = self.top_point_trace[i]
                        cv2.line(overlay, start_point, end_point, (0, 165, 255), 2)  # Naranja

                    # Aplicar la transparencia al overlay
                    alpha = 0.5  # Nivel de transparencia
                    cv2.addWeighted(overlay, alpha, self.webcam_image, 1 - alpha, 0, self.webcam_image)

                    # Dibujar la línea y los puntos
                    cv2.line(
                        self.webcam_image,
                        top_pixel,
                        bottom_pixel,
                        (0, 255, 0), 3
                    )

                    cv2.circle(self.webcam_image, top_pixel, 8, (0, 0, 255), -1)
                    cv2.circle(self.webcam_image, bottom_pixel, 8, (0, 0, 255), -1)

                    # Detección de ángulo
                    self.detect_hand_movement(top, bottom)

            k = cv2.waitKey(1) & 0xFF"""

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
                for hand_landmarks in results.multi_hand_landmarks:

                    # Coordenadas de la mano (arriba y abajo)
                    top = (hand_landmarks.landmark[9].x, hand_landmarks.landmark[9].y)
                    bottom = (hand_landmarks.landmark[0].x, hand_landmarks.landmark[0].y)

                    # Obtener coordenadas del 'cuadrado' de la mano para poder mostrarlo en la pantalla después
                    self.hand_left_x = hand_landmarks.landmark[4].x
                    self.hand_right_x = hand_landmarks.landmark[20].x
                    self.hand_top_y = hand_landmarks.landmark[12].y
                    self.hand_bottom_y = hand_landmarks.landmark[0].y

                    # Dejar algo de espacio alrededor
                    self.hand_left_x = self.hand_left_x - .1
                    self.hand_right_x = self.hand_right_x + .1
                    self.hand_top_y = self.hand_top_y - .1
                    self.hand_bottom_y = self.hand_bottom_y + .1

                    # Convertir coordenadas a píxeles
                    top_pixel = (int(top[0] * self.webcam.width()), int(top[1] * self.webcam.height()))
                    bottom_pixel = (int(bottom[0] * self.webcam.width()), int(bottom[1] * self.webcam.height()))

                    # Calcular el ángulo respecto a la línea vertical (eje y)
                    delta_x = top_pixel[0] - bottom_pixel[0]
                    delta_y = top_pixel[1] - bottom_pixel[1]
                    radians = math.atan2(delta_x, delta_y)
                    degrees = math.degrees(radians)

                    if degrees < 0:
                        degrees = 180 + degrees
                    else:
                        degrees = -180 + degrees

                    # Solo imprimir el ángulo si el juego ha comenzado
                    if self.started:
                        current_time = pygame.time.get_ticks()
                        if current_time - self.last_angle_print_time >= 100:
                            print(f"Ángulo formado: {degrees} grados")
                            self.last_angle_print_time = current_time

                            # Agregar la posición actual del punto superior y el ángulo al rastro
                            self.top_point_trace.append(top_pixel)
                            self.angle_trace.append(degrees)

                            # Limitar el rastro a las últimas 50 posiciones (ajustar según sea necesario)
                           # if len(self.top_point_trace) > 50:
                            #    self.top_point_trace.pop(0)
                            #    self.angle_trace.pop(0)

                    # Dibujar el rastro del punto superior y las líneas de ángulo
                    overlay = self.webcam_image.copy()
                    for i in range(1, len(self.top_point_trace)):
                        start_point = self.top_point_trace[i - 1]
                        end_point = self.top_point_trace[i]
                        cv2.line(overlay, start_point, end_point, (0, 165, 255), 2)  # Naranja

                    # Aplicar la transparencia al overlay
                    alpha = 0.5  # Nivel de transparencia
                    cv2.addWeighted(overlay, alpha, self.webcam_image, 1 - alpha, 0, self.webcam_image)

                    # Dibujar la línea y los puntos
                    cv2.line(
                        self.webcam_image,
                        top_pixel,
                        bottom_pixel,
                        (0, 255, 0), 3
                    )

                    cv2.circle(self.webcam_image, top_pixel, 8, (0, 0, 255), -1)
                    cv2.circle(self.webcam_image, bottom_pixel, 8, (0, 0, 255), -1)

                    # Detección de ángulo
                    self.detect_hand_movement(top, bottom)

    def detect_hand_movement(self, top, bottom):
        radians = math.atan2(bottom[1] - top[1], bottom[0] - top[0])
        degrees = math.degrees(radians)

        #Angulo de deteccion de 70 a 110 (-1 a 1)
        min_degrees = 70
        max_degrees = 110
        degree_range = max_degrees - min_degrees
        
        if degrees < min_degrees: degrees = min_degrees
        if degrees > max_degrees: degrees = max_degrees

        self.movement = ( ((degrees-min_degrees) / degree_range) * 2) - 1

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

    """def render_camera(self):
        # Limpiar coordenadas del cuadro de la cara
        if self.hand_left_x < 0: self.hand_left_x = 0
        if self.hand_right_x > 1: self.hand_right_x = 1
        if self.hand_top_y < 0: self.hand_top_y = 0
        if self.hand_bottom_y > 1: self.hand_bottom_y = 1

        hand_surf = pygame.image.frombuffer(self.webcam_image.tobytes(), self.webcam_image.shape[1::-1], "BGR")

        hand_rect = pygame.Rect(
            int(self.hand_left_x * self.webcam.width()),
            int(self.hand_top_y * self.webcam.height()),
            int(self.hand_right_x * self.webcam.width()) - int(self.hand_left_x * self.webcam.width()),
            int(self.hand_bottom_y * self.webcam.height()) - int(self.hand_top_y * self.webcam.height())
        )

        fixed_width = 200
        fixed_height = 200
        only_hand_surf = pygame.Surface((fixed_width, fixed_height))
        hand_image = hand_surf.subsurface(hand_rect).copy()
        hand_image = pygame.transform.scale(hand_image, (fixed_width, fixed_height))
        only_hand_surf.blit(hand_image, (0, 0))

        self.screen.blit(only_hand_surf, (0, 0))"""

