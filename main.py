import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import random
import math
from PIL import Image
import os
import heapq
import time

class DungeonGenerator:
    def __init__(self, width=51, height=51):
        self.width = width if width % 2 == 1 else width + 1
        self.height = height if height % 2 == 1 else height + 1
        self.grid = [[1 for _ in range(self.width)] for _ in range(self.height)]
        # Initialize attributes that will be set in generate_dungeon
        self.rooms = []
        self.torch_positions = []
        self.chest_positions = []
        self.skeletons = []

    def generate_dungeon(self):
        # 1. Start with a grid of walls
        self.grid = [[1 for _ in range(self.width)] for _ in range(self.height)]
        
        # 2. Carve out small/medium rooms FIRST
        num_rooms = random.randint(4, 8)
        self.rooms = []  # Store room information for chest placement
        attempts = 0
        max_attempts = 100
        while len(self.rooms) < num_rooms and attempts < max_attempts:
            room_w = random.randint(3, 6)
            room_h = random.randint(3, 6)
            x = random.randrange(1, self.width - room_w - 1, 1)
            y = random.randrange(1, self.height - room_h - 1, 1)
            # Check for overlap (only within the actual room area)
            overlap = False
            for i in range(x, x+room_w):
                for j in range(y, y+room_h):
                    if self.grid[j][i] == 0:
                        overlap = True
                        break
                if overlap:
                    break
            if not overlap:
                for i in range(x, x+room_w):
                    for j in range(y, y+room_h):
                        self.grid[j][i] = 0
                # Store room information for chest placement
                self.rooms.append((x, y, room_w, room_h))
            attempts += 1
        
        # 3. Generate maze with wider corridors, connecting rooms
        start_x, start_y = 1, 1
        self.grid[start_y][start_x] = 0
        self.grid[start_y][start_x + 1] = 0  # Make corridor 2 tiles wide
        stack = [(start_x, start_y)]
        while stack:
            x, y = stack[-1]
            neighbors = []
            for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
                nx, ny = x+dx, y+dy
                if 1 <= nx < self.width-2 and 1 <= ny < self.height-1 and self.grid[ny][nx] == 1:
                    neighbors.append((nx, ny))
            if neighbors:
                nx, ny = random.choice(neighbors)
                # Carve 2-tile-wide corridor
                self.grid[(y+ny)//2][(x+nx)//2] = 0
                self.grid[(y+ny)//2][(x+nx)//2 + 1] = 0  # Second tile
                self.grid[ny][nx] = 0
                self.grid[ny][nx + 1] = 0  # Second tile
                stack.append((nx, ny))
            else:
                stack.pop()
        
        # 4. Connect rooms to maze by carving a door
        for x, y, room_w, room_h in self.rooms:
            doors = []
            for i in range(x, x+room_w):
                if y > 1 and self.grid[y-2][i] == 0:
                    doors.append((i, y-1))
                if y+room_h < self.height-1 and self.grid[y+room_h+1][i] == 0:
                    doors.append((i, y+room_h))
            for j in range(y, y+room_h):
                if x > 1 and self.grid[j][x-2] == 0:
                    doors.append((x-1, j))
                if x+room_w < self.width-1 and self.grid[j][x+room_w+1] == 0:
                    doors.append((x+room_w, j))
            if doors:
                door_x, door_y = random.choice(doors)
                self.grid[door_y][door_x] = 0
        
        # 5. Place torches on walls
        self.torch_positions = []  # Will store (x, z, dx, dz, face_x, face_z)
        
        # Find wall positions that are adjacent to walkable areas
        wall_positions = []
        for z in range(len(self.grid)):
            for x in range(len(self.grid[0])):
                if self.grid[z][x] == 1:  # Wall
                    # Check if this wall is adjacent to a walkable area
                    for dx, dz in [(-1,0), (1,0), (0,-1), (0,1)]:
                        nx, nz = x + dx, z + dz
                        if (0 <= nx < len(self.grid[0]) and 
                            0 <= nz < len(self.grid) and 
                            self.grid[nz][nx] == 0):  # Adjacent to walkable area
                            # Calculate face position (slightly offset from wall)
                            face_x = x + 0.5 + dx * 0.55  # Offset slightly from wall face
                            face_z = z + 0.5 + dz * 0.55
                            wall_positions.append((x, z, dx, dz, face_x, face_z))
        
        print(f"Found {len(wall_positions)} wall positions adjacent to walkable areas")
        
        # Place torches with minimum spacing
        min_torch_distance = 3.0  # Minimum 3 tiles between torches
        placed_torches = []
        for wall_pos in wall_positions:
            x, z, dx, dz, face_x, face_z = wall_pos
            # Check if this position is far enough from existing torches
            too_close = False
            for torch_pos in placed_torches:
                torch_x, torch_z, _, _, _, _ = torch_pos
                distance = math.sqrt((x - torch_x)**2 + (z - torch_z)**2)
                if distance < min_torch_distance:
                    too_close = True
                    break
            
            if not too_close and random.random() < 0.6:  # 60% chance to place torch
                placed_torches.append((x, z, dx, dz, face_x, face_z))
                self.torch_positions.append((x, z, dx, dz, face_x, face_z))
        
        print(f"Placed {len(self.torch_positions)} torches at positions: {self.torch_positions[:5]}...")  # Show first 5
        
        # 6. Place chests in rooms
        self.chest_positions = []  # Will store (x, z, center_x, center_z)
        for room_x, room_y, room_w, room_h in self.rooms:
            # 90% chance to place a chest in each room
            if random.random() < 0.9:
                # Try to place chest in center of room
                chest_x = room_x + room_w // 2
                chest_z = room_y + room_h // 2
                if self.grid[chest_z][chest_x] == 0:
                    center_x = chest_x + 0.5
                    center_z = chest_z + 0.5
                    self.chest_positions.append((chest_x, chest_z, center_x, center_z))
                else:
                    # Find nearest open tile in the room
                    found = False
                    for dz in range(room_h):
                        for dx in range(room_w):
                            tx = room_x + dx
                            tz = room_y + dz
                            if self.grid[tz][tx] == 0:
                                center_x = tx + 0.5
                                center_z = tz + 0.5
                                self.chest_positions.append((tx, tz, center_x, center_z))
                                found = True
                                break
                        if found:
                            break
        
        print(f"Generated {len(self.rooms)} rooms, placed {len(self.chest_positions)} chests")
        
        # 7. Place skeletons
        self.skeletons = []
        player_spawn_x, player_spawn_z = 25, 25  # Default spawn (ignore Y)
        safe_radius = 8.0
        for room_x, room_y, room_w, room_h in self.rooms:
            if random.random() < 0.8:  # 80% chance to spawn a skeleton in a chest room
                skel_x = room_x + room_w // 2
                skel_z = room_y + room_h // 2
                if self.grid[skel_z][skel_x] == 0:
                    center_x = skel_x + 0.5
                    center_z = skel_z + 0.5
                    dist_to_player = math.sqrt((center_x - player_spawn_x)**2 + (center_z - player_spawn_z)**2)
                    if dist_to_player > safe_radius:
                        npc_type = self._choose_npc_type()
                        self.skeletons.append(NPC(skel_x, skel_z, center_x, center_z, npc_type=npc_type))
        # Random chance to spawn skeletons elsewhere
        for z in range(1, self.height-1):
            for x in range(1, self.width-1):
                if self.grid[z][x] == 0 and random.random() < 0.01:
                    center_x = x + 0.5
                    center_z = z + 0.5
                    dist_to_player = math.sqrt((center_x - player_spawn_x)**2 + (center_z - player_spawn_z)**2)
                    if dist_to_player > safe_radius:
                        npc_type = self._choose_npc_type()
                        self.skeletons.append(NPC(x, z, center_x, center_z, npc_type=npc_type))
        print(f"Placed {len(self.skeletons)} skeletons")
        
        return self.grid

    def _choose_npc_type(self):
        r = random.random()
        if r < 0.7:
            return "ghoul"
        elif r < 0.7 + 0.5:
            return "skeleton"
        elif r < 0.7 + 0.5 + 0.3:
            return "ghost"
        else:
            return "skeleton"  # fallback

class DungeonRenderer:
    def __init__(self):
        self.texture_id = None
        self.floor_texture_id = None
        self.ceiling_texture_id = None
        self.torch_texture_id = None
        self.chest_texture_id = None
        self.interact_texture_id = None
        self.weapon_texture_id = None  # Hotbar icon (rusty)
        self.held_weapon_texture_id = None  # Held weapon (rusty)
        self.skeleton_sword_texture_id = None  # Hotbar icon (skeleton)
        self.held_skeleton_sword_texture_id = None  # Held weapon (skeleton)
        self.health_bar_texture_id = None
        self.health_fill_texture_id = None
        self.mana_bar_texture_id = None
        self.mana_fill_texture_id = None
        self.skeleton_texture_id = None
        self.ghoul_texture_id = None
        self.ghost_texture_id = None
        self.potion_health_texture_id = None
        self.potion_magic_texture_id = None
        self.scroll_fire_texture_id = None
        self.scroll_magic_texture_id = None
        self.spell_fire_texture_id = None
        self.spell_magic_texture_id = None  # Add this line
        self.fireball_texture_id = None
        self.magicball_texture_id = None  # Add this line
        self.key_texture_id = None
        self.load_texture()
        
    def load_texture(self):
        """Load the stone, floor, ceiling, and torch textures"""
        try:
            # Load stone texture for walls
            image = Image.open("assets/stone.png")
            image = image.convert("RGBA")
            image_data = image.tobytes()
            self.texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image_data)
            print(f"Stone texture loaded: {image.width}x{image.height}")
            
            # Load floor texture
            floor_image = Image.open("assets/floor.png")
            floor_image = floor_image.convert("RGBA")
            floor_image_data = floor_image.tobytes()
            self.floor_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.floor_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, floor_image.width, floor_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, floor_image_data)
            print(f"Floor texture loaded: {floor_image.width}x{floor_image.height}")
            
            # Load ceiling texture
            ceiling_image = Image.open("assets/ceiling.png")
            ceiling_image = ceiling_image.convert("RGBA")
            ceiling_image_data = ceiling_image.tobytes()
            self.ceiling_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.ceiling_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ceiling_image.width, ceiling_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, ceiling_image_data)
            print(f"Ceiling texture loaded: {ceiling_image.width}x{ceiling_image.height}")
            
            # Load torch texture (flip vertically for OpenGL)
            torch_image = Image.open("assets/torch.png")
            torch_image = torch_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            torch_image = torch_image.convert("RGBA")
            torch_image_data = torch_image.tobytes()
            self.torch_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.torch_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, torch_image.width, torch_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, torch_image_data)
            print(f"Torch texture loaded: {torch_image.width}x{torch_image.height}")
            
            # Load chest texture (flip vertically for OpenGL)
            chest_image = Image.open("assets/chest.png")
            chest_image = chest_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            chest_image = chest_image.convert("RGBA")
            chest_image_data = chest_image.tobytes()
            self.chest_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.chest_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, chest_image.width, chest_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, chest_image_data)
            print(f"Chest texture loaded: {chest_image.width}x{chest_image.height}")
            
            # Load interact texture
            interact_image = Image.open("assets/interact.png")
            interact_image = interact_image.convert("RGBA")
            interact_image_data = interact_image.tobytes()
            self.interact_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.interact_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, interact_image.width, interact_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, interact_image_data)
            print(f"Interact texture loaded: {interact_image.width}x{interact_image.height}")
            
            # Load weapon texture for hotbar icon
            weapon_image = Image.open("assets/wep_rusty.png")
            weapon_image = weapon_image.convert("RGBA")
            weapon_image_data = weapon_image.tobytes()
            self.weapon_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.weapon_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, weapon_image.width, weapon_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, weapon_image_data)
            print(f"Weapon texture loaded: {weapon_image.width}x{weapon_image.height}")

            # Load held weapon texture for first-person view
            held_weapon_image = Image.open("assets/held_rusty.png")
            held_weapon_image = held_weapon_image.convert("RGBA")
            held_weapon_image_data = held_weapon_image.tobytes()
            self.held_weapon_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.held_weapon_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, held_weapon_image.width, held_weapon_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, held_weapon_image_data)
            print(f"Held weapon texture loaded: {held_weapon_image.width}x{held_weapon_image.height}")
            
            # Load health bar texture
            health_bar_image = Image.open("assets/meter.png")
            health_bar_image = health_bar_image.convert("RGBA")
            health_bar_image_data = health_bar_image.tobytes()
            self.health_bar_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.health_bar_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, health_bar_image.width, health_bar_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, health_bar_image_data)
            print(f"Health bar texture loaded: {health_bar_image.width}x{health_bar_image.height}")
            
            # Load health fill texture
            health_fill_image = Image.open("assets/health.png")
            health_fill_image = health_fill_image.convert("RGBA")
            health_fill_image_data = health_fill_image.tobytes()
            self.health_fill_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.health_fill_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, health_fill_image.width, health_fill_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, health_fill_image_data)
            print(f"Health fill texture loaded: {health_fill_image.width}x{health_fill_image.height}")
            
            # Load mana bar texture
            mana_bar_image = Image.open("assets/meter.png")
            mana_bar_image = mana_bar_image.convert("RGBA")
            mana_bar_image_data = mana_bar_image.tobytes()
            self.mana_bar_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.mana_bar_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, mana_bar_image.width, mana_bar_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, mana_bar_image_data)
            print(f"Mana bar texture loaded: {mana_bar_image.width}x{mana_bar_image.height}")
            
            # Load mana fill texture
            mana_fill_image = Image.open("assets/magic.png")
            mana_fill_image = mana_fill_image.convert("RGBA")
            mana_fill_image_data = mana_fill_image.tobytes()
            self.mana_fill_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.mana_fill_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, mana_fill_image.width, mana_fill_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, mana_fill_image_data)
            print(f"Mana fill texture loaded: {mana_fill_image.width}x{mana_fill_image.height}")
            
            # Load skeleton texture
            skeleton_image = Image.open("assets/skeleton.png")
            skeleton_image = skeleton_image.convert("RGBA")
            skeleton_image_data = skeleton_image.tobytes()
            self.skeleton_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.skeleton_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, skeleton_image.width, skeleton_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, skeleton_image_data)
            print(f"Skeleton texture loaded: {skeleton_image.width}x{skeleton_image.height}")

            # Load ghoul texture
            ghoul_image = Image.open("assets/ghoul.png")
            ghoul_image = ghoul_image.convert("RGBA")
            ghoul_image_data = ghoul_image.tobytes()
            self.ghoul_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.ghoul_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ghoul_image.width, ghoul_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, ghoul_image_data)
            print(f"Ghoul texture loaded: {ghoul_image.width}x{ghoul_image.height}")

            # Load ghost texture
            ghost_image = Image.open("assets/ghost.png")
            ghost_image = ghost_image.convert("RGBA")
            ghost_image_data = ghost_image.tobytes()
            self.ghost_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.ghost_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ghost_image.width, ghost_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, ghost_image_data)
            print(f"Ghost texture loaded: {ghost_image.width}x{ghost_image.height}")
            
            # Load skeleton sword icon
            skeleton_sword_image = Image.open("assets/wep_skeleton.png")
            skeleton_sword_image = skeleton_sword_image.convert("RGBA")
            skeleton_sword_image_data = skeleton_sword_image.tobytes()
            self.skeleton_sword_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.skeleton_sword_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, skeleton_sword_image.width, skeleton_sword_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, skeleton_sword_image_data)
            print(f"Skeleton sword icon loaded: {skeleton_sword_image.width}x{skeleton_sword_image.height}")
            
            # Load held skeleton sword
            held_skeleton_sword_image = Image.open("assets/held_skeleton.png")
            held_skeleton_sword_image = held_skeleton_sword_image.convert("RGBA")
            held_skeleton_sword_image_data = held_skeleton_sword_image.tobytes()
            self.held_skeleton_sword_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.held_skeleton_sword_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, held_skeleton_sword_image.width, held_skeleton_sword_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, held_skeleton_sword_image_data)
            print(f"Held skeleton sword loaded: {held_skeleton_sword_image.width}x{held_skeleton_sword_image.height}")
            
            # Load health potion texture
            potion_health_image = Image.open("assets/potion_health.png")
            potion_health_image = potion_health_image.convert("RGBA")
            potion_health_image_data = potion_health_image.tobytes()
            self.potion_health_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.potion_health_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, potion_health_image.width, potion_health_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, potion_health_image_data)
            print(f"Health potion texture loaded: {potion_health_image.width}x{potion_health_image.height}")
            
            # Load magic potion texture
            potion_magic_image = Image.open("assets/potion_magic.png")
            potion_magic_image = potion_magic_image.convert("RGBA")
            potion_magic_image_data = potion_magic_image.tobytes()
            self.potion_magic_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.potion_magic_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, potion_magic_image.width, potion_magic_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, potion_magic_image_data)
            print(f"Magic potion texture loaded: {potion_magic_image.width}x{potion_magic_image.height}")
            
            # Load fire scroll texture
            scroll_fire_image = Image.open("assets/scroll_fire.png")
            scroll_fire_image = scroll_fire_image.convert("RGBA")
            scroll_fire_image_data = scroll_fire_image.tobytes()
            self.scroll_fire_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.scroll_fire_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, scroll_fire_image.width, scroll_fire_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, scroll_fire_image_data)
            print(f"Fire scroll texture loaded: {scroll_fire_image.width}x{scroll_fire_image.height}")
            
            # Load magic scroll texture
            scroll_magic_image = Image.open("assets/scroll_magic.png")
            scroll_magic_image = scroll_magic_image.convert("RGBA")
            scroll_magic_image_data = scroll_magic_image.tobytes()
            self.scroll_magic_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.scroll_magic_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, scroll_magic_image.width, scroll_magic_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, scroll_magic_image_data)
            print(f"Magic scroll texture loaded: {scroll_magic_image.width}x{scroll_magic_image.height}")
            
            # Load spell fire texture (for held spell)
            spell_fire_image = Image.open("assets/spell_fire.png")
            spell_fire_image = spell_fire_image.convert("RGBA")
            spell_fire_image_data = spell_fire_image.tobytes()
            self.spell_fire_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.spell_fire_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, spell_fire_image.width, spell_fire_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, spell_fire_image_data)
            print(f"Spell fire texture loaded: {spell_fire_image.width}x{spell_fire_image.height}")
            
            # Unbind texture to avoid state issues
            glBindTexture(GL_TEXTURE_2D, 0)
            print("All textures loaded successfully")
            print("Starter weapon 'rusty_sword' added to inventory slot 0")

            # Load fireball texture (for fire spell projectile)
            fireball_image = Image.open("assets/fireball.png")
            fireball_image = fireball_image.convert("RGBA")
            fireball_image_data = fireball_image.tobytes()
            self.fireball_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.fireball_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, fireball_image.width, fireball_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, fireball_image_data)
            print(f"Fireball texture loaded: {fireball_image.width}x{fireball_image.height}")

            # Load magicball texture (for magic spell projectile)
            magicball_image = Image.open("assets/magicball.png")
            magicball_image = magicball_image.convert("RGBA")
            magicball_image_data = magicball_image.tobytes()
            self.magicball_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.magicball_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, magicball_image.width, magicball_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, magicball_image_data)
            print(f"Magicball texture loaded: {magicball_image.width}x{magicball_image.height}")

            # Load key texture (flip vertically for OpenGL)
            key_image = Image.open("assets/key.png")
            key_image = key_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            key_image = key_image.convert("RGBA")
            key_image_data = key_image.tobytes()
            self.key_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.key_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, key_image.width, key_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, key_image_data)
            print(f"Key texture loaded: {key_image.width}x{key_image.height}")
        except (OSError, IOError) as e:
            print(f"Error loading texture: {e}")
            self.texture_id = None
            self.floor_texture_id = None
            self.ceiling_texture_id = None
            self.torch_texture_id = None
            self.chest_texture_id = None
            self.interact_texture_id = None
            self.weapon_texture_id = None
            self.health_bar_texture_id = None
            self.health_fill_texture_id = None
            self.mana_bar_texture_id = None
            self.mana_fill_texture_id = None
            self.potion_health_texture_id = None
            self.potion_magic_texture_id = None
            self.scroll_fire_texture_id = None
            self.spell_fire_texture_id = None
            self.fireball_texture_id = None
            self.key_texture_id = None
    
    def render_wall(self, x, z, height=2.0, _camera_pos=None):
        """Render a wall segment with proper lighting"""
        # Set material properties for walls
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.9, 0.9, 0.9, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.2, 0.2, 0.2, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 10.0)
        
        if self.texture_id:
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
        
        # Render each face separately to ensure proper normals and lighting
        
        # Front face (facing positive Z)
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1)
        glTexCoord2f(0, 0); glVertex3f(x, 0, z)
        glTexCoord2f(1, 0); glVertex3f(x + 1, 0, z)
        glTexCoord2f(1, 1); glVertex3f(x + 1, height, z)
        glTexCoord2f(0, 1); glVertex3f(x, height, z)
        glEnd()
        
        # Back face (facing negative Z)
        glBegin(GL_QUADS)
        glNormal3f(0, 0, -1)
        glTexCoord2f(0, 0); glVertex3f(x, 0, z + 1)
        glTexCoord2f(1, 0); glVertex3f(x + 1, 0, z + 1)
        glTexCoord2f(1, 1); glVertex3f(x + 1, height, z + 1)
        glTexCoord2f(0, 1); glVertex3f(x, height, z + 1)
        glEnd()
        
        # Left face (facing negative X)
        glBegin(GL_QUADS)
        glNormal3f(-1, 0, 0)
        glTexCoord2f(0, 0); glVertex3f(x, 0, z)
        glTexCoord2f(1, 0); glVertex3f(x, 0, z + 1)
        glTexCoord2f(1, 1); glVertex3f(x, height, z + 1)
        glTexCoord2f(0, 1); glVertex3f(x, height, z)
        glEnd()
        
        # Right face (facing positive X)
        glBegin(GL_QUADS)
        glNormal3f(1, 0, 0)
        glTexCoord2f(0, 0); glVertex3f(x + 1, 0, z)
        glTexCoord2f(1, 0); glVertex3f(x + 1, 0, z + 1)
        glTexCoord2f(1, 1); glVertex3f(x + 1, height, z + 1)
        glTexCoord2f(0, 1); glVertex3f(x + 1, height, z)
        glEnd()
        
        if self.texture_id:
            glBindTexture(GL_TEXTURE_2D, 0)
    
    def render_floor(self, x, z, _camera_pos=None):
        """Render a floor segment"""
        # Set material properties for floors
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.9, 0.9, 0.9, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 5.0)
        
        if self.floor_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.floor_texture_id)
        
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glTexCoord2f(0, 0); glVertex3f(x, 0, z)
        glTexCoord2f(1, 0); glVertex3f(x + 1, 0, z)
        glTexCoord2f(1, 1); glVertex3f(x + 1, 0, z + 1)
        glTexCoord2f(0, 1); glVertex3f(x, 0, z + 1)
        glEnd()
        
        if self.floor_texture_id:
            glBindTexture(GL_TEXTURE_2D, 0)
    
    def render_ceiling(self, x, z, height=2.0, _camera_pos=None):
        """Render a ceiling segment"""
        # Set material properties for ceilings
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 5.0)
        
        if self.ceiling_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.ceiling_texture_id)
        glBegin(GL_QUADS)
        glNormal3f(0, -1, 0)  # Normal pointing down
        glTexCoord2f(0, 0); glVertex3f(x, height, z)
        glTexCoord2f(1, 0); glVertex3f(x + 1, height, z)
        glTexCoord2f(1, 1); glVertex3f(x + 1, height, z + 1)
        glTexCoord2f(0, 1); glVertex3f(x, height, z + 1)
        glEnd()
        if self.ceiling_texture_id:
            glBindTexture(GL_TEXTURE_2D, 0)
    
    def render_torch(self, _x, _z, dx, dz, face_x, face_z, height=1.5, camera_pos=None):
        """Render a torch on the correct face of the wall with blending enabled and billboarding"""
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        if self.torch_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.torch_texture_id)
        
        # Set material properties for torch
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.6, 0.3, 0.1, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [1.0, 0.5, 0.2, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.2, 0.1, 0.05, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 10.0)
        
        torch_size = 0.5
        
        # Calculate angle to player for billboarding
        if camera_pos:
            # Calculate direction from torch to player
            to_player_x = camera_pos[0] - face_x
            to_player_z = camera_pos[2] - face_z
            
            # Calculate angle to face player
            angle = math.atan2(to_player_x, to_player_z)
            
            # Apply rotation to face player
            glPushMatrix()
            glTranslatef(face_x, height, face_z)
            glRotatef(angle * 180 / math.pi, 0, 1, 0)
            
            # Render billboarded torch quad
            glBegin(GL_QUADS)
            glNormal3f(0, 0, 1)  # Always face forward
            glTexCoord2f(0, 0); glVertex3f(-torch_size/2, -torch_size/2, 0)
            glTexCoord2f(1, 0); glVertex3f(torch_size/2, -torch_size/2, 0)
            glTexCoord2f(1, 1); glVertex3f(torch_size/2, torch_size/2, 0)
            glTexCoord2f(0, 1); glVertex3f(-torch_size/2, torch_size/2, 0)
            glEnd()
            
            glPopMatrix()
        else:
            # Fallback to wall-mounted torch if no camera position
            glBegin(GL_QUADS)
            if dx == 1:  # Torch on left face (walkable is to the right)
                glNormal3f(1, 0, 0)
                glTexCoord2f(0, 0); glVertex3f(face_x, height - torch_size/2, face_z - torch_size/2)
                glTexCoord2f(1, 0); glVertex3f(face_x, height - torch_size/2, face_z + torch_size/2)
                glTexCoord2f(1, 1); glVertex3f(face_x, height + torch_size/2, face_z + torch_size/2)
                glTexCoord2f(0, 1); glVertex3f(face_x, height + torch_size/2, face_z - torch_size/2)
            elif dx == -1:  # Torch on right face (walkable is to the left)
                glNormal3f(-1, 0, 0)
                glTexCoord2f(0, 0); glVertex3f(face_x, height - torch_size/2, face_z - torch_size/2)
                glTexCoord2f(1, 0); glVertex3f(face_x, height - torch_size/2, face_z + torch_size/2)
                glTexCoord2f(1, 1); glVertex3f(face_x, height + torch_size/2, face_z + torch_size/2)
                glTexCoord2f(0, 1); glVertex3f(face_x, height + torch_size/2, face_z - torch_size/2)
            elif dz == 1:  # Torch on front face (walkable is in front)
                glNormal3f(0, 0, 1)
                glTexCoord2f(0, 0); glVertex3f(face_x - torch_size/2, height - torch_size/2, face_z)
                glTexCoord2f(1, 0); glVertex3f(face_x + torch_size/2, height - torch_size/2, face_z)
                glTexCoord2f(1, 1); glVertex3f(face_x + torch_size/2, height + torch_size/2, face_z)
                glTexCoord2f(0, 1); glVertex3f(face_x - torch_size/2, height + torch_size/2, face_z)
            elif dz == -1:  # Torch on back face (walkable is behind)
                glNormal3f(0, 0, -1)
                glTexCoord2f(0, 0); glVertex3f(face_x - torch_size/2, height - torch_size/2, face_z)
                glTexCoord2f(1, 0); glVertex3f(face_x + torch_size/2, height - torch_size/2, face_z)
                glTexCoord2f(1, 1); glVertex3f(face_x + torch_size/2, height + torch_size/2, face_z)
                glTexCoord2f(0, 1); glVertex3f(face_x - torch_size/2, height + torch_size/2, face_z)
            glEnd()
        
        if self.torch_texture_id:
            glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_BLEND)
    
    def render_chest(self, _x, _z, center_x, center_z, height=0.1, camera_pos=None):
        """Render a chest with billboarding (always facing the player)"""
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        if self.chest_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.chest_texture_id)
        
        # Set material properties for chest
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.4, 0.3, 0.2, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.8, 0.6, 0.4, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.05, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 5.0)
        
        chest_size = 0.4
        
        # Calculate angle to player for billboarding
        if camera_pos:
            # Calculate direction from chest to player
            to_player_x = camera_pos[0] - center_x
            to_player_z = camera_pos[2] - center_z
            
            # Calculate angle to face player
            angle = math.atan2(to_player_x, to_player_z)
            
            # Apply rotation to face player
            glPushMatrix()
            glTranslatef(center_x, height, center_z)
            glRotatef(angle * 180 / math.pi, 0, 1, 0)
            
            # Render billboarded chest quad
            glBegin(GL_QUADS)
            glNormal3f(0, 0, 1)  # Always face forward
            glTexCoord2f(0, 0); glVertex3f(-chest_size/2, 0, 0)
            glTexCoord2f(1, 0); glVertex3f(chest_size/2, 0, 0)
            glTexCoord2f(1, 1); glVertex3f(chest_size/2, chest_size, 0)
            glTexCoord2f(0, 1); glVertex3f(-chest_size/2, chest_size, 0)
            glEnd()
            
            glPopMatrix()
        else:
            # Fallback to simple quad if no camera position
            glBegin(GL_QUADS)
            glNormal3f(0, 0, 1)
            glTexCoord2f(0, 0); glVertex3f(center_x - chest_size/2, height, center_z)
            glTexCoord2f(1, 0); glVertex3f(center_x + chest_size/2, height, center_z)
            glTexCoord2f(1, 1); glVertex3f(center_x + chest_size/2, height + chest_size, center_z)
            glTexCoord2f(0, 1); glVertex3f(center_x - chest_size/2, height + chest_size, center_z)
            glEnd()
        
        if self.chest_texture_id:
            glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_BLEND)
    
    def render_interact_prompt(self, screen_width, screen_height):
        """Render the interact prompt centered at the bottom of the screen"""
        if not self.interact_texture_id:
            return
        
        # Save current OpenGL state
        glPushMatrix()
        glLoadIdentity()
        
        # Disable depth testing for 2D overlay
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        
        # Set up orthographic projection for 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, screen_width, 0, screen_height)
        glMatrixMode(GL_MODELVIEW)
        
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Bind interact texture
        glBindTexture(GL_TEXTURE_2D, self.interact_texture_id)
        
        # Calculate interact prompt position and size
        prompt_width = 52  # Doubled from 26 to maintain aspect ratio
        prompt_height = 64  # Doubled from 32 to maintain aspect ratio
        prompt_x = (screen_width - prompt_width) // 2  # Center horizontally
        prompt_y = 100  # 100 pixels from bottom
        
        # Render interact prompt quad
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(prompt_x, prompt_y)
        glTexCoord2f(1, 0); glVertex2f(prompt_x + prompt_width, prompt_y)
        glTexCoord2f(1, 1); glVertex2f(prompt_x + prompt_width, prompt_y + prompt_height)
        glTexCoord2f(0, 1); glVertex2f(prompt_x, prompt_y + prompt_height)
        glEnd()
        
        # Unbind texture
        glBindTexture(GL_TEXTURE_2D, 0)
        
        # Restore OpenGL state
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        
        # Restore projection matrix
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
    
    def render_walls_batch(self, wall_positions, camera_pos=None):
        """Render multiple walls in a single batch to reduce draw calls"""
        if not wall_positions:
            return
        
        # Set material properties for walls once
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.9, 0.9, 0.9, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.2, 0.2, 0.2, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 10.0)
        
        if self.texture_id:
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
        
        # Render all walls in one batch
        for wall_x, wall_z in wall_positions:
            # Front face (facing positive Z)
            glBegin(GL_QUADS)
            glNormal3f(0, 0, 1)
            glTexCoord2f(0, 0); glVertex3f(wall_x, 0, wall_z)
            glTexCoord2f(1, 0); glVertex3f(wall_x + 1, 0, wall_z)
            glTexCoord2f(1, 1); glVertex3f(wall_x + 1, 2.0, wall_z)
            glTexCoord2f(0, 1); glVertex3f(wall_x, 2.0, wall_z)
            glEnd()
            
            # Back face (facing negative Z)
            glBegin(GL_QUADS)
            glNormal3f(0, 0, -1)
            glTexCoord2f(0, 0); glVertex3f(wall_x, 0, wall_z + 1)
            glTexCoord2f(1, 0); glVertex3f(wall_x + 1, 0, wall_z + 1)
            glTexCoord2f(1, 1); glVertex3f(wall_x + 1, 2.0, wall_z + 1)
            glTexCoord2f(0, 1); glVertex3f(wall_x, 2.0, wall_z + 1)
            glEnd()
            
            # Left face (facing negative X)
            glBegin(GL_QUADS)
            glNormal3f(-1, 0, 0)
            glTexCoord2f(0, 0); glVertex3f(wall_x, 0, wall_z)
            glTexCoord2f(1, 0); glVertex3f(wall_x, 0, wall_z + 1)
            glTexCoord2f(1, 1); glVertex3f(wall_x, 2.0, wall_z + 1)
            glTexCoord2f(0, 1); glVertex3f(wall_x, 2.0, wall_z)
            glEnd()
            
            # Right face (facing positive X)
            glBegin(GL_QUADS)
            glNormal3f(1, 0, 0)
            glTexCoord2f(0, 0); glVertex3f(wall_x + 1, 0, wall_z)
            glTexCoord2f(1, 0); glVertex3f(wall_x + 1, 0, wall_z + 1)
            glTexCoord2f(1, 1); glVertex3f(wall_x + 1, 2.0, wall_z + 1)
            glTexCoord2f(0, 1); glVertex3f(wall_x + 1, 2.0, wall_z)
            glEnd()
        
        if self.texture_id:
            glBindTexture(GL_TEXTURE_2D, 0)
    
    def render_floors_batch(self, floor_positions, camera_pos=None):
        """Render multiple floors in a single batch"""
        if not floor_positions:
            return
        
        # Set material properties for floors once
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.9, 0.9, 0.9, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 5.0)
        
        if self.floor_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.floor_texture_id)
        
        # Render all floors in one batch
        for floor_x, floor_z in floor_positions:
            glBegin(GL_QUADS)
            glNormal3f(0, 1, 0)
            glTexCoord2f(0, 0); glVertex3f(floor_x, 0, floor_z)
            glTexCoord2f(1, 0); glVertex3f(floor_x + 1, 0, floor_z)
            glTexCoord2f(1, 1); glVertex3f(floor_x + 1, 0, floor_z + 1)
            glTexCoord2f(0, 1); glVertex3f(floor_x, 0, floor_z + 1)
            glEnd()
        
        if self.floor_texture_id:
            glBindTexture(GL_TEXTURE_2D, 0)
    
    def create_spatial_grid(self, dungeon_grid, torch_positions, chest_positions, chunk_size=8):
        """Create a spatial grid to organize objects into chunks for efficient rendering"""
        self.chunk_size = chunk_size
        self.grid_width = len(dungeon_grid[0])
        self.grid_height = len(dungeon_grid)
        self.chunks_x = (self.grid_width + chunk_size - 1) // chunk_size
        self.chunks_z = (self.grid_height + chunk_size - 1) // chunk_size
        
        # Initialize chunk storage
        self.wall_chunks = [[[] for _ in range(self.chunks_x)] for _ in range(self.chunks_z)]
        self.torch_chunks = [[[] for _ in range(self.chunks_x)] for _ in range(self.chunks_z)]
        self.chest_chunks = [[[] for _ in range(self.chunks_x)] for _ in range(self.chunks_z)]
        
        # Organize walls into chunks
        for z in range(self.grid_height):
            for x in range(self.grid_width):
                if dungeon_grid[z][x] == 1:  # Wall
                    chunk_x = x // chunk_size
                    chunk_z = z // chunk_size
                    if 0 <= chunk_x < self.chunks_x and 0 <= chunk_z < self.chunks_z:
                        self.wall_chunks[chunk_z][chunk_x].append((x, z))
        
        # Organize torches into chunks
        if torch_positions:
            for torch_x, torch_z, dx, dz, face_x, face_z in torch_positions:
                chunk_x = int(face_x) // chunk_size
                chunk_z = int(face_z) // chunk_size
                if 0 <= chunk_x < self.chunks_x and 0 <= chunk_z < self.chunks_z:
                    self.torch_chunks[chunk_z][chunk_x].append((torch_x, torch_z, dx, dz, face_x, face_z))
        
        # Organize chests into chunks
        if chest_positions:
            for chest_x, chest_z, center_x, center_z in chest_positions:
                chunk_x = int(center_x) // chunk_size
                chunk_z = int(center_z) // chunk_size
                if 0 <= chunk_x < self.chunks_x and 0 <= chunk_z < self.chunks_z:
                    self.chest_chunks[chunk_z][chunk_x].append((chest_x, chest_z, center_x, center_z))
    
    def get_nearby_chunks(self, camera_pos, chunk_size=8):
        """Get the current chunk and adjacent chunks for the player's position"""
        if not camera_pos:
            return []
        
        chunk_x = int(camera_pos[0]) // chunk_size
        chunk_z = int(camera_pos[2]) // chunk_size
        
        nearby_chunks = []
        for dz in range(-1, 2):  # -1, 0, 1
            for dx in range(-1, 2):  # -1, 0, 1
                new_chunk_x = chunk_x + dx
                new_chunk_z = chunk_z + dz
                if (0 <= new_chunk_x < self.chunks_x and 
                    0 <= new_chunk_z < self.chunks_z):
                    nearby_chunks.append((new_chunk_x, new_chunk_z))
        
        return nearby_chunks

    def is_in_frustum(self, object_x, object_z, camera_pos, camera_rot, fov_angle=120.0, max_distance=10.0):
        """Check if an object is within the camera's view frustum"""
        if not camera_pos:
            return True
        
        # Calculate distance to object
        dx = object_x - camera_pos[0]
        dz = object_z - camera_pos[2]
        distance = math.sqrt(dx*dx + dz*dz)
        
        # Check if object is too far away
        if distance > max_distance:
            return False
        
        # Calculate angle to object relative to camera forward direction
        # Camera forward is -sin(yaw), -cos(yaw) based on your camera setup
        camera_forward_x = -math.sin(camera_rot[1])
        camera_forward_z = -math.cos(camera_rot[1])
        
        # Normalize the direction to object
        if distance > 0:
            object_dir_x = dx / distance
            object_dir_z = dz / distance
        else:
            return True  # Object is at camera position
        
        # Calculate dot product between camera forward and object direction
        dot_product = camera_forward_x * object_dir_x + camera_forward_z * object_dir_z
        
        # Convert FOV to radians and calculate the cosine of half the FOV
        fov_rad = math.radians(fov_angle)
        cos_half_fov = math.cos(fov_rad / 2)
        
        # Add a large buffer to prevent popping (make the frustum much wider)
        cos_half_fov -= 0.3  # This makes the frustum about 30% wider
        
        # Object is in frustum if dot product is greater than cosine of half FOV
        return dot_product > cos_half_fov

    def render_dungeon(self, dungeon_grid, camera_pos=None, torch_positions=None, chest_positions=None, camera_rot=None):
        """Render the entire dungeon using spatial partitioning and batch rendering"""
        # Set texture environment to MODULATE for world rendering
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        # Create spatial grid if not already created
        if not hasattr(self, 'wall_chunks'):
            self.create_spatial_grid(dungeon_grid, torch_positions, chest_positions)
        
        # Get nearby chunks to render
        nearby_chunks = self.get_nearby_chunks(camera_pos)
        
        # Collect visible walls for batch rendering
        visible_walls = []
        visible_floors = []
        
        if camera_pos and camera_rot and nearby_chunks:
            wall_render_distance = 6.0  # Only render walls within 6 units
            for chunk_x, chunk_z in nearby_chunks:
                for wall_x, wall_z in self.wall_chunks[chunk_z][chunk_x]:
                    # Calculate distance from wall center to player
                    wall_center_x = wall_x + 0.5
                    wall_center_z = wall_z + 0.5
                    distance = math.sqrt((wall_center_x - camera_pos[0])**2 + (wall_center_z - camera_pos[2])**2)
                    if distance <= wall_render_distance and self.is_in_frustum(wall_center_x, wall_center_z, camera_pos, camera_rot):
                        visible_walls.append((wall_x, wall_z))
        
        # Collect visible floors for batch rendering (with distance check)
        if camera_pos:
            floor_render_distance = 6.0  # Only render floors within 6 units
            for z in range(len(dungeon_grid)):
                for x in range(len(dungeon_grid[0])):
                    if dungeon_grid[z][x] == 0:  # Floor
                        # Calculate distance from floor center to player
                        floor_center_x = x + 0.5
                        floor_center_z = z + 0.5
                        distance = math.sqrt((floor_center_x - camera_pos[0])**2 + (floor_center_z - camera_pos[2])**2)
                        if distance <= floor_render_distance:
                            visible_floors.append((x, z))
        else:
            # Fallback: render all floors if no camera position
            for z in range(len(dungeon_grid)):
                for x in range(len(dungeon_grid[0])):
                    if dungeon_grid[z][x] == 0:  # Floor
                        visible_floors.append((x, z))
        
        # Render walls in batch
        self.render_walls_batch(visible_walls, camera_pos)
        
        # Render floors in batch
        self.render_floors_batch(visible_floors, camera_pos)
        
        # Render all ceilings (always visible)
        for z in range(len(dungeon_grid)):
            for x in range(len(dungeon_grid[0])):
                self.render_ceiling(x, z, _camera_pos=camera_pos)
        
        # Render torches only from nearby chunks
        if camera_pos and camera_rot and nearby_chunks:
            render_distance = 5.0  # Only render torches within 5 units
            for chunk_x, chunk_z in nearby_chunks:
                for torch_data in self.torch_chunks[chunk_z][chunk_x]:
                    torch_x, torch_z, dx, dz, face_x, face_z = torch_data
                    distance = math.sqrt((face_x - camera_pos[0])**2 + (face_z - camera_pos[2])**2)
                    if distance <= render_distance and self.is_in_frustum(face_x, face_z, camera_pos, camera_rot):
                        self.render_torch(torch_x, torch_z, dx, dz, face_x, face_z, camera_pos=camera_pos)
        
        # Render chests only from nearby chunks
        if camera_pos and camera_rot and nearby_chunks:
            render_distance = 5.0  # Only render chests within 5 units
            for chunk_x, chunk_z in nearby_chunks:
                for chest_data in self.chest_chunks[chunk_z][chunk_x]:
                    chest_x, chest_z, center_x, center_z = chest_data
                    distance = math.sqrt((center_x - camera_pos[0])**2 + (center_z - camera_pos[2])**2)
                    if distance <= render_distance and self.is_in_frustum(center_x, center_z, camera_pos, camera_rot):
                        self.render_chest(chest_x, chest_z, center_x, center_z, camera_pos=camera_pos)

    def render_npc(self, npc, camera_pos=None):
        if not npc.is_alive:
            return
        glEnable(GL_BLEND)
        if npc.flash_timer > 0:
            glBlendFunc(GL_ONE, GL_ONE)
        else:
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # Choose texture based on type
        if npc.npc_type == "ghoul" and self.ghoul_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.ghoul_texture_id)
        elif npc.npc_type == "ghost" and self.ghost_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.ghost_texture_id)
        elif npc.npc_type == "skeleton" and self.skeleton_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.skeleton_texture_id)
        else:
            glBindTexture(GL_TEXTURE_2D, 0)
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        if npc.flash_timer > 0:
            glColor4f(2.0, 0.1, 0.1, 1.0)
        else:
            glColor4f(1.0, 1.0, 1.0, 1.0)
        glDisable(GL_LIGHTING)
        width = 0.7
        # Use different aspect ratios if needed
        if npc.npc_type == "ghoul":
            height = width * (984/718)
        elif npc.npc_type == "ghost":
            height = width * (984/718)
        else:
            height = width * (984/718)
        if camera_pos:
            to_player_x = camera_pos[0] - npc.center_x
            to_player_z = camera_pos[2] - npc.center_z
            angle = math.atan2(to_player_x, to_player_z)
            glPushMatrix()
            glTranslatef(npc.center_x, 0.1, npc.center_z)
            glRotatef(angle * 180 / math.pi, 0, 1, 0)
            glBegin(GL_QUADS)
            glNormal3f(0, 0, 1)
            glTexCoord2f(0, 1); glVertex3f(-width/2, 0, 0)
            glTexCoord2f(1, 1); glVertex3f(width/2, 0, 0)
            glTexCoord2f(1, 0); glVertex3f(width/2, height, 0)
            glTexCoord2f(0, 0); glVertex3f(-width/2, height, 0)
            glEnd()
            glPopMatrix()
        else:
            glBegin(GL_QUADS)
            glNormal3f(0, 0, 1)
            glTexCoord2f(0, 1); glVertex3f(npc.center_x - width/2, 0, npc.center_z)
            glTexCoord2f(1, 1); glVertex3f(npc.center_x + width/2, 0, npc.center_z)
            glTexCoord2f(1, 0); glVertex3f(npc.center_x + width/2, height, npc.center_z)
            glTexCoord2f(0, 0); glVertex3f(npc.center_x - width/2, height, npc.center_z)
            glEnd()
        glEnable(GL_LIGHTING)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_BLEND)

    def render_npcs(self, npcs, camera_pos=None, camera_rot=None):
        if not npcs or camera_pos is None:
            return
        max_distance = 10.0
        for npc in npcs:
            dist = math.sqrt((npc.center_x - camera_pos[0])**2 + (npc.center_z - camera_pos[2])**2)
            if dist > max_distance:
                continue
            if camera_rot is not None and not self.is_in_frustum(npc.center_x, npc.center_z, camera_pos, camera_rot, max_distance=max_distance):
                continue
            self.render_npc(npc, camera_pos=camera_pos)

    def render_dropped_item(self, item, camera_pos=None):
        # Only render if not collected
        if item.collected:
            return
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # Choose texture based on item type
        if item.item_type == 'skeleton_sword' and self.skeleton_sword_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.skeleton_sword_texture_id)
            item_size = 0.32  # Smaller dropped skeleton sword
            item_height = item_size  # 1:1 aspect ratio (125x125)
        elif item.item_type == 'rusty_sword' and self.weapon_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.weapon_texture_id)  # wep_rusty.png (hotbar icon)
            item_size = 0.32  # Smaller dropped rusty sword
            item_height = item_size  # 1:1 aspect ratio (125x125)
        elif item.item_type == 'health_potion' and self.potion_health_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.potion_health_texture_id)
            item_size = 0.25
            item_height = item_size * (160/110)  # Potion aspect ratio (110x160)
        elif item.item_type == 'magic_potion' and self.potion_magic_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.potion_magic_texture_id)
            item_size = 0.25
            item_height = item_size * (160/110)  # Potion aspect ratio (110x160)
        elif item.item_type == 'fire_scroll' and self.scroll_fire_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.scroll_fire_texture_id)
            item_size = 0.4
            item_height = item_size * (125/111)  # Scroll aspect ratio (111x125)
        elif item.item_type == 'magic_scroll' and hasattr(self, 'scroll_magic_texture_id') and self.scroll_magic_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.scroll_magic_texture_id)
            item_size = 0.4
            item_height = item_size * (125/111)  # Same aspect ratio as fire scroll
        elif item.item_type == 'key' and hasattr(self, 'key_texture_id') and self.key_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.key_texture_id)
            item_size = 0.18  # Small-ish
            item_height = item_size * (670/344)  # Key aspect ratio
        elif item.item_type == 'key':
            return
        else:
            return
        # Billboarded sprite
        y = 0.15
        angle = 0
        if camera_pos:
            to_player_x = camera_pos[0] - item.x
            to_player_z = camera_pos[2] - item.z
            angle = math.atan2(to_player_x, to_player_z)
        glPushMatrix()
        glTranslatef(item.x, y, item.z)
        glRotatef(angle * 180 / math.pi, 0, 1, 0)
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1)
        glTexCoord2f(0, 1); glVertex3f(-item_size/2, 0, 0)
        glTexCoord2f(1, 1); glVertex3f(item_size/2, 0, 0)
        glTexCoord2f(1, 0); glVertex3f(item_size/2, item_height, 0)
        glTexCoord2f(0, 0); glVertex3f(-item_size/2, item_height, 0)
        glEnd()
        glPopMatrix()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_BLEND)

    def render_dropped_items(self, dropped_items, camera_pos=None):
        for item in dropped_items:
            self.render_dropped_item(item, camera_pos)

    def render_fireball(self, fireball, camera_pos=None):
        """Render a fireball as a billboarded sprite"""
        if not fireball.active:
            return
        # Choose texture and color based on fireball type
        if hasattr(fireball, 'is_magic') and fireball.is_magic:
            if not hasattr(self, 'magicball_texture_id') or not self.magicball_texture_id:
                return
            texture_id = self.magicball_texture_id
            color_ambient = [0.3, 0.3, 0.8, 1.0]
            color_diffuse = [0.5, 0.5, 1.0, 1.0]
        else:
            if not self.fireball_texture_id:
                return
            texture_id = self.fireball_texture_id
            color_ambient = [0.8, 0.4, 0.1, 1.0]
            color_diffuse = [1.0, 0.5, 0.2, 1.0]
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        # Set material properties
        glMaterialfv(GL_FRONT, GL_AMBIENT, color_ambient)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, color_diffuse)
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.2, 0.1, 0.05, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 10.0)
        # Fireball size and aspect ratio (109x125)
        fireball_size = 0.4
        fireball_height = fireball_size * (125/109)
        y = 0.5
        angle = 0
        if camera_pos:
            to_player_x = camera_pos[0] - fireball.x
            to_player_z = camera_pos[2] - fireball.z
            angle = math.atan2(to_player_x, to_player_z)
        glPushMatrix()
        glTranslatef(fireball.x, y, fireball.z)
        glRotatef(angle * 180 / math.pi, 0, 1, 0)
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1)
        glTexCoord2f(0, 1); glVertex3f(-fireball_size/2, 0, 0)
        glTexCoord2f(1, 1); glVertex3f(fireball_size/2, 0, 0)
        glTexCoord2f(1, 0); glVertex3f(fireball_size/2, fireball_height, 0)
        glTexCoord2f(0, 0); glVertex3f(-fireball_size/2, fireball_height, 0)
        glEnd()
        glPopMatrix()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_BLEND)

    def render_fireballs(self, fireballs, camera_pos=None):
        """Render all active fireballs"""
        for fireball in fireballs:
            self.render_fireball(fireball, camera_pos)

