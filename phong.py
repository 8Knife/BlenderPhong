import bpy
import os.path
import math
import sys

C = bpy.context
D = bpy.data
scene = D.scenes['Scene']

# cameras: a list of camera positions
# a camera position is defined by two parameters: (theta, phi),
# where we fix the "r" of (r, theta, phi) in spherical coordinate system.

# 5 orientations: front, right, back, left, top
# cameras = [
#     (60, 0), (60, 90), (60, 180), (60, 270),
#     (0, 0)
# ]

# 12 orientations around the object with 30-deg elevation
cameras = [(60, i) for i in range(0, 360, 30)]

render_setting = scene.render

# output image size = (W, H)
w = 500
h = 500
render_setting.resolution_x = w
render_setting.resolution_y = h


def main():
    argv = sys.argv
    argv = argv[argv.index('--') + 1:]

    if len(argv) != 2:
        print('phong.py args: <3d mesh path> <image dir>')
        exit(-1)

    model = argv[0]
    image_dir = argv[1]

    # blender has no native support for off files
    # install_off_addon()

    init_camera()
    fix_camera_to_origin()

    do_model(model, image_dir)


def install_off_addon():
    try:
        bpy.ops.wm.addon_install(
            overwrite=False,
            filepath=os.path.dirname(__file__) +
            '/blender-off-addon/import_off.py'
        )
        bpy.ops.wm.addon_enable(module='import_off')
    except Exception:
        print("""Import blender-off-addon failed.
              Did you pull the blender-off-addon submodule?
              $ git submodule update --recursive --remote
              """)
        exit(-1)


def init_camera():
    cam = D.objects['Camera']
    # 新版 Blender 的激活语法
    C.view_layer.objects.active = cam
    # 新版 Blender 的选中语法
    cam.select_set(True)

    # set the rendering mode to orthogonal and scale
    C.object.data.type = 'ORTHO'
    C.object.data.ortho_scale = 2.


def fix_camera_to_origin():
    origin_name = 'Origin'

    # create origin
    try:
        origin = D.objects[origin_name]
    except KeyError:
        bpy.ops.object.empty_add(type='SPHERE')
        D.objects['Empty'].name = origin_name
        origin = D.objects[origin_name]

    origin.location = (0, 0, 0)

    cam = D.objects['Camera']
    # 新版 Blender 的激活与选中语法
    C.view_layer.objects.active = cam
    cam.select_set(True)

    if 'Track To' not in cam.constraints:
        bpy.ops.object.constraint_add(type='TRACK_TO')

    cam.constraints['Track To'].target = origin
    cam.constraints['Track To'].track_axis = 'TRACK_NEGATIVE_Z'
    cam.constraints['Track To'].up_axis = 'UP_Y'


def do_model(path, image_dir):
    name = load_model(path)
    center_model(name)
    normalize_model(name)

    # 👇 新增这一行，在拍照前打好光、上好色 👇
    setup_lighting_and_material(name)

    image_subdir = image_dir
    for i, c in enumerate(cameras):
        move_camera(c)
        render()
        save(image_subdir, '%s_%03d' % (name, i))

    delete_model(name)


def load_off(filepath, obj_name):
    # 手写的高性能 OFF 文件解析器，专治各种不服
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # 清除空行和注释
    lines = [l.strip() for l in lines if l.strip() and not l.startswith('#')]

    # 修复 ModelNet40 的祖传 Bug：OFF 经常和数字粘在一起，比如 "OFF34 50 0"
    if lines[0].startswith('OFF') and len(lines[0]) > 3:
        parts = lines[0][3:].split()
        lines.insert(1, ' '.join(parts))

    counts = lines[1].split()
    num_verts = int(counts[0])
    num_faces = int(counts[1])

    verts = []
    for i in range(2, 2 + num_verts):
        verts.append(list(map(float, lines[i].split()[:3])))

    faces = []
    for i in range(2 + num_verts, 2 + num_verts + num_faces):
        # OFF 格式的面：第一个数字是顶点数，后面是顶点的索引
        faces.append(list(map(int, lines[i].split()[1:])))

    # 在现代版 Blender 中直接生成 3D 模型
    mesh = D.meshes.new(obj_name)
    obj = D.objects.new(obj_name, mesh)

    # 链接到当前场景 (Blender 2.8+ 之后的新语法)
    C.scene.collection.objects.link(obj)

    mesh.from_pydata(verts, [], faces)
    mesh.update()


