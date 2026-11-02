"""
Generate OncoSentinel high-resolution multi-size Windows .ico file.
"""
from PIL import Image, ImageDraw

def create_icon():
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []

    for size in sizes:
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        w, h = size
        
        # Outer rounded shield / circle with dark slate border
        pad = max(1, int(w * 0.04))
        # Sentinel deep blue-indigo background
        draw.rounded_rectangle([pad, pad, w - pad, h - pad], radius=int(w * 0.22), fill=(15, 23, 42, 255), outline=(14, 165, 233, 255), width=max(1, int(w * 0.05)))
        
        # Medical Plus / Cross in bright cyan / teal
        cw = int(w * 0.18)
        ch = int(h * 0.52)
        cx = w // 2
        cy = h // 2
        
        # Vertical bar
        draw.rounded_rectangle([cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2], radius=int(cw * 0.3), fill=(6, 182, 212, 255))
        # Horizontal bar
        draw.rounded_rectangle([cx - ch // 2, cy - cw // 2, cx + ch // 2, cy + cw // 2], radius=int(cw * 0.3), fill=(6, 182, 212, 255))
        
        # Center core dot (glowing radar / sentinel dot)
        rw = max(2, int(w * 0.09))
        draw.ellipse([cx - rw, cy - rw, cx + rw, cy + rw], fill=(255, 255, 255, 255))
        
        images.append(img)
        
    images[0].save("oncosentinel.ico", format="ICO", sizes=[(s[0], s[1]) for s in sizes], append_images=images[1:])
    print("oncosentinel.ico created successfully!")

if __name__ == "__main__":
    create_icon()