def astar(grid, start, goal):
    """A* pathfinding for a 2D grid. Returns a list of (x, z) tiles from start to goal (inclusive), or [] if no path."""
    width, height = len(grid[0]), len(grid)
    def neighbors(pos):
        x, z = pos
        for dx, dz in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, nz = x+dx, z+dz
            if 0 <= nx < width and 0 <= nz < height and grid[nz][nx] == 0:
                yield (nx, nz)
    def heuristic(a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])
    open_set = []
    heapq.heappush(open_set, (0 + heuristic(start, goal), 0, start, [start]))
    visited = set()
    while open_set:
        est_total, cost, current, path = heapq.heappop(open_set)
        if current == goal:
            return path
        if current in visited:
            continue
        visited.add(current)
        for neighbor in neighbors(current):
            if neighbor not in visited:
                heapq.heappush(open_set, (cost+1+heuristic(neighbor, goal), cost+1, neighbor, path+[neighbor]))
    return []

class NPC:
    def __init__(self, x, z, center_x, center_z, npc_type="skeleton", health=None):
        self.x = x
        self.z = z
        self.center_x = center_x
        self.center_z = center_z
        self.npc_type = npc_type  # "skeleton", "ghoul", or "ghost"
        # Set health based on type if not provided
        if health is not None:
            self.health = health
        elif npc_type == "ghoul":
            self.health = 20
        elif npc_type == "skeleton":
            self.health = 30
        elif npc_type == "ghost":
            self.health = 40
        else:
            self.health = 20
        self.flash_timer = 0  # Frames to flash red
        self.is_alive = True
        self.death_timer = 0  # Frames to show corpse (black)
        self.attack_cooldown = 0  # Frames until next attack
        self.frozen_timer = 0  # Frames to freeze movement after attack
        self.path = []  # Path of (x, z) tiles to follow
        self.path_timer = 0  # Frames until next path recalculation
        self.last_player_tile = None

    def update_path(self, grid, player_tile):
        skel_tile = (int(self.center_x), int(self.center_z))
        player_tile = (int(player_tile[0]), int(player_tile[1]))
        if self.path and self.path[0] != skel_tile:
            self.path_timer = 0
        if self.path_timer > 0 and self.last_player_tile == player_tile:
            self.path_timer -= 1
            return
        self.last_player_tile = player_tile
        self.path = astar(grid, skel_tile, player_tile)
        self.path_timer = 20

    def move_along_path(self, collision_checker, speed=0.05):
        if not self.is_alive or not self.path or len(self.path) < 2:
            return
        skel_tile = (int(self.center_x), int(self.center_z))
        next_tile = self.path[1]
        if next_tile == skel_tile:
            return
        dx = next_tile[0] + 0.5 - self.center_x
        dz = next_tile[1] + 0.5 - self.center_z
        dist = math.sqrt(dx*dx + dz*dz)
        if dist < 1e-5:
            return
        move_dist = min(speed, dist)
        move_x = dx / dist * move_dist
        move_z = dz / dist * move_dist
        new_x = self.center_x + move_x
        new_z = self.center_z + move_z
        if not collision_checker(new_x, new_z):
            self.center_x = new_x
            self.center_z = new_z

    def take_damage(self, amount, knockback_vec=None, collision_checker=None):
        if not self.is_alive:
            return
        self.health -= amount
        self.flash_timer = 10
        if self.health <= 0:
            self.is_alive = False
            self.death_timer = 0
        if knockback_vec is not None:
            new_x = self.center_x + knockback_vec[0]
            new_z = self.center_z + knockback_vec[1]
            if collision_checker is None or not collision_checker(new_x, new_z):
                self.center_x = new_x
                self.center_z = new_z

    def move_toward_player(self, player_pos, collision_checker, speed=0.05):
        if not self.is_alive:
            return
        dx = player_pos[0] - self.center_x
        dz = player_pos[2] - self.center_z
        dist = math.sqrt(dx*dx + dz*dz)
        if dist < 1e-5:
            return
        move_dist = min(speed, dist)
        move_x = dx / dist * move_dist
        move_z = dz / dist * move_dist
        new_x = self.center_x + move_x
        new_z = self.center_z + move_z
        if not collision_checker(new_x, new_z):
            self.center_x = new_x
            self.center_z = new_z

