import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import random
import math
from PIL import Image
import os

class DungeonGenerator:
    def __init__(self, width=51, height=51):
        self.width = width if width % 2 == 1 else width + 1
        self.height = height if height % 2 == 1 else height + 1
        self.grid = [[1 for _ in range(self.width)] for _ in range(self.height)]

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
        for room_x, room_y, room_w, room_h in self.rooms:
            if random.random() < 0.8:  # 80% chance to spawn a skeleton in a chest room
                skel_x = room_x + room_w // 2
                skel_z = room_y + room_h // 2
                if self.grid[skel_z][skel_x] == 0:
                    center_x = skel_x + 0.5
                    center_z = skel_z + 0.5
                    self.skeletons.append(Skeleton(skel_x, skel_z, center_x, center_z))
        # Random chance to spawn skeletons elsewhere
        for z in range(1, self.height-1):
            for x in range(1, self.width-1):
                if self.grid[z][x] == 0 and random.random() < 0.01:
                    center_x = x + 0.5
                    center_z = z + 0.5
                    self.skeletons.append(Skeleton(x, z, center_x, center_z))
        print(f"Placed {len(self.skeletons)} skeletons")
        
        return self.grid

class DungeonRenderer:
    def __init__(self):
        self.texture_id = None
        self.floor_texture_id = None
        self.ceiling_texture_id = None
        self.torch_texture_id = None
        self.chest_texture_id = None
        self.interact_texture_id = None
        self.weapon_texture_id = None
        self.health_bar_texture_id = None
        self.health_fill_texture_id = None
        self.skeleton_texture_id = None
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
            
            # Load weapon texture
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
            
            # Unbind texture to avoid state issues
            glBindTexture(GL_TEXTURE_2D, 0)
            print("All textures loaded successfully")
            print("Starter weapon 'rusty_sword' added to inventory slot 0")
        except Exception as e:
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
    
    def render_wall(self, x, z, height=2.0, camera_pos=None):
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
    
    def render_floor(self, x, z, camera_pos=None):
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
    
    def render_ceiling(self, x, z, height=2.0, camera_pos=None):
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
    
    def render_torch(self, x, z, dx, dz, face_x, face_z, height=1.5, camera_pos=None):
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
    
    def render_chest(self, x, z, center_x, center_z, height=0.1, camera_pos=None):
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
                self.render_ceiling(x, z, camera_pos=camera_pos)
        
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

    def render_skeleton(self, skeleton, camera_pos=None):
        """Render a skeleton as a billboarded sprite, with strong additive tint for red flash/black death, and upright sprite"""
        if not skeleton.is_alive and skeleton.death_timer <= 0:
            return
        glEnable(GL_BLEND)
        # Use additive blending for red flash or black death
        use_additive = (not skeleton.is_alive and skeleton.death_timer > 0) or (skeleton.flash_timer > 0)
        if use_additive:
            glBlendFunc(GL_ONE, GL_ONE)
        else:
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        if self.skeleton_texture_id:
            glBindTexture(GL_TEXTURE_2D, self.skeleton_texture_id)
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        # Set color: red flash, black if dead, else white
        if not skeleton.is_alive and skeleton.death_timer > 0:
            glColor4f(0.2, 0.2, 0.2, 1.0)  # Black (additive, so not pure 0)
        elif skeleton.flash_timer > 0:
            glColor4f(2.0, 0.1, 0.1, 1.0)  # Strong red (additive, >1.0 for more effect)
        else:
            glColor4f(1.0, 1.0, 1.0, 1.0)
        glDisable(GL_LIGHTING)
        skel_width = 0.7
        skel_height = skel_width * (984/718)
        if camera_pos:
            to_player_x = camera_pos[0] - skeleton.center_x
            to_player_z = camera_pos[2] - skeleton.center_z
            angle = math.atan2(to_player_x, to_player_z)
            glPushMatrix()
            glTranslatef(skeleton.center_x, 0.1, skeleton.center_z)
            glRotatef(angle * 180 / math.pi, 0, 1, 0)
            glBegin(GL_QUADS)
            glNormal3f(0, 0, 1)
            # Flip vertically: swap v texture coordinates
            glTexCoord2f(0, 1); glVertex3f(-skel_width/2, 0, 0)
            glTexCoord2f(1, 1); glVertex3f(skel_width/2, 0, 0)
            glTexCoord2f(1, 0); glVertex3f(skel_width/2, skel_height, 0)
            glTexCoord2f(0, 0); glVertex3f(-skel_width/2, skel_height, 0)
            glEnd()
            glPopMatrix()
        else:
            glBegin(GL_QUADS)
            glNormal3f(0, 0, 1)
            glTexCoord2f(0, 1); glVertex3f(skeleton.center_x - skel_width/2, 0, skeleton.center_z)
            glTexCoord2f(1, 1); glVertex3f(skeleton.center_x + skel_width/2, 0, skeleton.center_z)
            glTexCoord2f(1, 0); glVertex3f(skeleton.center_x + skel_width/2, skel_height, skeleton.center_z)
            glTexCoord2f(0, 0); glVertex3f(skeleton.center_x - skel_width/2, skel_height, skeleton.center_z)
            glEnd()
        glEnable(GL_LIGHTING)
        glColor4f(1.0, 1.0, 1.0, 1.0)  # Reset color
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)  # Restore normal blending
        glDisable(GL_BLEND)

    def render_skeletons(self, skeletons, camera_pos=None):
        if not skeletons:
            return
        for skeleton in skeletons:
            self.render_skeleton(skeleton, camera_pos=camera_pos)

