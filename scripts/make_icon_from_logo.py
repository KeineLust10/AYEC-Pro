from PIL import Image
import os

SRC = os.path.join('Setup_Files', 'assets', 'logo.png') if os.path.exists(os.path.join('Setup_Files','assets','logo.png')) else os.path.join('assets','logo.png')
DST = os.path.join('assets', 'app_icon.ico')

def ensure_assets_dir():
    if not os.path.exists('assets'):
        os.makedirs('assets', exist_ok=True)

def generate_icon(src, dst):
    try:
        img = Image.open(src).convert('RGBA')
    except Exception as e:
        print(f"Failed to open source image '{src}': {e}")
        return False

    sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
    # Ensure square by fitting onto transparent square canvas
    # Create temporary resized images
    icons = []
    for s in sizes:
        try:
            f = img.copy()
            f.thumbnail(s, Image.LANCZOS)
            # Paste onto transparent square
            canvas = Image.new('RGBA', s, (0,0,0,0))
            x = (s[0]-f.width)//2
            y = (s[1]-f.height)//2
            canvas.paste(f, (x,y), f)
            icons.append(canvas)
        except Exception as e:
            print(f"Failed to create size {s}: {e}")

    try:
        # Pillow will accept a list of sizes when saving ICO
        # Save highest resolution first
        icons[-1].save(dst, format='ICO', sizes=sizes)
        print(f"Generated ICO: {dst}")
        return True
    except Exception as e:
        print(f"Failed to save ICO '{dst}': {e}")
        return False

if __name__ == '__main__':
    ensure_assets_dir()
    ok = generate_icon(SRC, DST)
    if not ok:
        print('Icon generation failed.')