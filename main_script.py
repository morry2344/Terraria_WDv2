import tkinter as tk
from tkinter import filedialog
import json

import pygame
import lihzahrd


#----------------------------------------------------------------------------------------------#
# CONFIG
#----------------------------------------------------------------------------------------------#
WINDOW_SIZE = (1920, 1080)  # starting window size in pixels
DEFAULT_TILE = 16           # starting tile pixel size
PAN_SPEED    = 32           # pixels per keypress
ZOOM_STEP    = 2            # tile-size change per wheel click
MIN_TILE     = 2            # smallest zoom
MAX_TILE     = 32           # largest zoom

LIQUID_OFFSET = 692
CHUNK_TILES = 64            # number of tiles in a chunk (64x64)

PANEL_WIDTH  = 350          # width of the right panel
PADDING      = 8            # padding around text in the panel
LINE_SPACING = 6            # spacing between lines in the panel

#----------------------------------------------------------------------------------------------#
# HELPERS
#----------------------------------------------------------------------------------------------#
#gets the metadata of a world
def extract_metadata(world):

    md = {}
    md["name"] = getattr(world, "name", None)
    md["seed"] = getattr(getattr(world, "generator", None), "seed", None)
    md["size"] = (world.size.x, world.size.y)
    md["hardmode"] = getattr(world, "is_hardmode", None)
    md["corruption"] = getattr(world.world_evil, "name", None)
    md["difficulty"] = getattr(world.difficulty, "name", None)
    
    if getattr(world, "spawn_point", None):
        md["spawn"] = (world.spawn_point.x, world.spawn_point.y)
    else:
        md["spawn"] = None
    if hasattr(world, "id"):
        md["id"] = world.id
    if hasattr(world, "version"):
        md["version"] = world.version
    if hasattr(world, "creation_time"):
        ct = world.creation_time
        md["created"] = ct.isoformat() if hasattr(ct, "isoformat") else ct
    return md

#gets the wdl. file path
def pick_world_file():

    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select a Terraria .wld file",
        filetypes=[("Terraria Worlds","*.wld")],
    )
    root.destroy()
    return path or ""

#load the palette.json
def load_palettes(json_path="palette.json"):

    data = json.load(open(json_path, encoding="utf-8"))
    tile_pal, tile_names = {}, {}

    for k,v in data["tiles"].items():
        key = int(k) if k.isdigit() else k
        tile_pal[key]   = tuple(v["color"])
        tile_names[key] = v["name"]
    wall_pal, wall_names = {}, {}

    for k,v in data["walls"].items():
        wid = int(k)
        wall_pal[wid]   = tuple(v["color"])
        wall_names[wid] = v["name"]
    return tile_pal, tile_names, wall_pal, wall_names

#draw a chunk of the world
chunk_cache = {}
def get_chunk(world, tile_pal, wall_pal, tile_size, cx, cy):

    key = (tile_size, cx, cy)
    if key in chunk_cache:
        return chunk_cache[key]

    surf = pygame.Surface((CHUNK_TILES*tile_size, CHUNK_TILES*tile_size), pygame.SRCALPHA)
    ox, oy = cx*CHUNK_TILES, cy*CHUNK_TILES

    for dy in range(CHUNK_TILES):
        for dx in range(CHUNK_TILES):
            x, y = ox + dx, oy + dy
            if x >= world.size.x or y >= world.size.y:
                continue
            t = world.tiles[x, y]

            #wall
            if t.wall:
                col = wall_pal.get(t.wall.type.value, (30,30,30))
                pygame.draw.rect(
                    surf, col,
                    (dx*tile_size, dy*tile_size, tile_size, tile_size)
                )

            #liquid
            #draw any non‐None liquid by numeric ID (693–696)
            if t.liquid and t.liquid.type.value > 0:
                lid = t.liquid.type.value             # 1=Water,2=Lava,3=Honey,4=Shimmer
                tid = 692 + lid                       
                col = tile_pal.get(tid, (200,200,200))
                pygame.draw.rect(
                    surf, col,
                    (dx * tile_size,
                    dy * tile_size,
                    tile_size,
                    tile_size)
                )

            #block
            if t.block:
                col = tile_pal.get(t.block.type.value, (200,200,200))
                pygame.draw.rect(
                    surf, col,
                    (dx*tile_size, dy*tile_size, tile_size, tile_size)
                )

    chunk_cache[key] = surf
    return surf

#draw the whole world
def draw_world(screen, world, tile_pal, wall_pal, cam_x, cam_y, tile_size):
    screen.fill((40,40,40))
    sw, sh = screen.get_size()
    chunk_px = CHUNK_TILES * tile_size

    start_cx = cam_x  // chunk_px
    start_cy = cam_y  // chunk_px
    end_cx   = (cam_x + sw) // chunk_px
    end_cy   = (cam_y + sh) // chunk_px

    sx = int(start_cx)
    sy = int(start_cy)
    ex = int(end_cx) + 1
    ey = int(end_cy) + 1

    for cy in range(sy, ey):
        for cx in range(sx, ex):
            chunk = get_chunk(world, tile_pal, wall_pal, tile_size, cx, cy)
            px = cx * chunk_px - cam_x
            py = cy * chunk_px - cam_y
            screen.blit(chunk, (px, py))

