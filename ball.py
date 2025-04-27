import pygame
import win32gui
import win32con
import win32api
import time
from PIL import ImageGrab
import json
import os

def hex_to_rgb(hex_color):
    hex_color = hex_color.strip().lstrip("#").lstrip("0x")
    if len(hex_color) != 6:
        raise ValueError("Invalid hex color format")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


# Configs
WIDTH, HEIGHT = 1980, 1080
BALL_RADIUS = 20
BALL_COLOR = (100, 100, 100)
HIGHLIGHT_COLOR = (255, 0, 0)
BACKGROUND_COLOR = (0, 0, 0)
TICK_INTERVAL = 0.6  # seconds
CYCLE_LENGTH = 8
SAVE_FILE = "overlay_settings.json"

# Initialize
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("OSRS Overlay")

# Make window transparent and click-through
hwnd = pygame.display.get_wm_info()['window']
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 300, 300, WIDTH, HEIGHT, 0)
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                       win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) |
                       win32con.WS_EX_LAYERED)
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*BACKGROUND_COLOR), 0, win32con.LWA_COLORKEY)

# Initialize balls
balls = []
start_x = (WIDTH - 5 * 60) // 2
y = HEIGHT // 2
for i in range(6):
    balls.append({
        "pos": [start_x + i * 60, y],
        "dragging": False
    })

# Setup which ticks to highlight which balls
tick_sequence = [0, 1, 2, 3, 4, 5, None, None]
tick_index = 0
last_tick_time = time.time()

# Sync settings
sync_pixel = None
target_color = None
prev_color = None

def load_settings():
    global sync_pixel, target_color
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            for i in range(min(len(data.get("balls", [])), len(balls))):
                balls[i]["pos"] = data["balls"][i]
            sync_pixel = data.get("sync_pixel")
            target_color = data.get("target_color")
def save_settings():
    data = {
        "balls": [ball["pos"] for ball in balls],
        "sync_pixel": sync_pixel,
        "target_color": target_color
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)

# Get pixel color at global screen position
def get_pixel_color(x, y):
    screenshot = ImageGrab.grab(bbox=(x, y, x + 1, y + 1))
    return screenshot.getpixel((0, 0))

# Load saved state
load_settings()

#TODO fix loading and analyzing colors
target_color = hex_to_rgb("#FF00FF")

#Begin the main loop
clock = pygame.time.Clock()
running = True

while running:
    screen.fill(BACKGROUND_COLOR)

    # Sync detection
    if sync_pixel:
        current_color = get_pixel_color(*sync_pixel)
        if prev_color is not None and current_color == target_color and prev_color != target_color:
            tick_index = 0
            last_tick_time = time.time()
        prev_color = current_color

    #Move to next ball
    now = time.time()
    if now - last_tick_time >= TICK_INTERVAL:
        tick_index = (tick_index + 1) % CYCLE_LENGTH
        last_tick_time = now

    current_highlight = tick_sequence[tick_index]

    # Draw balls
    for i, ball in enumerate(balls):
        x, y = ball["pos"]
        color = HIGHLIGHT_COLOR if i == current_highlight else BALL_COLOR
        pygame.draw.circle(screen, color, (int(x), int(y)), BALL_RADIUS)

    pygame.display.update()
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mods = pygame.key.get_mods()
            if event.button == 1 and mods & pygame.KMOD_ALT and mods & pygame.KMOD_SHIFT:
                sync_pixel = win32api.GetCursorPos()
                target_color = get_pixel_color(*sync_pixel)
                prev_color = None
                print(f"Sync pixel set to {sync_pixel}, color: {target_color}")
            else:
                mouse_pos = pygame.mouse.get_pos()
                for ball in balls:
                    bx, by = ball["pos"]
                    dist = ((mouse_pos[0] - bx) ** 2 + (mouse_pos[1] - by) ** 2) ** 0.5
                    if dist <= BALL_RADIUS:
                        ball["dragging"] = True
                        ball["offset"] = (bx - mouse_pos[0], by - mouse_pos[1])
                        break

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                for ball in balls:
                    ball["dragging"] = False

        elif event.type == pygame.MOUSEMOTION:
            mouse_pos = pygame.mouse.get_pos()
            for ball in balls:
                if ball["dragging"]:
                    offset_x, offset_y = ball["offset"]
                    ball["pos"][0] = mouse_pos[0] + offset_x
                    ball["pos"][1] = mouse_pos[1] + offset_y

# Save settings on exit
save_settings()
pygame.quit()