class DroppedItem:
    def __init__(self, item_type, x, z):
        self.item_type = item_type
        self.x = x
        self.z = z
        self.collected = False
        self.spawn_time = time.time()

class Fireball:
    def __init__(self, x, z, direction_x, direction_z, speed=0.3, max_distance=7.0, is_magic=False, collision_checker=None):
        self.x = x
        self.z = z
        self.direction_x = direction_x
        self.direction_z = direction_z
        self.speed = speed
        self.max_distance = max_distance
        self.distance_traveled = 0.0
        self.spawn_x = x
        self.spawn_z = z
        self.active = True
        self.is_magic = is_magic
        self.collision_checker = collision_checker
    
    def update(self):
        """Update fireball position and check if it should be destroyed"""
        if not self.active:
            return
        # Move fireball in its direction
        next_x = self.x + self.direction_x * self.speed
        next_z = self.z + self.direction_z * self.speed
        # Check for wall collision before moving
        if self.collision_checker and self.collision_checker(next_x, next_z):
            self.active = False
            return
        self.x = next_x
        self.z = next_z
        # Calculate distance traveled
        dx = self.x - self.spawn_x
        dz = self.z - self.spawn_z
        self.distance_traveled = math.sqrt(dx*dx + dz*dz)
        # Destroy if traveled too far
        if self.distance_traveled >= self.max_distance:
            self.active = False
    
    def check_collision_with_skeleton(self, skeleton):
        """Check if fireball hits a skeleton"""
        if not self.active or not skeleton.is_alive:
            return False
        
        # Calculate distance between fireball and skeleton
        dx = self.x - skeleton.center_x
        dz = self.z - skeleton.center_z
        distance = math.sqrt(dx*dx + dz*dz)
        
        # Collision radius (fireball size)
        collision_radius = 0.3
        
        if distance <= collision_radius:
            # Hit! Apply damage and destroy fireball
            if hasattr(self, 'is_magic') and self.is_magic:
                skeleton.take_damage(20)  # Magicball deals 20 damage
            else:
                skeleton.take_damage(10)  # Fireball deals 10 damage
            self.active = False
            return True
        
        return False