#----------------------------------------------------------------------------------------------#
# MAIN RUN
#----------------------------------------------------------------------------------------------#
def main():

    world_path = pick_world_file()
    
    #loading screen
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("Terraria Map Viewer")

    screen.fill((0,0,0))
    loader_font = pygame.font.SysFont(None, 48)
    msg = loader_font.render("Loading world… please wait", True, (255,255,255))
    rect = msg.get_rect(center=(screen.get_width()//2, screen.get_height()//2))
    screen.blit(msg, rect)
    pygame.display.flip()

    try:
        world = lihzahrd.World.create_from_file(world_path)
    except Exception as e:
        print("Failed to load world:", e)
        return

    #load everything else
    tile_pal, tile_names, wall_pal, wall_names = load_palettes("palette.json")
    metadata = extract_metadata(world)

    #start main window
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption("Terraria Map Viewer")
    clock = pygame.time.Clock()

    #fonts
    font = pygame.font.SysFont("Consolas", 32, bold=True)
    font1 = pygame.font.SysFont("Consolas", 26, bold=True)
    #font2 = pygame.font.SysFont("Consolas", 18, bold=False)

    #camera
    spawn = world.spawn_point
    cam_x = max(0, spawn.x*DEFAULT_TILE - WINDOW_SIZE[0]//2)
    cam_y = max(0, spawn.y*DEFAULT_TILE - WINDOW_SIZE[1]//2)
    tile_size = DEFAULT_TILE


    #render loop
    running        = True
    dragging       = False

    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            #mouse drag
            elif ev.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((ev.w, ev.h), pygame.RESIZABLE)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                dragging = True
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                dragging = False
            elif ev.type == pygame.MOUSEMOTION and dragging:
                dx, dy = ev.rel
                cam_x = max(0, cam_x - dx)
                cam_y = max(0, cam_y - dy)

            #zoom
            elif ev.type == pygame.MOUSEWHEEL:

                mx, my   = pygame.mouse.get_pos()
                old_ts    = tile_size
                world_x   = (mx + cam_x) / old_ts
                world_y   = (my + cam_y) / old_ts

                new_tile_size = max(
                    MIN_TILE,
                    min(MAX_TILE, tile_size + ev.y * ZOOM_STEP)
                )

                if new_tile_size != tile_size:
                    chunk_cache.clear()
                    tile_size = new_tile_size

                cam_x = world_x * tile_size - mx
                cam_y = world_y * tile_size - my



        #clamp to world bounds
        world_px_w = world.size.x * tile_size
        world_px_h = world.size.y * tile_size
        cam_x = min(max(cam_x, 0), max(0, world_px_w - screen.get_width()))
        cam_y = min(max(cam_y, 0), max(0, world_px_h - screen.get_height()))

        screen.fill((80, 80, 80))
        draw_world(screen, world, tile_pal, wall_pal, cam_x, cam_y, tile_size)

        #hover and coords
        mx, my = pygame.mouse.get_pos()
        tx = int((mx + cam_x) // tile_size)
        ty = int((my + cam_y) // tile_size)
        sw, sh  = screen.get_size()
        
        if (mx <= sw - PANEL_WIDTH or my >= 400):
            if 0 <= tx < world.size.x and 0 <= ty < world.size.y:
                t = world.tiles[tx, ty]
                hover_text = "Air Block"

                if t.block:
                    hover_id = t.block.type.value
                    hover_text = tile_names.get(hover_id, f"Tile {hover_id}")

                elif t.liquid and t.liquid.type.value > 0:
                    #map 1–4 → 693–696
                    hover_id = LIQUID_OFFSET + t.liquid.type.value
                    hover_text = tile_names.get(hover_id, f"Tile {hover_id}")

                elif t.wall:
                    wid = t.wall.type.value
                    hover_text = wall_names.get(wid, f"Wall {wid}")

            else: hover_text = None
        else: hover_text = None

        #text top right
        sw, sh = screen.get_size()
        x0 = sw - PANEL_WIDTH

        panel_rect = pygame.Rect(x0, 0, PANEL_WIDTH, 400)
        pygame.draw.rect(screen, (60, 60, 60), panel_rect)

        col1_x = x0 + PADDING
        col2_x = x0 + PANEL_WIDTH // 2

        y = PADDING
        for key, val in metadata.items():

            key_surf = font1.render(str(key).title(), True, (230,230,230))
            screen.blit(key_surf, (col1_x, y))

            val_surf = font1.render(str(val), True, (230,230,230))
            screen.blit(val_surf, (col2_x, y))
            y += font1.get_linesize() + LINE_SPACING

        pygame.draw.line(screen, (100,100,100), (x0, 0), (x0, 400), 2)

        #text left top
        info_text  = f"Zoom={tile_size}  Pos=({int(tx)}, {int(ty)})"
        info_surf  = font.render(info_text, True, (255,255,255))
        hover_surf = font.render(hover_text, True, (255,255,255))

        padding = 5
        spacing = 10
        text_w  = info_surf.get_width() + spacing + hover_surf.get_width()
        text_h  = max(info_surf.get_height(), hover_surf.get_height())
        bg_w    = text_w + padding * 2
        bg_h    = text_h + padding * 2

        bg_x, bg_y = 10, 10
        bg_rect    = pygame.Rect(bg_x, bg_y, bg_w, bg_h)

        pygame.draw.rect(screen, (30, 30, 30),    bg_rect)
        pygame.draw.rect(screen, (200, 200, 200), bg_rect, 1) 

        screen.blit(info_surf,  (bg_x + padding, bg_y + padding))
        screen.blit(hover_surf, (bg_x + padding + info_surf.get_width() + spacing, bg_y + padding))


        #----------------------------------------------------------------------------------------------#
        pygame.display.flip()
        clock.tick(60)
 
    pygame.quit()

if __name__ == "__main__":
    main()
