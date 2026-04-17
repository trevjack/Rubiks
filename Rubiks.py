from ursina import *
import random
from ursina import Button, color

app = Ursina()

# 1. THE CUBIE CLASS
class Cubie(Entity):
    def __init__(self, x, y, z):
        super().__init__(position=(x, y, z))
        
        # Define the 6 possible faces
        # (Color, Local Position, Local Rotation)
        faces = [
            (color.white,  (0, .5, 0),  (90, 0, 0)),  # Top (y=1)
            (color.yellow, (0, -.5, 0), (-90, 0, 0)),  # Bottom (y=-1)
            (color.red,    (.5, 0, 0),  (0, -90, 0)),  # Right (x=1)
            (color.orange, (-.5, 0, 0), (0, 90, 0)),  # Left (x=-1)
            (color.blue,   (0, 0, -.5), (0, 0, 0)),   # Front (z=-1)
            (color.green,  (0, 0, .5),  (180, 0, 0))    # Back (z=1)
        ]

        # Only add a face if the cubie is on the edge of that axis
        if y == 1:  self.make_face(faces[0]) # Add Top
        if y == -1: self.make_face(faces[1]) # Add Bottom
        if x == 1:  self.make_face(faces[2]) # Add Right
        if x == -1: self.make_face(faces[3]) # Add Left
        if z == -1: self.make_face(faces[4]) # Add Front
        if z == 1:  self.make_face(faces[5]) # Add Back

    def make_face(self, data):
        Entity(
            parent=self,
            model='quad',
            color=data[0],
            position=data[1],
            rotation=data[2],
            scale=.99,
            collider='box'
        )

# 2. SETUP THE CUBE
cubies = []
for x in range(-1, 2):
    for y in range(-1, 2):
        for z in range(-1, 2):
            if x == 0 and y == 0 and z == 0: continue
            cubies.append(Cubie(x, y, z))

# 3. THE ROTATION ENGINE
pivot = Entity()

def rotate_slice(axis, layer, angle):
    pivot.rotation = (0,0,0)
    for c in cubies:
        c.world_parent = scene
        # Logic: Is this cubie in the slice we want to move?
        if abs(getattr(c, axis) - layer) < 0.1:
            c.world_parent = pivot

    # Animate the rotation
    if axis == 'x': 
        pivot.animate_rotation_x(angle, duration=0.15, curve=curve.linear)
    elif axis == 'y': 
        pivot.animate_rotation_y(angle, duration=0.15, curve=curve.linear)
    elif axis == 'z': 
        pivot.animate_rotation_z(angle, duration=0.15, curve=curve.linear)
    
    # CRITICAL: Snap to perfect integers after rotation
    invoke(snap_to_grid, delay=0.25)

def snap_to_grid():
    for c in cubies:
        c.world_parent = scene
        # Round the positions and rotations to keep the math "clean"
        c.position = (round(c.x), round(c.y), round(c.z))
        c.rotation = (round(c.rotation_x/90)*90, 
                      round(c.rotation_y/90)*90, 
                      round(c.rotation_z/90)*90)


# 4. Mouse controls
DIR_MAP = {
    'z': [ # Hit Front/Back: Can move along X or Y
        (Vec3(1,0,0),  'y', 'y',  90), # Move Right -> Rotate Y-axis
        (Vec3(-1,0,0), 'y', 'y', -90), # Move Left  -> Rotate Y-axis
        (Vec3(0,1,0),  'x', 'x', -90), # Move Up    -> Rotate X-axis
        (Vec3(0,-1,0), 'x', 'x',  90)  # Move Down  -> Rotate X-axis
    ],
    'x': [ # Hit Sides: Can move along Y or Z
        (Vec3(0,1,0),  'z', 'z', -90), # Move Up    -> Rotate Z-axis
        (Vec3(0,-1,0), 'z', 'z',  90), # Move Down  -> Rotate Z-axis
        (Vec3(0,0,1),  'y', 'y', -90), # Move "Right"(Z+) -> Rotate Y-axis
        (Vec3(0,0,-1), 'y', 'y',  90)  # Move "Left"(Z-)  -> Rotate Y-axis
    ],
    'y': [ # Hit Top/Bottom: Can move along X or Z
        (Vec3(1,0,0),  'z', 'z',  90), # Move Right -> Rotate Z-axis
        (Vec3(-1,0,0), 'z', 'z', -90), # Move Left  -> Rotate Z-axis
        (Vec3(0,0,1),  'x', 'x',  90), # Move Up(Z+) -> Rotate X-axis
        (Vec3(0,0,-1), 'x', 'x', -90)  # Move Down(Z-) -> Rotate X-axis
    ]
}

start_mouse_pos = None
current_targets = []

def input(key):
    global start_mouse_pos, current_targets

    if key == 'left mouse down' and mouse.hovered_entity:
        sticker = mouse.hovered_entity
        cubie = sticker.parent
        
        # 1. Identify which coordinate is non-zero (The Face ID)
        lp = sticker.world_position - cubie.world_position
        face_axis = 'x' if abs(lp.x) > 0.1 else ('y' if abs(lp.y) > 0.1 else 'z')
        
        # 2. Build the 4 targets around the cubie's world center
        anchor = cubie.world_position
        start_mouse_pos = mouse.world_point
        current_targets = []
        for offset, rot_axis, layer_attr, angle in DIR_MAP[face_axis]:
            target_pos = anchor + offset
            angle = angle if getattr(cubie, face_axis) > 0 else -angle
            # Store (Target World Pos, Rotation Axis, Layer Coordinate, Angle)
            current_targets.append((target_pos, rot_axis, getattr(cubie, layer_attr), angle))

    if key == 'left mouse up' and start_mouse_pos and mouse.world_point:
        # 3. Check if the user actually dragged a minimum distance
        if distance(start_mouse_pos, mouse.world_point) > 0.1:
            
            # 4. Find the closest target point to where the mouse is now
            # winner looks like: (pos, axis, layer, angle)
            winner = min(current_targets, key=lambda t: distance(t[0], mouse.world_point))
            # 5. Execute the rotation
            rotate_slice(winner[1], round(winner[2]), winner[3])
            
        # Reset for next click
        start_mouse_pos = None
        current_targets = []

# Shuffling the cube with a random sequence of moves
sequence = []

def shuffle_cube(steps=20):
    global sequence
    # Generate 20 random move instructions
    axes = ['x', 'y', 'z']
    layers = [-1, 0, 1]
    angles = [90, -90]
    
    sequence = [(random.choice(axes), random.choice(layers), random.choice(angles)) 
                for i in range(steps)]
    
    run_next_move()

def run_next_move():
    if not sequence:
        return # We are done!

    # Pull the first move out of the list
    ax, lay, ang = sequence.pop(0)
    
    # Execute the move
    rotate_slice(ax, lay, ang)
    
    # WAIT for the animation duration (0.2s) + cleanup (0.05s)
    # then call this function again for the next move
    invoke(run_next_move, delay=0.3)

# Shuffle Button
shuffle_btn = Button(
    text='Shuffle',
    color=color.azure,
    scale=(0.15, 0.05),
    position=(0.7, 0.4), # Top right
    on_click=shuffle_cube
)

cam = EditorCamera() # Allows you to right-click and drag to rotate the camera

app.run()