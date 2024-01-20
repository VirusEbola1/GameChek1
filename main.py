import sys
import pygame
from pygame.locals import *

from pynput import keyboard
import time
import os
from random import randint as rand

pygame.init()

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('Your Game Title')
pressed_keys = set()

font = pygame.font.SysFont(None, 36)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

TICK_SLEEP = 0.2
CLOUDS_UPDATE = 100
TREE_UPDATE = 20
FIRE_UPDATE = 200
MAP_W, MAP_H = 20, 10

def randbool(r, mxr):
    t = rand(0, mxr)
    return t <= r

def randcell(w, h):
    tw = rand(0, w - 1)
    th = rand(0, h - 1)
    return (th, tw)

def randcell2(x, y):
    moves = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    t = rand(0, 3)
    dx, dy = moves[t][0], moves[t][1]
    return (x + dx, y + dy)

class Clouds:
    def __init__(self, w, h, r=2, mxr=20, g=5, mxg=10):
        self.w = w
        self.h = h
        self.cells = [[0 for i in range(w)] for j in range(h)]
        self.update(r, mxr, g, mxg)

    def update(self, r=1, mxr=20, g=1, mxg=10):
        for i in range(self.h):
            for j in range(self.w):
                if randbool(r, mxr):
                    self.cells[i][j] = 1
                    if randbool(g, mxg):
                        self.cells[i][j] = 2
                else:
                    self.cells[i][j] = 0

    def export_data(self):
        return {"cells": self.cells}

    def import_data(self, data):
        self.cells = data["cells"] or [[0 for i in range(self.w)] for j in range(self.h)]

class Map:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.cells = [[0 for i in range(w)] for j in range(h)]
        self.generate_forest(5, 10)
        self.generate_river(10)
        self.generate_river(10)
        self.generate_upgrade_shop()
        self.generate_hospital()

    def check_bounds(self, x, y):
        if (x < 0 or y < 0 or x >= self.h or y >= self.w):
            return False
        return True

    def print_map(self, helico, clouds):
        for ri in range(self.h):
            for ci in range(self.w):
                cell = self.cells[ri][ci]
                if clouds.cells[ri][ci] == 1:
                    window.blit(CLOUD_SYMBOL, (ci * 40, ri * 40))
                elif clouds.cells[ri][ci] == 2:
                    window.blit(LIGHTNING_SYMBOL, (ci * 40, ri * 40))
                elif helico.x == ri and helico.y == ci:
                    window.blit(HELICOPTER_SYMBOL, (ci * 40, ri * 40))
                elif 0 <= cell < len(CELL_SYMBOLS):
                    window.blit(CELL_SYMBOLS[cell], (ci * 40, ri * 40))

    def generate_river(self, l):
        rc = randcell(self.w, self.h)
        rx, ry = rc[0], rc[1]
        self.cells[rx][ry] = 2
        while l > 0:
            rc2 = randcell2(rx, ry)
            rx2, ry2 = rc2[0], rc2[1]
            if self.check_bounds(rx2, ry2):
                self.cells[rx2][ry2] = 2
                rx, ry = rx2, ry2
                l -= 1

    def generate_forest(self, r, mxr):
        for ri in range(self.h):
            for ci in range(self.w):
                if randbool(r, mxr):
                    self.cells[ri][ci] = 1

    def generate_tree(self):
        c = randcell(self.w, self.h)
        cx, cy = c[0], c[1]
        if self.cells[cx][cy] == 0:
            self.cells[cx][cy] = 1

    def generate_upgrade_shop(self):
        c = randcell(self.w, self.h)
        cx, cy = c[0], c[1]
        self.cells[cx][cy] = 4

    def generate_hospital(self):
        c = randcell(self.w, self.h)
        cx, cy = c[0], c[1]
        if self.cells[cx][cy] != 4:
            self.cells[cx][cy] = 3
        else:
            self.generate_hospital()

    def add_fire(self):
        c = randcell(self.w, self.h)
        cx, cy = c[0], c[1]
        if self.cells[cx][cy] == 1:
            self.cells[cx][cy] = 5

    def update_fires(self):
        for ri in range(self.h):
            for ci in range(self.w):
                cell = self.cells[ri][ci]
                if cell == 5:
                    self.cells[ri][ci] = 0
        for i in range(30):
            self.add_fire()

    def process_helicopter(self, helico, clouds):
        c = self.cells[helico.x][helico.y]
        d = clouds.cells[helico.x][helico.y]
        if c == 2:
            helico.tank = helico.mxtank
        if c == 5 and helico.tank > 0:
            helico.tank -= 1
            helico.score += TREE_BONUS
            self.cells[helico.x][helico.y] = 1
        if c == 4 and helico.score >= UPGRADE_HELICOPTER_COST:
            helico.mxtank += 1
            helico.score -= UPGRADE_HELICOPTER_COST
        if c == 3 and helico.score >= LIFE_RECOVERY_COST:
            helico.lives += 10
            helico.score -= LIFE_RECOVERY_COST
        if d == 2:
            helico.lives -= 1
            if helico.lives <= 0:
                helico.game_over()

    def export_data(self):
        return {"cells": self.cells}

    def import_data(self, data):
        self.cells = data["cells"] or [[0 for i in range(self.w)] for j in range(self.h)]