class DungeonCrawler:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()  # Initialize the mixer for audio
        self.width, self.height = 1200, 800
        pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("3D Dungeon Crawler")
        
        # Initialize dungeon
        self.dungeon_generator = DungeonGenerator(51, 51)
        self.dungeon_grid = self.dungeon_generator.generate_dungeon()
        # Create collision grid as exact copy
        self.collision_grid = [row[:] for row in self.dungeon_grid]
        
        # Find a valid spawn position for the player
        spawn_pos = self.find_valid_spawn_position()
        self.camera_pos = [spawn_pos[0], 1, spawn_pos[1]]
        self.camera_rot = [0, 0]  # [pitch, yaw] - pitch disabled
        self.mouse_sensitivity = 0.2
        self.move_speed = 0.1
        self.renderer = DungeonRenderer()
        
        # Load and start background music
        self.load_background_music()
        
        # Initialize hotbar
        self.hotbar_texture_id = None
        self.load_hotbar()
        
        # Chest interaction variables
        self.nearby_chest = None
        self.interaction_distance = 2.0  # Distance to trigger interaction
        
        # Hotbar navigation variables
        self.selected_slot = 0  # Current selected slot (0-6 for 7 slots)
        self.num_slots = 7  # Total number of hotbar slots
        
        # Inventory system
        self.inventory = [{"type": "empty", "count": 0}] * self.num_slots  # Initialize with dict items
        self.inventory[0] = {"type": "rusty_sword", "count": 1}  # Place starter item in first slot
        
        # Sword swing animation variables
        self.is_swinging = False
        self.swing_start_time = 0
        self.swing_duration = 500  # Animation duration in milliseconds
        
        # Health system
        self.max_health = 100
        self.current_health = 100
        
        # Mana system
        self.max_mana = 100
        self.current_mana = 100
        
        # Mouse control
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        
        # Setup OpenGL
        self.setup_gl()
        
        # Initialize chest proximity check
        self.check_nearby_chests()
        
        # Skeletons
        self.skeletons = self.dungeon_generator.skeletons
        self.dropped_items = []
        self.nearby_item = None  # Track item for interact prompt
        
        # Fireballs
        self.fireballs = []

        # Spawn the key at the farthest location from the player
        self.spawn_key_item()
    
    def load_background_music(self):
        """Load and start the background music"""
        try:
            pygame.mixer.music.load("assets/dungeon1.wav")
            pygame.mixer.music.set_volume(0.3)  # Set volume to 30% before playing
            pygame.mixer.music.play(-1)  # -1 means loop indefinitely
            pygame.mixer.music.set_volume(0.3)  # Set volume to 30% after playing (in case it is reset)
            # Also set the volume on the default channel to 30%
            pygame.mixer.Channel(0).set_volume(0.3)
            # Debug: If still not quiet, set to 0.05 (almost mute)
            # pygame.mixer.music.set_volume(0.05)
            print("Background music loaded and started (volume forced to 30%)")
        except Exception as e:
            print(f"Could not load background music: {e}")
            print("Make sure 'dungeon1.wav' exists in the assets folder")
    
    def load_hotbar(self):
        """Load the hotbar texture"""
        try:
            # Load hotbar texture
            image = Image.open("assets/bar.png")
            image = image.convert("RGBA")
            image_data = image.tobytes()
            self.hotbar_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.hotbar_texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image_data)
            print("Hotbar texture loaded successfully")
        except Exception as e:
            print(f"Could not load hotbar texture: {e}")
            print("Make sure 'bar.png' exists in the assets folder")
            self.hotbar_texture_id = None
    
    def setup_gl(self):
        """Setup OpenGL environment"""
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_FOG)  # Enable fog
        # glEnable(GL_CULL_FACE)  # Disable face culling for now
        # glCullFace(GL_BACK)
        
        # Set up fog for atmospheric effect
        glFogi(GL_FOG_MODE, GL_LINEAR)
        glFogf(GL_FOG_START, 1.0)  # Start fog further back
        glFogf(GL_FOG_END, 4.0)    # End fog at 4 units (better visibility)
        glFogfv(GL_FOG_COLOR, [0.02, 0.02, 0.05, 1.0])  # Darker blue tint to fog
        
        # Set up lighting - simple uniform lighting
        glLightfv(GL_LIGHT0, GL_POSITION, [0, 10, 0, 1])  # Light from above
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1])  # Moderate ambient lighting
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.4, 0.4, 0.4, 1])  # Moderate diffuse lighting
        
        # Disable all other lights for now to fix flickering
        glDisable(GL_LIGHT1)
        glDisable(GL_LIGHT2)
        glDisable(GL_LIGHT3)
        glDisable(GL_LIGHT4)
        glDisable(GL_LIGHT5)
        
        # Set up perspective
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, self.width / self.height, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)
    
    def handle_input(self):
        """Handle keyboard and mouse input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_e and self.nearby_chest is not None:
                    # Interact with nearby chest
                    self.interact_with_chest()
                elif event.key == pygame.K_e and self.nearby_item is not None:
                    # Interact with nearby dropped item
                    self.pick_up_item(self.nearby_item)
                elif event.key == pygame.K_q:
                    # Drop the selected item
                    self.drop_selected_item()
                elif event.key == pygame.K_LEFT:
                    # Navigate hotbar left
                    self.selected_slot = (self.selected_slot - 1) % self.num_slots
                elif event.key == pygame.K_RIGHT:
                    # Navigate hotbar right
                    self.selected_slot = (self.selected_slot + 1) % self.num_slots
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check if a sword is equipped and start swing animation
                    if self.inventory[self.selected_slot]["type"] in ("rusty_sword", "skeleton_sword") and not self.is_swinging:
                        self.is_swinging = True
                        self.swing_start_time = pygame.time.get_ticks()
                        self.try_attack_skeletons()
                    elif self.inventory[self.selected_slot]["type"] == "fire_scroll" and not self.is_swinging:
                        if self.current_mana >= 5:
                            self.is_swinging = True
                            self.swing_start_time = pygame.time.get_ticks()
                            self.cast_fire_spell()
                        # If not enough mana, do nothing (no animation, no spell)
                    elif self.inventory[self.selected_slot]["type"] == "health_potion":
                        self.use_health_potion()
                    elif self.inventory[self.selected_slot]["type"] == "magic_potion":
                        self.use_magic_potion()
                elif self.inventory[self.selected_slot]["type"] == "magic_scroll" and not self.is_swinging:
                    if self.current_mana >= 5:
                        self.is_swinging = True
                        self.swing_start_time = pygame.time.get_ticks()
                        self.cast_magic_spell()
                    # If not enough mana, do nothing (no animation, no spell)
            elif event.type == pygame.MOUSEMOTION:
                self.camera_rot[1] -= event.rel[0] * self.mouse_sensitivity * 0.01  # Fixed left/right
                self.camera_rot[0] -= event.rel[1] * self.mouse_sensitivity * 0.01  # Enable up/down
                # self.camera_rot[0] = max(-1.5, min(1.5, self.camera_rot[0]))  # Disabled pitch clamping
        keys = pygame.key.get_pressed()
        # Fix forward vector calculation for proper W/S movement
        forward = [-math.sin(self.camera_rot[1]), 0, -math.cos(self.camera_rot[1])]
        right = [math.cos(self.camera_rot[1]), 0, -math.sin(self.camera_rot[1])]
        move = [0, 0, 0]
        if keys[pygame.K_w]:  # W goes forward
            move[0] += forward[0] * self.move_speed
            move[2] += forward[2] * self.move_speed
        if keys[pygame.K_s]:  # S goes backward
            move[0] -= forward[0] * self.move_speed
            move[2] -= forward[2] * self.move_speed
        if keys[pygame.K_a]:  # A goes left
            move[0] -= right[0] * self.move_speed
            move[2] -= right[2] * self.move_speed
        if keys[pygame.K_d]:  # D goes right
            move[0] += right[0] * self.move_speed
            move[2] += right[2] * self.move_speed
        # Collision detection
        new_x = self.camera_pos[0] + move[0]
        new_z = self.camera_pos[2] + move[2]
        if not self.check_collision(new_x, new_z):
            self.camera_pos[0] = new_x
            self.camera_pos[2] = new_z
        # Check for nearby chests
        self.check_nearby_chests()
        # Check for nearby dropped items
        self.check_nearby_items()
        return True
    
    def interact_with_chest(self):
        """Handle chest interaction - drop items and remove the chest from the game"""
        if self.nearby_chest is not None:
            print(f"Attempting to open chest: {self.nearby_chest}")
            print(f"Current chest positions: {self.dungeon_generator.chest_positions}")
            
            # Get chest position for item drops
            chest_x, chest_z, center_x, center_z = self.nearby_chest
            
            # Drop 3-5 random items around the chest
            num_items = random.randint(3, 5)
            fire_scroll_dropped = False
            for i in range(num_items):
                # Determine item type based on rarity
                rand = random.random() * 100  # Random number 0-100
                if rand < 20:
                    if not fire_scroll_dropped:
                        item_type = 'fire_scroll'
                        fire_scroll_dropped = True
                    else:
                        # Replace with a random valid item (health or magic potion)
                        item_type = random.choice(['health_potion', 'magic_potion'])
                elif rand < 50:  # 30% chance for health potions (70% total - 20% scrolls = 30% remaining)
                    item_type = 'health_potion'
                elif rand < 80:  # 30% chance for magic potions (60% total - 30% health = 30% remaining)
                    item_type = 'magic_potion'
                else:  # 20% chance for no item (empty drop)
                    continue
                
                # Calculate random position around chest (within 1.5 units)
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0.5, 1.5)
                drop_x = center_x + math.cos(angle) * distance
                drop_z = center_z + math.sin(angle) * distance
                
                # Create dropped item
                self.dropped_items.append(DroppedItem(item_type, drop_x, drop_z))
                print(f"Dropped {item_type} at ({drop_x:.2f}, {drop_z:.2f})")
            
            # Remove the chest from the chest positions list
            if hasattr(self.dungeon_generator, 'chest_positions'):
                if self.nearby_chest in self.dungeon_generator.chest_positions:
                    self.dungeon_generator.chest_positions.remove(self.nearby_chest)
                    print(f"Chest opened and removed! Dropped {num_items} items. Remaining chests: {len(self.dungeon_generator.chest_positions)}")
                    
                    # Update the spatial grid to reflect the removed chest
                    if hasattr(self.renderer, 'chest_chunks'):
                        self.renderer.create_spatial_grid(self.dungeon_grid, self.dungeon_generator.torch_positions, self.dungeon_generator.chest_positions)
                        print("Spatial grid updated")
                else:
                    print(f"Chest not found in list!")
            
            # Clear the nearby chest reference
            self.nearby_chest = None
    
    def check_nearby_chests(self):
        """Check if player is near any chests and update nearby_chest"""
        self.nearby_chest = None
        if hasattr(self.dungeon_generator, 'chest_positions'):
            for chest_data in self.dungeon_generator.chest_positions:
                chest_x, chest_z, center_x, center_z = chest_data
                distance = math.sqrt((center_x - self.camera_pos[0])**2 + (center_z - self.camera_pos[2])**2)
                if distance <= self.interaction_distance:
                    self.nearby_chest = chest_data
                    break
    
    def check_collision(self, x, z):
        """Check if position is inside a wall"""
        # Convert world coordinates to grid coordinates
        grid_x = int(x)
        grid_z = int(z)
        
        # Check bounds
        if (grid_z < 0 or grid_z >= len(self.collision_grid) or 
            grid_x < 0 or grid_x >= len(self.collision_grid[0])):
            return True  # Out of bounds = collision
        
        # Check if position is a wall
        return self.collision_grid[grid_z][grid_x] == 1
    
    def render_hotbar(self):
        """Render the hotbar as a 2D overlay at the bottom of the screen"""
        if not self.hotbar_texture_id:
            return
        # Set texture environment to REPLACE for UI
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
        # Save current OpenGL state
        glPushMatrix()
        glLoadIdentity()
        # Disable depth testing for 2D overlay
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        # Set up orthographic projection for 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, self.width, 0, self.height)
        glMatrixMode(GL_MODELVIEW)
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # Calculate hotbar position and size
        hotbar_width = 320  # Scaled down from 1024
        hotbar_height = 59   # Scaled down from 189 (maintaining aspect ratio)
        hotbar_x = 20  # Far left position
        hotbar_y = 20  # 20 pixels from bottom
        # Bind hotbar texture
        glBindTexture(GL_TEXTURE_2D, self.hotbar_texture_id)
        # Render hotbar quad
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(hotbar_x, hotbar_y)
        glTexCoord2f(1, 0); glVertex2f(hotbar_x + hotbar_width, hotbar_y)
        glTexCoord2f(1, 1); glVertex2f(hotbar_x + hotbar_width, hotbar_y + hotbar_height)
        glTexCoord2f(0, 1); glVertex2f(hotbar_x, hotbar_y + hotbar_height)
        glEnd()
        # Unbind hotbar texture
        glBindTexture(GL_TEXTURE_2D, 0)
        # Render inventory items (both rusty_sword and skeleton_sword)
        slot_width = hotbar_width // self.num_slots
        slot_height = hotbar_height * 0.8  # 80% of hotbar height
        for i in range(self.num_slots):
            slot_x = hotbar_x + (i * slot_width) + (slot_width * 0.1)  # 10% margin
            slot_y = hotbar_y + (hotbar_height - slot_height) / 2  # Center vertically
            item_data = self.inventory[i]
            if item_data["type"] == "rusty_sword" and self.renderer.weapon_texture_id:
                glBindTexture(GL_TEXTURE_2D, self.renderer.weapon_texture_id)
                glBegin(GL_QUADS)
                glTexCoord2f(0, 0); glVertex2f(slot_x, slot_y)
                glTexCoord2f(1, 0); glVertex2f(slot_x + slot_width * 0.8, slot_y)
                glTexCoord2f(1, 1); glVertex2f(slot_x + slot_width * 0.8, slot_y + slot_height)
                glTexCoord2f(0, 1); glVertex2f(slot_x, slot_y + slot_height)
                glEnd()
                glBindTexture(GL_TEXTURE_2D, 0)
            elif item_data["type"] == "skeleton_sword" and self.renderer.skeleton_sword_texture_id:
                glBindTexture(GL_TEXTURE_2D, self.renderer.skeleton_sword_texture_id)
                glBegin(GL_QUADS)
                glTexCoord2f(0, 0); glVertex2f(slot_x, slot_y)
                glTexCoord2f(1, 0); glVertex2f(slot_x + slot_width * 0.8, slot_y)
                glTexCoord2f(1, 1); glVertex2f(slot_x + slot_width * 0.8, slot_y + slot_height)
                glTexCoord2f(0, 1); glVertex2f(slot_x, slot_y + slot_height)
                glEnd()
                glBindTexture(GL_TEXTURE_2D, 0)
            elif item_data["type"] == "health_potion" and self.renderer.potion_health_texture_id:
                glBindTexture(GL_TEXTURE_2D, self.renderer.potion_health_texture_id)
                glBegin(GL_QUADS)
                glTexCoord2f(0, 1); glVertex2f(slot_x, slot_y)
                glTexCoord2f(1, 1); glVertex2f(slot_x + slot_width * 0.8, slot_y)
                glTexCoord2f(1, 0); glVertex2f(slot_x + slot_width * 0.8, slot_y + slot_height)
                glTexCoord2f(0, 0); glVertex2f(slot_x, slot_y + slot_height)
                glEnd()
                glBindTexture(GL_TEXTURE_2D, 0)
            elif item_data["type"] == "magic_potion" and self.renderer.potion_magic_texture_id:
                glBindTexture(GL_TEXTURE_2D, self.renderer.potion_magic_texture_id)
                glBegin(GL_QUADS)
                glTexCoord2f(0, 1); glVertex2f(slot_x, slot_y)
                glTexCoord2f(1, 1); glVertex2f(slot_x + slot_width * 0.8, slot_y)
                glTexCoord2f(1, 0); glVertex2f(slot_x + slot_width * 0.8, slot_y + slot_height)
                glTexCoord2f(0, 0); glVertex2f(slot_x, slot_y + slot_height)
                glEnd()
                glBindTexture(GL_TEXTURE_2D, 0)
            elif item_data["type"] == "fire_scroll" and self.renderer.scroll_fire_texture_id:
                glBindTexture(GL_TEXTURE_2D, self.renderer.scroll_fire_texture_id)
                glBegin(GL_QUADS)
                glTexCoord2f(0, 1); glVertex2f(slot_x, slot_y)
                glTexCoord2f(1, 1); glVertex2f(slot_x + slot_width * 0.8, slot_y)
                glTexCoord2f(1, 0); glVertex2f(slot_x + slot_width * 0.8, slot_y + slot_height)
                glTexCoord2f(0, 0); glVertex2f(slot_x, slot_y + slot_height)
                glEnd()
                glBindTexture(GL_TEXTURE_2D, 0)
            elif item_data["type"] == "key" and hasattr(self.renderer, 'key_texture_id') and self.renderer.key_texture_id:
                glBindTexture(GL_TEXTURE_2D, self.renderer.key_texture_id)
                glBegin(GL_QUADS)
                glTexCoord2f(0, 1); glVertex2f(slot_x, slot_y)
                glTexCoord2f(1, 1); glVertex2f(slot_x + slot_width * 0.8, slot_y)
                glTexCoord2f(1, 0); glVertex2f(slot_x + slot_width * 0.8, slot_y + slot_height)
                glTexCoord2f(0, 0); glVertex2f(slot_x, slot_y + slot_height)
                glEnd()
                glBindTexture(GL_TEXTURE_2D, 0)
        # Restore OpenGL state
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        # Restore projection matrix
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
    
    def render_equipped_weapon(self):
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
        if self.inventory[self.selected_slot]["type"] == "rusty_sword":
            if not self.renderer.held_weapon_texture_id:
                return
            held_texture_id = self.renderer.held_weapon_texture_id
            held_width = 340  # Increased size
            held_height = held_width * (500/255)  # Updated to 255x500 aspect ratio
        elif self.inventory[self.selected_slot]["type"] == "skeleton_sword":
            if not self.renderer.held_skeleton_sword_texture_id:
                return
            held_texture_id = self.renderer.held_skeleton_sword_texture_id
            held_width = 300  # Slightly smaller than rusty sword
            held_height = held_width * (250/108)
        elif self.inventory[self.selected_slot]["type"] == "health_potion":
            if not self.renderer.potion_health_texture_id:
                return
            held_texture_id = self.renderer.potion_health_texture_id
            held_width = 200
            held_height = held_width * (160/110)  # Potion aspect ratio
        elif self.inventory[self.selected_slot]["type"] == "magic_potion":
            if not self.renderer.potion_magic_texture_id:
                return
            held_texture_id = self.renderer.potion_magic_texture_id
            held_width = 200
            held_height = held_width * (160/110)  # Potion aspect ratio
        elif self.inventory[self.selected_slot]["type"] == "fire_scroll":
            if not self.renderer.spell_fire_texture_id:
                return
            held_texture_id = self.renderer.spell_fire_texture_id
            held_width = 200
            held_height = held_width * (384/146)  # Spell fire aspect ratio (146x384)
        elif self.inventory[self.selected_slot]["type"] == "magic_scroll":
            if not hasattr(self.renderer, 'spell_magic_texture_id') or not self.renderer.spell_magic_texture_id:
                return
            held_texture_id = self.renderer.spell_magic_texture_id
            held_width = 200
            held_height = held_width * (384/146)  # Spell magic aspect ratio (146x384)
        elif self.inventory[self.selected_slot]["type"] == "key":
            if not hasattr(self.renderer, 'key_texture_id') or not self.renderer.key_texture_id:
                return
            held_texture_id = self.renderer.key_texture_id
            held_width = 150
            held_height = held_width * (670/344)  # Key aspect ratio
        else:
            return
        swing_rotation = 0
        # Show swing animation for weapons and spells
        if self.is_swinging and self.inventory[self.selected_slot]["type"] in ["rusty_sword", "skeleton_sword", "fire_scroll", "magic_scroll", "key"]:
            current_time = pygame.time.get_ticks()
            elapsed_time = current_time - self.swing_start_time
            if elapsed_time < self.swing_duration:
                progress = elapsed_time / self.swing_duration
                if progress < 0.5:
                    swing_rotation = 75 * (progress * 2)
                else:
                    swing_rotation = 75 * (2 - progress * 2)
            else:
                self.is_swinging = False
                swing_rotation = 0
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, self.width, 0, self.height)
        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glBindTexture(GL_TEXTURE_2D, held_texture_id)
        weapon_x = self.width - held_width - 20
        # Move fire spell to the left
        if self.inventory[self.selected_slot]["type"] == "fire_scroll":
            weapon_x -= 50  # Move 50 pixels to the left
        elif self.inventory[self.selected_slot]["type"] == "magic_scroll":
            weapon_x -= 50  # Move 50 pixels to the left
        weapon_y = -50
        glPushMatrix()
        glTranslatef(weapon_x + held_width/2, weapon_y + held_height/2, 0)
        # Different rotation for weapons vs potions
        if self.inventory[self.selected_slot]["type"] in ["rusty_sword", "skeleton_sword", "fire_scroll", "key"]:
            glRotatef(15 + swing_rotation, 0, 0, 1)
        elif self.inventory[self.selected_slot]["type"] == "magic_scroll":
            glRotatef(15 + swing_rotation, 0, 0, 1)
        else:
            glRotatef(5, 0, 0, 1)  # Slight tilt for potions
        glTranslatef(-(weapon_x + held_width/2), -(weapon_y + held_height/2), 0)
        glBegin(GL_QUADS)
        # Flip texture coordinates for potions to show right-side up
        if self.inventory[self.selected_slot]["type"] in ["health_potion", "magic_potion"]:
            glTexCoord2f(0, 1); glVertex2f(weapon_x, weapon_y)
            glTexCoord2f(1, 1); glVertex2f(weapon_x + held_width, weapon_y)
            glTexCoord2f(1, 0); glVertex2f(weapon_x + held_width, weapon_y + held_height)
            glTexCoord2f(0, 0); glVertex2f(weapon_x, weapon_y + held_height)
        else:
            glTexCoord2f(0, 1); glVertex2f(weapon_x, weapon_y)
            glTexCoord2f(1, 1); glVertex2f(weapon_x + held_width, weapon_y)
            glTexCoord2f(1, 0); glVertex2f(weapon_x + held_width, weapon_y + held_height)
            glTexCoord2f(0, 0); glVertex2f(weapon_x, weapon_y + held_height)
        glEnd()
        glPopMatrix()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
    
    def render_health_bar(self):
        """Render the health bar at the top left of the screen"""
        if not self.renderer.health_bar_texture_id:
            return
        # Set texture environment to REPLACE for UI
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
        # Save current OpenGL state
        glPushMatrix()
        glLoadIdentity()
        # Disable depth testing for 2D overlay
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        # Set up orthographic projection for 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, self.width, 0, self.height)
        glMatrixMode(GL_MODELVIEW)
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # Bind health bar texture
        glBindTexture(GL_TEXTURE_2D, self.renderer.health_bar_texture_id)
        # Calculate health bar position and size (top left)
        health_bar_width = 256  # Scaled down from 1024 (1/4 size)
        health_bar_height = 79  # Scaled down from 318 (1/4 size, maintaining aspect ratio)
        health_bar_x = 20  # 20 pixels from left edge
        health_bar_y = self.height - health_bar_height - 20  # 20 pixels from top
        # Render health bar quad
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(health_bar_x, health_bar_y)
        glTexCoord2f(1, 0); glVertex2f(health_bar_x + health_bar_width, health_bar_y)
        glTexCoord2f(1, 1); glVertex2f(health_bar_x + health_bar_width, health_bar_y + health_bar_height)
        glTexCoord2f(0, 1); glVertex2f(health_bar_x, health_bar_y + health_bar_height)
        glEnd()
        # Unbind health bar texture
        glBindTexture(GL_TEXTURE_2D, 0)
        # Render health fill overlay only if health > 0
        if self.renderer.health_fill_texture_id and self.current_health > 0:
            # Bind health fill texture
            glBindTexture(GL_TEXTURE_2D, self.renderer.health_fill_texture_id)
            # Calculate health fill size (smaller than meter, maintaining aspect ratio)
            health_fill_scale = 0.8  # Make health fill 80% of meter size
            health_fill_width = health_bar_width * health_fill_scale
            # Calculate height based on health.png aspect ratio (1024x197)
            health_aspect_ratio = 197 / 1024  # height/width ratio
            health_fill_height = health_fill_width * health_aspect_ratio
            # Calculate health fill position (centered within meter)
            health_fill_x = health_bar_x + (health_bar_width - health_fill_width) / 2
            health_fill_y = health_bar_y + (health_bar_height - health_fill_height) / 2
            # Calculate health fill width based on current health percentage
            health_percentage = self.current_health / self.max_health
            actual_health_width = health_fill_width * health_percentage
            # Render health fill quad (smaller than meter, width based on health)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(health_fill_x, health_fill_y)
            glTexCoord2f(health_percentage, 0); glVertex2f(health_fill_x + actual_health_width, health_fill_y)
            glTexCoord2f(health_percentage, 1); glVertex2f(health_fill_x + actual_health_width, health_fill_y + health_fill_height)
            glTexCoord2f(0, 1); glVertex2f(health_fill_x, health_fill_y + health_fill_height)
            glEnd()
            # Unbind health fill texture
            glBindTexture(GL_TEXTURE_2D, 0)
        # Restore OpenGL state
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        # Restore projection matrix
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
    
    def render_mana_bar(self):
        """Render the mana bar below the health bar"""
        if not self.renderer.mana_bar_texture_id:
            return
        # Set texture environment to REPLACE for UI
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
        # Save current OpenGL state
        glPushMatrix()
        glLoadIdentity()
        # Disable depth testing for 2D overlay
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        # Set up orthographic projection for 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, self.width, 0, self.height)
        glMatrixMode(GL_MODELVIEW)
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # Bind mana bar texture
        glBindTexture(GL_TEXTURE_2D, self.renderer.mana_bar_texture_id)
        # Calculate mana bar position and size (below health bar)
        mana_bar_width = 256  # Same size as health bar
        mana_bar_height = 79  # Same size as health bar
        mana_bar_x = 20  # Same x position as health bar
        mana_bar_y = self.height - mana_bar_height - 20 - mana_bar_height - 10  # Below health bar with 10px gap
        # Render mana bar quad
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(mana_bar_x, mana_bar_y)
        glTexCoord2f(1, 0); glVertex2f(mana_bar_x + mana_bar_width, mana_bar_y)
        glTexCoord2f(1, 1); glVertex2f(mana_bar_x + mana_bar_width, mana_bar_y + mana_bar_height)
        glTexCoord2f(0, 1); glVertex2f(mana_bar_x, mana_bar_y + mana_bar_height)
        glEnd()
        # Unbind mana bar texture
        glBindTexture(GL_TEXTURE_2D, 0)
        # Render mana fill overlay only if mana > 0
        if self.renderer.mana_fill_texture_id and self.current_mana > 0:
            # Bind mana fill texture
            glBindTexture(GL_TEXTURE_2D, self.renderer.mana_fill_texture_id)
            # Calculate mana fill size (smaller than meter, maintaining aspect ratio)
            mana_fill_scale = 0.8  # Make mana fill 80% of meter size
            mana_fill_width = mana_bar_width * mana_fill_scale
            # Calculate height based on magic.png aspect ratio (same as health.png)
            mana_aspect_ratio = 197 / 1024  # height/width ratio (same as health.png)
            mana_fill_height = mana_fill_width * mana_aspect_ratio
            # Calculate mana fill position (centered within meter)
            mana_fill_x = mana_bar_x + (mana_bar_width - mana_fill_width) / 2
            mana_fill_y = mana_bar_y + (mana_bar_height - mana_fill_height) / 2
            # Calculate mana fill width based on current mana percentage
            mana_percentage = self.current_mana / self.max_mana
            actual_mana_width = mana_fill_width * mana_percentage
            # Render mana fill quad (smaller than meter, width based on mana)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(mana_fill_x, mana_fill_y)
            glTexCoord2f(mana_percentage, 0); glVertex2f(mana_fill_x + actual_mana_width, mana_fill_y)
            glTexCoord2f(mana_percentage, 1); glVertex2f(mana_fill_x + actual_mana_width, mana_fill_y + mana_fill_height)
            glTexCoord2f(0, 1); glVertex2f(mana_fill_x, mana_fill_y + mana_fill_height)
            glEnd()
            # Unbind mana fill texture
            glBindTexture(GL_TEXTURE_2D, 0)
        # Restore OpenGL state
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        # Restore projection matrix
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
    
    def render(self):
        """Render the scene"""
        glClear(int(GL_COLOR_BUFFER_BIT) | int(GL_DEPTH_BUFFER_BIT))
        glLoadIdentity()
        
        # Apply camera rotation and position
        glRotatef(-self.camera_rot[0] * 180 / math.pi, 1, 0, 0)  # Enable pitch rotation (up/down)
        glRotatef(-self.camera_rot[1] * 180 / math.pi, 0, 1, 0)  # Only yaw rotation (left/right)
        glTranslatef(-self.camera_pos[0], -self.camera_pos[1], -self.camera_pos[2])
        
        # Set up basic ambient lighting
        glLightfv(GL_LIGHT0, GL_POSITION, [0, 10, 0, 1])  # Light from above
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1])  # Moderate ambient lighting
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.4, 0.4, 0.4, 1])  # Moderate diffuse lighting
        
        # Add torch lights (stable lighting)
        if hasattr(self.dungeon_generator, 'torch_positions') and self.dungeon_generator.torch_positions:
            # Calculate distances to player for all torches
            torch_distances = []
            for torch_data in self.dungeon_generator.torch_positions:
                if len(torch_data) == 6:  # New format with face coordinates
                    torch_x, torch_z, dx, dz, face_x, face_z = torch_data
                else:  # Old format, skip
                    continue
                distance = math.sqrt((torch_x - self.camera_pos[0])**2 + (torch_z - self.camera_pos[2])**2)
                torch_distances.append((distance, torch_x, torch_z, dx, dz, face_x, face_z))
            
            # Sort by distance and take the 3 closest torches
            torch_distances.sort()
            closest_torches = torch_distances[:3]
            
            # Enable lights for closest torches
            glEnable(GL_LIGHT1)
            glEnable(GL_LIGHT2)
            glEnable(GL_LIGHT3)
            
            # Set up torch lights with stable lighting
            torch_lights = [
                (GL_LIGHT1, [4.0, 2.0, 0.8, 1]),  # Very bright orange torch light
                (GL_LIGHT2, [3.8, 1.9, 0.8, 1]),
                (GL_LIGHT3, [4.2, 2.1, 0.9, 1]),
            ]
            
            for i, (distance, torch_x, torch_z, dx, dz, face_x, face_z) in enumerate(closest_torches):
                if i < len(torch_lights):
                    light_id, light_color = torch_lights[i]
                    # Place the light at the face position
                    torch_light_pos = [face_x, 1.5, face_z, 1.0]
                    glLightfv(light_id, GL_POSITION, torch_light_pos)
                    glLightfv(light_id, GL_AMBIENT, [0.4, 0.2, 0.1, 1])  # Higher ambient for visibility
                    glLightfv(light_id, GL_DIFFUSE, light_color)
                    glLightf(light_id, GL_CONSTANT_ATTENUATION, 1.0)
                    glLightf(light_id, GL_LINEAR_ATTENUATION, 0.3)  # Reduced attenuation for stability
                    glLightf(light_id, GL_QUADRATIC_ATTENUATION, 0.1)  # Reduced attenuation for stability
                    
                    # Make it a spotlight pointing away from the wall
                    glLightf(light_id, GL_SPOT_CUTOFF, 60.0)  # Wider cone for more stable lighting
                    glLightf(light_id, GL_SPOT_EXPONENT, 1.0)  # Less focused for stability
                    # Direction vector pointing away from the wall
                    spot_direction = [-dx, -0.1, -dz]  # Point slightly downward and away from wall
                    glLightfv(light_id, GL_SPOT_DIRECTION, spot_direction)
            
            # Disable unused lights
            glDisable(GL_LIGHT4)
            glDisable(GL_LIGHT5)
        else:
            # Disable torch lights if no torches
            glDisable(GL_LIGHT1)
            glDisable(GL_LIGHT2)
            glDisable(GL_LIGHT3)
            glDisable(GL_LIGHT4)
            glDisable(GL_LIGHT5)
        
        # Render dungeon
        self.renderer.render_dungeon(self.dungeon_grid, self.camera_pos, self.dungeon_generator.torch_positions, self.dungeon_generator.chest_positions, self.camera_rot)
        
        # Render skeletons
        self.renderer.render_npcs(self.skeletons, self.camera_pos, self.camera_rot)
        
        # Render dropped items
        self.renderer.render_dropped_items(self.dropped_items, self.camera_pos)
        
        # Render fireballs
        self.renderer.render_fireballs(self.fireballs, self.camera_pos)
        
        # Always render the key if it exists and hasn't been picked up
        if hasattr(self, 'key_item') and self.key_item and not self.key_item.collected:
            self.renderer.render_dropped_item(self.key_item, self.camera_pos)
        
        # Render all UI elements last (on top of everything)
        # Render hotbar
        self.render_hotbar()
        
        # Render interact prompt if near a chest or item
        if self.nearby_chest is not None or (self.nearby_item is not None and not self.nearby_item.collected):
            self.renderer.render_interact_prompt(self.width, self.height)
        
        # Render equipped weapon
        self.render_equipped_weapon()
        
        # Render health bar
        self.render_health_bar()
        
        # Render mana bar
        self.render_mana_bar()
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        
        while True:
            if not self.handle_input():
                break
            
            self.update_skeletons()
            self.render()
            clock.tick(60)
        
        pygame.quit()

    def update_skeletons(self):
        alive = []
        player_tile = (int(self.camera_pos[0]), int(self.camera_pos[2]))
        for skel in self.skeletons:
            if skel.is_alive:
                if skel.flash_timer > 0:
                    skel.flash_timer -= 1
                dx = self.camera_pos[0] - skel.center_x
                dz = self.camera_pos[2] - skel.center_z
                dist = math.sqrt(dx*dx + dz*dz)
                activation_radius = 7.0
                min_distance = 1.7
                attacked = False
                if skel.attack_cooldown > 0:
                    skel.attack_cooldown -= 1
                else:
                    if dist < 2.0:
                        # Set damage based on type
                        if skel.npc_type == "ghoul":
                            damage = 5
                        elif skel.npc_type == "skeleton":
                            damage = 7
                        elif skel.npc_type == "ghost":
                            damage = 10
                        else:
                            damage = 5
                        self.current_health = max(0, self.current_health - damage)
                        skel.attack_cooldown = 40
                        skel.frozen_timer = 10
                        attacked = True
                if skel.frozen_timer > 0:
                    skel.frozen_timer -= 1
                # Only move if not attacking, not frozen, not too close, and within activation radius
                if not attacked and skel.frozen_timer == 0 and dist < activation_radius and dist > min_distance:
                    skel.update_path(self.dungeon_grid, player_tile)
                    skel.move_along_path(self.check_collision, speed=0.05)
                alive.append(skel)
            else:
                # Only skeletons can drop skeleton sword
                if skel.npc_type == "skeleton" and random.random() < 0.4:
                    self.dropped_items.append(DroppedItem('skeleton_sword', skel.center_x, skel.center_z))
                # Only ghosts can drop magic scroll
                if skel.npc_type == "ghost" and random.random() < 0.15:
                    self.dropped_items.append(DroppedItem('magic_scroll', skel.center_x, skel.center_z))
        
        # Update fireballs and check for skeleton collisions
        active_fireballs = []
        for fireball in self.fireballs:
            fireball.update()
            
            # Check collision with skeletons
            for skeleton in self.skeletons:
                if fireball.check_collision_with_skeleton(skeleton):
                    print(f"Fireball hit skeleton! Skeleton health: {skeleton.health}")
                    break
            
            # Keep only active fireballs
            if fireball.active:
                active_fireballs.append(fireball)
        
        self.fireballs = active_fireballs
        
        # Remove dropped items after 120 seconds, but never remove the key
        now = time.time()
        self.dropped_items = [item for item in self.dropped_items if (item.item_type == 'key') or (not item.collected and (now - item.spawn_time) < 120)]
        self.skeletons = alive
        self.check_item_pickup()

    def check_item_pickup(self):
        pass  # Method removed as it is unused

    def try_attack_skeletons(self):
        # Only attack if a sword is equipped and not already swinging
        if self.inventory[self.selected_slot]["type"] not in ("rusty_sword", "skeleton_sword"):
            return
        # Attack range and angle
        attack_range = 1.8  # About 2 tiles
        attack_angle = math.radians(60)  # 60 degree cone
        # Player forward vector
        yaw = self.camera_rot[1]
        forward = np.array([-math.sin(yaw), -math.cos(yaw)])
        # Set damage based on weapon
        if self.inventory[self.selected_slot]["type"] == "rusty_sword":
            damage = 5
        elif self.inventory[self.selected_slot]["type"] == "skeleton_sword":
            damage = 10
        else:
            damage = 0
        for skel in self.skeletons:
            if not skel.is_alive:
                continue
            # Vector from player to skeleton
            to_skel = np.array([skel.center_x - self.camera_pos[0], skel.center_z - self.camera_pos[2]])
            dist = np.linalg.norm(to_skel)
            if dist > attack_range:
                continue
            if dist == 0:
                continue
            to_skel_norm = to_skel / dist
            dot = np.dot(forward, to_skel_norm)
            angle = math.acos(np.clip(dot, -1, 1))
            if angle < attack_angle / 2:
                # Hit! Apply damage and knockback
                knockback = to_skel_norm * 0.7  # Move back 0.7 units
                skel.take_damage(damage, knockback_vec=knockback, collision_checker=self.check_collision)

    def cast_fire_spell(self):
        """Cast a fire spell that creates a fireball projectile"""
        if self.current_mana < 5:
            print("Not enough mana to cast fire spell!")
            return
        self.current_mana -= 5
        print(f"Cast fire spell! Consumed 5 mana. Current mana: {self.current_mana}/{self.max_mana}")
        # Calculate fireball spawn position (in front of player)
        pitch = self.camera_rot[0]
        yaw = self.camera_rot[1]
        spawn_distance = 1.0
        # 3D direction
        direction_x = -math.sin(yaw) * math.cos(pitch)
        direction_y = math.sin(pitch)
        direction_z = -math.cos(yaw) * math.cos(pitch)
        spawn_x = self.camera_pos[0] + direction_x * spawn_distance
        spawn_z = self.camera_pos[2] + direction_z * spawn_distance
        # Create fireball projectile (2D, ignore y for now)
        fireball = Fireball(spawn_x, spawn_z, direction_x, direction_z, max_distance=7.0, is_magic=False, collision_checker=self.check_collision)
        self.fireballs.append(fireball)
        print(f"Fireball spawned at ({spawn_x:.2f}, {spawn_z:.2f})")

    def check_nearby_items(self):
        """Check if player is near any dropped items and update nearby_item"""
        self.nearby_item = None
        min_dist = float('inf')
        
        # Check regular dropped items
        for item in self.dropped_items:
            if item.collected:
                continue
            dist = math.sqrt((item.x - self.camera_pos[0])**2 + (item.z - self.camera_pos[2])**2)
            if dist < 1.0 and dist < min_dist:
                self.nearby_item = item
                min_dist = dist
        
        # Check key item
        if hasattr(self, 'key_item') and self.key_item and not self.key_item.collected:
            dist = math.sqrt((self.key_item.x - self.camera_pos[0])**2 + (self.key_item.z - self.camera_pos[2])**2)
            if dist < 1.0 and dist < min_dist:
                self.nearby_item = self.key_item
                min_dist = dist

    def pick_up_item(self, item):
        if item.collected:
            return
        placed = False
        
        # Handle key item specially - add to inventory
        if item.item_type == 'key':
            for i in range(self.num_slots):
                if self.inventory[i]["type"] == "empty":
                    self.inventory[i] = {"type": item.item_type, "count": 1}
                    item.collected = True
                    placed = True
                    print('Key picked up!')
                    break
            if not placed:
                print('Inventory full! Cannot pick up key.')
            return
        
        # Handle other items
        if item.item_type in ["health_potion", "magic_potion"]:
            for i in range(self.num_slots):
                if (self.inventory[i]["type"] == item.item_type and 
                    self.inventory[i]["count"] > 0):
                    self.inventory[i]["count"] += 1
                    item.collected = True
                    placed = True
                    break
            if not placed:
                for i in range(self.num_slots - 1, -1, -1):
                    if self.inventory[i]["type"] == "empty":
                        self.inventory[i] = {"type": item.item_type, "count": 1}
                        item.collected = True
                        placed = True
                        break
        else:
            for i in range(self.num_slots):
                if self.inventory[i]["type"] == "empty":
                    self.inventory[i] = {"type": item.item_type, "count": 1}
                    item.collected = True
                    placed = True
                    break
        if not placed:
            print('Inventory full! Cannot pick up item.')

    def drop_selected_item(self):
        """Drop the selected item in front of the player and shift items left to fill the gap."""
        slot = self.selected_slot
        item_data = self.inventory[slot]
        if item_data["type"] == "empty":
            return  # Nothing to drop
        # Calculate drop position in front of player
        yaw = self.camera_rot[1]
        drop_distance = 1.0
        drop_x = self.camera_pos[0] + (-math.sin(yaw)) * drop_distance
        drop_z = self.camera_pos[2] + (-math.cos(yaw)) * drop_distance
        # Only allow dropping known item types
        if item_data["type"] in ("rusty_sword", "skeleton_sword", "health_potion", "magic_potion", "fire_scroll", "key"):
            self.dropped_items.append(DroppedItem(item_data["type"], drop_x, drop_z))
            print(f"Dropped {item_data['type']} from slot {slot} at ({drop_x:.2f}, {drop_z:.2f})")
        # Handle stacked items
        if item_data["count"] > 1:
            item_data["count"] -= 1
        else:
            # Remove the item and shift all items to the right of this slot left
            for i in range(slot, self.num_slots - 1):
                self.inventory[i] = self.inventory[i + 1]
            self.inventory[self.num_slots - 1] = {"type": "empty", "count": 0}
            # If the selected slot is now empty, move selection left if possible
            if self.inventory[slot]["type"] == "empty" and slot > 0:
                self.selected_slot = slot - 1

    def use_health_potion(self):
        """Use a health potion to heal the player by 10 HP"""
        slot = self.selected_slot
        item_data = self.inventory[slot]
        
        if item_data["type"] != "health_potion" or item_data["count"] <= 0:
            return  # Not a health potion or no potions left
        
        # Heal the player
        heal_amount = 10
        old_health = self.current_health
        self.current_health = min(self.max_health, self.current_health + heal_amount)
        actual_heal = self.current_health - old_health
        
        print(f"Used health potion! Healed {actual_heal} HP (Health: {self.current_health}/{self.max_health})")
        
        # Consume one potion
        if item_data["count"] > 1:
            item_data["count"] -= 1
        else:
            # Remove the item and shift all items to the right of this slot left
            for i in range(slot, self.num_slots - 1):
                self.inventory[i] = self.inventory[i + 1]
            self.inventory[self.num_slots - 1] = {"type": "empty", "count": 0}
            # If the selected slot is now empty, move selection left if possible
            if self.inventory[slot]["type"] == "empty" and slot > 0:
                self.selected_slot = slot - 1

    def use_magic_potion(self):
        """Use a magic potion to restore 5 mana"""
        slot = self.selected_slot
        item_data = self.inventory[slot]
        
        if item_data["type"] != "magic_potion" or item_data["count"] <= 0:
            return  # Not a magic potion or no potions left
        
        # Restore mana
        restore_amount = 5
        old_mana = self.current_mana
        self.current_mana = min(self.max_mana, self.current_mana + restore_amount)
        actual_restore = self.current_mana - old_mana
        
        print(f"Used magic potion! Restored {actual_restore} mana (Mana: {self.current_mana}/{self.max_mana})")
        
        # Consume one potion
        if item_data["count"] > 1:
            item_data["count"] -= 1
        else:
            # Remove the item and shift all items to the right of this slot left
            for i in range(slot, self.num_slots - 1):
                self.inventory[i] = self.inventory[i + 1]
            self.inventory[self.num_slots - 1] = {"type": "empty", "count": 0}
            # If the selected slot is now empty, move selection left if possible
            if self.inventory[slot]["type"] == "empty" and slot > 0:
                self.selected_slot = slot - 1

    def cast_magic_spell(self):
        """Cast a magic spell that creates a magicball projectile"""
        if self.current_mana < 5:
            print("Not enough mana to cast magic spell!")
            return
        self.current_mana -= 5
        print(f"Cast magic spell! Consumed 5 mana. Current mana: {self.current_mana}/{self.max_mana}")
        pitch = self.camera_rot[0]
        yaw = self.camera_rot[1]
        spawn_distance = 1.0
        direction_x = -math.sin(yaw) * math.cos(pitch)
        direction_y = math.sin(pitch)
        direction_z = -math.cos(yaw) * math.cos(pitch)
        spawn_x = self.camera_pos[0] + direction_x * spawn_distance
        spawn_z = self.camera_pos[2] + direction_z * spawn_distance
        magicball = Fireball(spawn_x, spawn_z, direction_x, direction_z, max_distance=7.0, is_magic=True, collision_checker=self.check_collision)
        magicball.active = True
        self.fireballs.append(magicball)
        print(f"Magicball spawned at ({spawn_x:.2f}, {spawn_z:.2f})")

    def find_valid_spawn_position(self):
        """Find a valid spawn position for the player (walkable tile near center)"""
        center_x, center_z = len(self.dungeon_grid[0]) // 2, len(self.dungeon_grid) // 2
        
        # Start from center and search in expanding circles
        for radius in range(0, max(len(self.dungeon_grid), len(self.dungeon_grid[0]))):
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    # Only check positions at the current radius
                    if abs(dx) == radius or abs(dz) == radius:
                        x, z = center_x + dx, center_z + dz
                        # Check bounds
                        if 0 <= x < len(self.dungeon_grid[0]) and 0 <= z < len(self.dungeon_grid):
                            if self.dungeon_grid[z][x] == 0:  # Walkable
                                spawn_x = x + 0.5
                                spawn_z = z + 0.5
                                print(f"Player spawned at ({spawn_x:.2f}, {spawn_z:.2f})")
                                return (spawn_x, spawn_z)
        
        # Fallback: find any walkable tile
        for z in range(len(self.dungeon_grid)):
            for x in range(len(self.dungeon_grid[0])):
                if self.dungeon_grid[z][x] == 0:  # Walkable
                    spawn_x = x + 0.5
                    spawn_z = z + 0.5
                    print(f"Player spawned at fallback position ({spawn_x:.2f}, {spawn_z:.2f})")
                    return (spawn_x, spawn_z)
        
        # Last resort: spawn at center
        print("Warning: No walkable tiles found, spawning at center")
        return (center_x + 0.5, center_z + 0.5)

    def spawn_key_item(self):
        # Find the farthest walkable tile from the player
        max_dist = -1
        farthest_pos = None
        player_x, player_z = int(self.camera_pos[0]), int(self.camera_pos[2])
        for z in range(len(self.dungeon_grid)):
            for x in range(len(self.dungeon_grid[0])):
                if self.dungeon_grid[z][x] == 0:  # Walkable
                    dist = math.sqrt((x - player_x) ** 2 + (z - player_z) ** 2)
                    if dist > max_dist:
                        max_dist = dist
                        farthest_pos = (x + 0.5, z + 0.5)
        if farthest_pos:
            self.key_item = DroppedItem('key', farthest_pos[0], farthest_pos[1])
            self.key_spawned = True
            print(f"Key spawned at ({farthest_pos[0]:.2f}, {farthest_pos[1]:.2f})")
        else:
            print("Failed to spawn key - no walkable tiles found!")

if __name__ == "__main__":
    game = DungeonCrawler()
    game.run()