class Skeleton:
    def __init__(self, x, z, center_x, center_z, health=20):
        self.x = x
        self.z = z
        self.center_x = center_x
        self.center_z = center_z
        self.health = health
        self.flash_timer = 0  # Frames to flash red
        self.is_alive = True
        self.death_timer = 0  # Frames to show corpse (black)
        self.attack_cooldown = 0  # Frames until next attack
        self.frozen_timer = 0  # Frames to freeze movement after attack

    def take_damage(self, amount, knockback_vec=None, collision_checker=None):
        if not self.is_alive:
            return
        self.health -= amount
        self.flash_timer = 10  # Flash red for 10 frames
        if self.health <= 0:
            self.is_alive = False
            self.death_timer = 60  # 1 second at 60 FPS
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
        move_dist = min(speed, dist)  # Don't overshoot
        move_x = dx / dist * move_dist
        move_z = dz / dist * move_dist
        new_x = self.center_x + move_x
        new_z = self.center_z + move_z
        if not collision_checker(new_x, new_z):
            self.center_x = new_x
            self.center_z = new_z

class DungeonCrawler:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()  # Initialize the mixer for audio
        self.width, self.height = 1200, 800
        pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("3D Dungeon Crawler")
        
        # Camera position and rotation
        self.camera_pos = [25, 1, 25]  # Start in the middle of the dungeon
        self.camera_rot = [0, 0]  # [pitch, yaw] - pitch disabled
        self.mouse_sensitivity = 0.2
        self.move_speed = 0.1
        
        # Initialize dungeon
        self.dungeon_generator = DungeonGenerator(51, 51)
        self.dungeon_grid = self.dungeon_generator.generate_dungeon()
        # Create collision grid as exact copy
        self.collision_grid = [row[:] for row in self.dungeon_grid]
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
        self.inventory = ["empty"] * self.num_slots  # Initialize with string items
        self.inventory[0] = "rusty_sword"  # Place starter item in first slot
        
        # Sword swing animation variables
        self.is_swinging = False
        self.swing_start_time = 0
        self.swing_duration = 500  # Animation duration in milliseconds
        
        # Health system
        self.max_health = 100
        self.current_health = 100
        
        # Mouse control
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        
        # Setup OpenGL
        self.setup_gl()
        
        # Initialize chest proximity check
        self.check_nearby_chests()
        
        # Skeletons
        self.skeletons = self.dungeon_generator.skeletons
    
    def load_background_music(self):
        """Load and start the background music"""
        try:
            pygame.mixer.music.load("assets/dungeon1.wav")
            pygame.mixer.music.set_volume(0.5)  # Set volume to 50%
            pygame.mixer.music.play(-1)  # -1 means loop indefinitely
            print("Background music loaded and started")
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
                elif event.key == pygame.K_LEFT:
                    # Navigate hotbar left
                    self.selected_slot = (self.selected_slot - 1) % self.num_slots
                elif event.key == pygame.K_RIGHT:
                    # Navigate hotbar right
                    self.selected_slot = (self.selected_slot + 1) % self.num_slots
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check if rusty sword is equipped and start swing animation
                    if self.inventory[self.selected_slot] == "rusty_sword" and not self.is_swinging:
                        self.is_swinging = True
                        self.swing_start_time = pygame.time.get_ticks()
                        self.try_attack_skeletons()
            elif event.type == pygame.MOUSEMOTION:
                self.camera_rot[1] -= event.rel[0] * self.mouse_sensitivity * 0.01  # Fixed left/right
                # self.camera_rot[0] -= event.rel[1] * self.mouse_sensitivity * 0.01  # Disabled up/down
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
        
        return True
    
    def interact_with_chest(self):
        """Handle chest interaction - remove the chest from the game"""
        if self.nearby_chest is not None:
            print(f"Attempting to remove chest: {self.nearby_chest}")
            print(f"Current chest positions: {self.dungeon_generator.chest_positions}")
            
            # Remove the chest from the chest positions list
            if hasattr(self.dungeon_generator, 'chest_positions'):
                if self.nearby_chest in self.dungeon_generator.chest_positions:
                    self.dungeon_generator.chest_positions.remove(self.nearby_chest)
                    print(f"Chest opened and removed! Remaining chests: {len(self.dungeon_generator.chest_positions)}")
                    
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
        # Original size: 1024x189, maintaining aspect ratio
        # Scaled down to reasonable size: 320x59 (maintaining aspect ratio)
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
        
        # Render inventory items
        if self.renderer.weapon_texture_id:
            # Calculate slot positions
            slot_width = hotbar_width // self.num_slots
            slot_height = hotbar_height * 0.8  # 80% of hotbar height
            
            # Render items in each slot
            for i in range(self.num_slots):
                if self.inventory[i] == "rusty_sword":
                    # Calculate slot position
                    slot_x = hotbar_x + (i * slot_width) + (slot_width * 0.1)  # 10% margin
                    slot_y = hotbar_y + (hotbar_height - slot_height) / 2  # Center vertically
                    
                    # Bind weapon texture
                    glBindTexture(GL_TEXTURE_2D, self.renderer.weapon_texture_id)
                    
                    # Draw weapon item
                    glBegin(GL_QUADS)
                    glTexCoord2f(0, 0); glVertex2f(slot_x, slot_y)
                    glTexCoord2f(1, 0); glVertex2f(slot_x + slot_width * 0.8, slot_y)
                    glTexCoord2f(1, 1); glVertex2f(slot_x + slot_width * 0.8, slot_y + slot_height)
                    glTexCoord2f(0, 1); glVertex2f(slot_x, slot_y + slot_height)
                    glEnd()
                    
                    # Unbind weapon texture
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
        """Render the equipped weapon on the right side of the screen"""
        # Set texture environment to REPLACE for UI
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
        # Check if the selected slot has the rusty sword
        if self.inventory[self.selected_slot] == "rusty_sword":
            if not self.renderer.weapon_texture_id:
                return
            
            # Calculate swing animation rotation
            swing_rotation = 0
            if self.is_swinging:
                current_time = pygame.time.get_ticks()
                elapsed_time = current_time - self.swing_start_time
                if elapsed_time < self.swing_duration:
                    # Calculate swing progress (0 to 1)
                    progress = elapsed_time / self.swing_duration
                    # Create a swing arc: start at 0, peak at 75 degrees, return to 0
                    if progress < 0.5:
                        # First half: swing to the right (0 to 75 degrees)
                        swing_rotation = 75 * (progress * 2)
                    else:
                        # Second half: swing back (75 to 0 degrees)
                        swing_rotation = 75 * (2 - progress * 2)
                else:
                    # Animation finished
                    self.is_swinging = False
                    swing_rotation = 0
            
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
            
            # Bind weapon texture
            glBindTexture(GL_TEXTURE_2D, self.renderer.weapon_texture_id)
            
            # Calculate weapon position (right side, positioned like holding it)
            weapon_width = 350  # Slightly bigger size for held weapon
            weapon_height = 525  # Maintain aspect ratio
            weapon_x = self.width - weapon_width - 20  # 20 pixels from right edge (moved closer)
            weapon_y = -50  # Lower position on screen (50 pixels below bottom edge)
            
            # Apply rotation to tilt the weapon to the right + swing animation
            glPushMatrix()
            glTranslatef(weapon_x + weapon_width/2, weapon_y + weapon_height/2, 0)  # Move to center
            glRotatef(15 + swing_rotation, 0, 0, 1)  # Base rotation + swing rotation
            glTranslatef(-(weapon_x + weapon_width/2), -(weapon_y + weapon_height/2), 0)  # Move back
            
            # Render weapon quad (flip vertically to fix orientation)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 1); glVertex2f(weapon_x, weapon_y)  # Flip texture coordinates
            glTexCoord2f(1, 1); glVertex2f(weapon_x + weapon_width, weapon_y)
            glTexCoord2f(1, 0); glVertex2f(weapon_x + weapon_width, weapon_y + weapon_height)
            glTexCoord2f(0, 0); glVertex2f(weapon_x, weapon_y + weapon_height)
            glEnd()
            
            glPopMatrix()  # Restore matrix
            
            # Unbind weapon texture
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
    
    def render(self):
        """Render the scene"""
        glClear(int(GL_COLOR_BUFFER_BIT) | int(GL_DEPTH_BUFFER_BIT))
        glLoadIdentity()
        
        # Apply camera rotation and position
        # glRotatef(-self.camera_rot[0] * 180 / math.pi, 1, 0, 0)  # Disabled pitch rotation (up/down)
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
        
        # Render hotbar
        self.render_hotbar()
        
        # Render interact prompt if near a chest
        if self.nearby_chest is not None:
            self.renderer.render_interact_prompt(self.width, self.height)
        
        # Render equipped weapon
        self.render_equipped_weapon()
        
        # Render health bar
        self.render_health_bar()
        
        # Render skeletons
        self.renderer.render_skeletons(self.skeletons, self.camera_pos)
        
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
        for skel in self.skeletons:
            if skel.is_alive:
                if skel.flash_timer > 0:
                    skel.flash_timer -= 1
                # Skeleton only moves if player is within activation radius and not frozen
                dx = self.camera_pos[0] - skel.center_x
                dz = self.camera_pos[2] - skel.center_z
                dist = math.sqrt(dx*dx + dz*dz)
                activation_radius = 7.0
                min_distance = 1.7  # Minimum distance to keep from player
                attacked = False
                # Skeleton attack logic
                if skel.attack_cooldown > 0:
                    skel.attack_cooldown -= 1
                else:
                    if dist < 2.0:  # Attack range
                        # Remove player knockback: only deal damage and apply cooldown/freeze
                        self.current_health = max(0, self.current_health - 5)
                        skel.attack_cooldown = 40  # ~0.66s at 60 FPS
                        skel.frozen_timer = 10  # Freeze movement for 10 frames after attack
                        attacked = True
                # Decrement frozen_timer if active
                if skel.frozen_timer > 0:
                    skel.frozen_timer -= 1
                # Only move if not attacking this frame, not frozen, and not too close
                if not attacked and skel.frozen_timer == 0 and dist < activation_radius and dist > min_distance:
                    skel.move_toward_player(self.camera_pos, self.check_collision, speed=0.05)
                alive.append(skel)
            elif skel.death_timer > 0:
                skel.death_timer -= 1
                alive.append(skel)
        self.skeletons = alive

    def try_attack_skeletons(self):
        # Only attack if sword is equipped and not already swinging
        if self.inventory[self.selected_slot] != "rusty_sword":
            return
        # Attack range and angle
        attack_range = 1.8  # About 2 tiles
        attack_angle = math.radians(60)  # 60 degree cone
        # Player forward vector
        yaw = self.camera_rot[1]
        forward = np.array([-math.sin(yaw), -math.cos(yaw)])
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
                skel.take_damage(5, knockback_vec=knockback, collision_checker=self.check_collision)

if __name__ == "__main__":
    game = DungeonCrawler()
    game.run()