class Helicopter:
    def __init__(self, w, h):
        rc = randcell(w, h)
        rx, ry = rc[0], rc[1]
        self.x = rx
        self.y = ry
        self.h = h
        self.w = w
        self.tank = 0
        self.mxtank = 1
        self.score = 0
        self.lives = 20
        self.game_over_flag = False  # Флаг, который будет сигнализировать о завершении игры

    def export_data(self):
        return {"x": self.x, "y": self.y, "tank": self.tank,
                "mxtank": self.mxtank, "score": self.score, "lives": self.lives}

    def import_data(self, data):
        self.x = data["x"]
        self.y = data["y"]
        self.tank = data["tank"]
        self.mxtank = data["mxtank"]
        self.score = data["score"]
        self.lives = data["lives"]

    def move(self, dx, dy):
        self.x = max(0, min(self.x + dx, self.h - 1))
        self.y = max(0, min(self.y + dy, self.w - 1))

    def print_stats(self):
        text = font.render(
            f"Tank: {self.tank}/{self.mxtank}, Score: {self.score}, Lives: {self.lives}",
            True,
            BLACK
        )
        window.blit(text, (10, WINDOW_HEIGHT - 40))

    def game_over(self):
        self.game_over_flag = True  # Установка флага о завершении игры

    def draw_game_over(self):
        game_over_text = font.render("Game Over", True, (255, 0, 0))
        restart_text = font.render("Press R to Restart", True, (255, 0, 0))
        window.blit(game_over_text, (WINDOW_WIDTH // 2 - game_over_text.get_width() // 2, WINDOW_HEIGHT // 2 - FONT_SIZE))
        window.blit(restart_text, (WINDOW_WIDTH // 2 - restart_text.get_width() // 2, WINDOW_HEIGHT // 2 + FONT_SIZE))
        pygame.display.update()

# Constants
TREE_BONUS = 100
UPGRADE_HELICOPTER_COST = 2000
LIFE_RECOVERY_COST = 3000
FONT_SIZE = 48

# Load symbols
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")

HELICOPTER_SYMBOL = pygame.image.load(os.path.join(IMAGE_DIR, "helicopter_symbol.png"))
CLOUD_SYMBOL = pygame.image.load(os.path.join(IMAGE_DIR, "cloud_symbol.png"))
LIGHTNING_SYMBOL = pygame.image.load(os.path.join(IMAGE_DIR, "lightning_symbol.png"))

CELL_SYMBOLS = [
    pygame.image.load(os.path.join(IMAGE_DIR, "0_symbol.png")),  # поле
    pygame.image.load(os.path.join(IMAGE_DIR, "1_symbol.png")),  # дерево
    pygame.image.load(os.path.join(IMAGE_DIR, "2_symbol.png")),  # река
    pygame.image.load(os.path.join(IMAGE_DIR, "3_symbol.png")),  # госпиталь
    pygame.image.load(os.path.join(IMAGE_DIR, "4_symbol.png")),  # апгрейд шоп
    pygame.image.load(os.path.join(IMAGE_DIR, "5_symbol.png")),] # огонь

# Main Loop
TICK_SLEEP = 0.1
CLOUDS_UPDATE = 100
TREE_UPDATE = 30
FIRE_UPDATE = 75
MAP_W, MAP_H = 20, 10

field = Map(MAP_W, MAP_H)
clouds = Clouds(MAP_W, MAP_H)
helico = Helicopter(MAP_W, MAP_H)
tick = 1

MOVES = {'w': (-1, 0), 'd': (0, 1), 's': (1, 0), 'a': (0, -1)}

def process_key(key):
    global helico, tick, clouds, field
    try:
        c = key.char.lower()
        if c in MOVES.keys():
            dx, dy = MOVES[c][0], MOVES[c][1]
            helico.move(dx, dy)
    except AttributeError:
        pass

listener = keyboard.Listener(on_press=None, on_release=process_key,)
listener.start()

# Main Game Loop
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                helico = Helicopter(MAP_W, MAP_H)
                field = Map(MAP_W, MAP_H)
                clouds = Clouds(MAP_W, MAP_H)
                tick = 1
            elif event.key in MOVES.keys():
                pressed_keys.add(event.key)
        elif event.type == pygame.KEYUP:
            if event.key in MOVES.keys():
                pressed_keys.remove(event.key)

    if helico.lives > 0:
        window.fill(WHITE)

        # Обработка нажатия клавиш
        for key, (dx, dy) in MOVES.items():
            if key in pressed_keys:
                helico.move(dx, dy)

        field.process_helicopter(helico, clouds)
        helico.print_stats()
        field.print_map(helico, clouds)
        print("TICK", tick)
        tick += 1
        time.sleep(TICK_SLEEP)
        if tick % TREE_UPDATE == 0:
            field.generate_tree()
        if tick % FIRE_UPDATE == 0:
            field.update_fires()
        if tick % CLOUDS_UPDATE == 0:
            clouds.update()
    else:
        helico.draw_game_over()

    pygame.display.update()