def load_model(path):
    ext = path.split('.')[-1].lower()
    name = os.path.basename(path).split('.')[0]

    if name not in D.objects:
        print('loading :' + name)
        if ext == 'off':
            load_off(path, name)
        else:
            print('当前快捷修复版本仅支持 .off 格式，跳过该文件')
            exit(-1)
    return name


def delete_model(name):
    for ob in scene.objects:
        if ob.type == 'MESH' and ob.name.startswith(name):
            ob.select_set(True)  # 新版选中语法
        else:
            ob.select_set(False) # 新版取消选中语法
    bpy.ops.object.delete()


def center_model(name):
    C.view_layer.update()  # 关键：强制刷新场景，计算真实的包围盒
    bpy.ops.object.select_all(action='DESELECT')
    obj = D.objects[name]
    C.view_layer.objects.active = obj
    obj.select_set(True)

    # 将原点设置到几何中心，并移到世界坐标的最中心
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    obj.location = (0, 0, 0)
    C.view_layer.update()


def normalize_model(name):
    C.view_layer.update()
    obj = D.objects[name]
    dim = obj.dimensions

    max_dim = max(dim[0], dim[1], dim[2])
    if max_dim > 0:
        # 强制缩放模型，使其最大边为 1.5（完美适配当前的摄像机视野）
        scale_factor = 1.5 / max_dim
        obj.scale = (scale_factor, scale_factor, scale_factor)

    # 应用缩放，把这个尺寸永久固定下来
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    C.view_layer.update()


def setup_lighting_and_material(obj_name):
    # 1. 设置纯白背景
    C.scene.render.film_transparent = False
    if C.scene.world is None:
        C.scene.world = bpy.data.worlds.new("World")
    C.scene.world.use_nodes = True
    bg_node = C.scene.world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)  # 纯白色

    # 2. 给模型加上深色材质（深灰偏蓝），带一点反光，对比度拉满
    mat = bpy.data.materials.new(name="PhongMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.2, 0.2, 0.25, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.4  # 稍微光滑一点，产生质感高光

    obj = D.objects[obj_name]
    if len(obj.data.materials) == 0:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat

    # 3. 确保场景里有一盏强力的太阳光
    if not any(o.type == 'LIGHT' for o in C.scene.objects):
        light_data = bpy.data.lights.new(name="SunLight", type='SUN')
        light_data.energy = 3.0  # 光照强度
        light_obj = bpy.data.objects.new(name="SunLight", object_data=light_data)
        C.scene.collection.objects.link(light_obj)
        light_obj.rotation_euler = (0.785, 0.785, 0.785)  # 从斜上方打光，凸显立体感


def move_camera(coord):
    def deg2rad(deg):
        return deg * math.pi / 180.

    r = 3.
    theta, phi = deg2rad(coord[0]), deg2rad(coord[1])
    loc_x = r * math.sin(theta) * math.cos(phi)
    loc_y = r * math.sin(theta) * math.sin(phi)
    loc_z = r * math.cos(theta)

    D.objects['Camera'].location = (loc_x, loc_y, loc_z)


def render():
    bpy.ops.render.render()


def save(image_dir, name):
    path = os.path.join(image_dir, name + '.png')
    D.images['Render Result'].save_render(filepath=path)
    print('save to ' + path)


if __name__ == '__main__':
    main()
