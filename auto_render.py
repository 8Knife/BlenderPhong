import os
import subprocess

# ================= 配置区域 =================
# 1. 你的 3D 模型总目录 (里面包含 airplane 等各个类型的文件夹)
MODEL_DIR = r"D:\PROGRAMS\mvCnn\mvcnn_pytorch\modelnet40_images_new_12x"

# 2. 生成的 2D 图片想要保存的总目录
OUTPUT_DIR = r"D:\PROGRAMS\mvCnn\mvcnn_pytorch\modelnet40_images"

# 3. 你电脑上 Blender 的完整路径
BLENDER_PATH = r"D:\AppDatas\Blender\blender.exe"
# ============================================

# 自动遍历所有的文件夹和子文件夹
for root, dirs, files in os.walk(MODEL_DIR):
    for file in files:
        # 只处理 3D 模型文件
        if file.endswith(('.off', '.obj', '.stl')):
            model_path = os.path.join(root, file)

            # 计算相对路径，完美克隆 "类型/训练" 这样的目录结构
            rel_path = os.path.relpath(root, MODEL_DIR)
            out_dir = os.path.join(OUTPUT_DIR, rel_path)

            # 如果输出目录不存在，自动创建它
            os.makedirs(out_dir, exist_ok=True)

            # 👇 新增的断点续传逻辑 👇
            # 获取模型名字（不带后缀）
            model_name = os.path.splitext(file)[0]
            # 检查最后一张图（第12张，后缀是 _011.png）是不是已经生成了
            last_image_path = os.path.join(out_dir, f"{model_name}_011.png")

            if os.path.exists(last_image_path):
                print(f"已跳过 (上次已跑完): {model_name}")
                continue  # 直接跳过当前模型，进入下一个循环
            # 👆 新增的断点续传逻辑 👆

            print(f"----------------------------------------")
            print(f"正在渲染模型: {model_path}")

            # 拼装并执行 Blender 后台渲染命令
            cmd = f'"{BLENDER_PATH}" phong.blend --background --python phong.py -- "{model_path}" "{out_dir}"'
            subprocess.run(cmd, shell=True)

print("🎉 所有模型全部渲染完成，目录结构已完美保留！")