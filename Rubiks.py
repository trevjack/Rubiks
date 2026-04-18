from ursina import *
import random
from ursina import Button, color

app = Ursina()
pivot = None
leftButtonIsDown = False
totalAngle = [0,0,0]  # Tracks angle around x-, y-, or z-axis resp.
speed = 200 # Degrees per unit dragged by mouse
dragDir = None

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
def setPivot(axis,layer,dir):
    global pivot
    pivot = Entity()
    pivot.axis=axis
    pivot.dir=dir
    pivot.rotation = (0,0,0)
    for c in cubies:
        c.world_parent = scene
        if abs(getattr(c, axis) - layer) < 0.1:
            c.world_parent = pivot

def rotatePivot(angle):
    global pivot, totalAngle
    # Animate the rotation
    change = angle*pivot.dir
    if pivot.axis == 'x': 
        pivot.rotation += (change,0,0)
        totalAngle[0] += change
    elif pivot.axis == 'y': 
        pivot.rotation += (0,change,0)
        totalAngle[1] += change
    elif pivot.axis == 'z': 
        pivot.rotation += (0,0,change)
        totalAngle[2] += change

def animatedRotatePivot(angle):
    if pivot.axis == 'x':
        pivot.animate_rotation_x(pivot.rotation_x+angle*pivot.dir,
                                 duration=0.15, curve=curve.linear)
    if pivot.axis == 'y': 
        pivot.animate_rotation_y(pivot.rotation_y+angle*pivot.dir,
                                 duration=0.15, curve=curve.linear)
    if pivot.axis == 'z': 
        pivot.animate_rotation_z(pivot.rotation_z+angle*pivot.dir,
                                 duration=0.15, curve=curve.linear)


def resetPivot():
    global pivot, totalAngle
    if totalAngle[0]:
        pivot.animate_rotation_x(round(totalAngle[0]/90)*90,
                                 duration=0.15, curve=curve.linear)
    if totalAngle[1]: 
        pivot.animate_rotation_y(round(totalAngle[1]/90)*90,
                                 duration=0.15, curve=curve.linear)
    if totalAngle[2]: 
        pivot.animate_rotation_z(round(totalAngle[2]/90)*90,
                                 duration=0.15, curve=curve.linear)
    totalAngle = [0,0,0]
    invoke(resetCubies, delay=0.16)

def resetCubies():
    global pivot
    for c in cubies:
        c.world_parent = scene
        c.position = (round(c.x), round(c.y), round(c.z))
        c.rotation = (round(c.rotation_x/90)*90, 
                      round(c.rotation_y/90)*90, 
                      round(c.rotation_z/90)*90)
    pivot = None

# 4. Mouse controls
DIR_MAP = {
    'z': [ # Hit Front/Back: Can move along X or Y
        (Vec3(1,0,0),  'y', -1), # Move Right -> Rotate Y-axis
        (Vec3(-1,0,0), 'y',  1), # Move Left  -> Rotate Y-axis
        (Vec3(0,1,0),  'x',  1), # Move Up    -> Rotate X-axis
        (Vec3(0,-1,0), 'x', -1)  # Move Down  -> Rotate X-axis
    ],
    'x': [ # Hit Sides: Can move along Y or Z
        (Vec3(0,1,0),  'z',  1), # Move Up    -> Rotate Z-axis
        (Vec3(0,-1,0), 'z', -1), # Move Down  -> Rotate Z-axis
        (Vec3(0,0,1),  'y', 1), # Move "Right"(Z+) -> Rotate Y-axis
        (Vec3(0,0,-1), 'y',  -1)  # Move "Left"(Z-)  -> Rotate Y-axis
    ],
    'y': [ # Hit Top/Bottom: Can move along X or Z
        (Vec3(1,0,0),  'z', -1), # Move Right -> Rotate Z-axis
        (Vec3(-1,0,0), 'z',  1), # Move Left  -> Rotate Z-axis
        (Vec3(0,0,1),  'x', -1), # Move Up(Z+) -> Rotate X-axis
        (Vec3(0,0,-1), 'x',  1)  # Move Down(Z-) -> Rotate X-axis
    ]
}

start_world_point = None
start_mouse_pos = None
current_targets = []

def input(key):
    global start_world_point, start_mouse_pos, dragDir
    global current_targets, leftButtonIsDown

    if key == 'left mouse down' and mouse.hovered_entity:
        leftButtonIsDown = True
        face = mouse.hovered_entity
        cubie = face.parent
        
        # 1. Identify which coordinate is non-zero (The Face ID)
        lp = face.world_position - cubie.world_position
        face_axis = 'x' if abs(lp.x) > 0.1 else ('y' if abs(lp.y) > 0.1 else 'z')
        
        # 2. Build the 4 targets around the cubie's world center
        current_targets = []
        start_world_point = mouse.world_point
        start_mouse_pos = mouse.position
        for offset, rot_axis, dir in DIR_MAP[face_axis]:
            # Store (Target World Pos, Rotation Axis, Layer Coordinate)
            current_targets.append((offset,rot_axis,
                                    getattr(cubie, rot_axis),
                                    dir*getattr(cubie, face_axis)))

    if key == 'left mouse up': 
        # Reset for next click
        leftButtonIsDown = False
        start_mouse_pos = None
        start_world_point = None
        dragDir = None
        current_targets = []
        resetPivot()

def update():
    global start_mouse_pos, dragDir, start_world_point
    if leftButtonIsDown:
        if not pivot and mouse.world_point:
            mouse_change = distance(start_world_point, mouse.world_point)
            if  mouse_change>.05 and distance(mouse.position,start_mouse_pos)>.05:
                winner = min(current_targets, key=lambda t: distance(t[0],start_world_point - mouse.world_point))
                setPivot(winner[1],round(winner[2]),winner[3])
                dragDir = mouse.position-start_mouse_pos
                dragDir = dragDir / distance((0,0,0),dragDir)
        elif dragDir:
            mouse_change = dragDir.dot(mouse.position-start_mouse_pos)
            if abs(mouse_change)>.01:
                rotatePivot(mouse_change*speed)
                start_mouse_pos = mouse.position


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
    setPivot(ax,lay,1)
    animatedRotatePivot(ang)
    
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