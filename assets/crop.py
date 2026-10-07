from PIL import Image, ImageEnhance
import glob

# Approximate bounding box for the Instagram modal image on a 2940x1912 screen
box = (350, 150, 1550, 1650) # x1, y1, x2, y2

for file in glob.glob('*.jpg'):
    img = Image.open(file)
    if img.size[0] > 2000:
        cropped = img.crop(box)
        # Amélioration
        enhancer = ImageEnhance.Contrast(cropped)
        cropped = enhancer.enhance(1.15)
        enhancer = ImageEnhance.Color(cropped)
        cropped = enhancer.enhance(1.1)
        
        cropped.save(file, quality=95)
        print(f"Cropped and enhanced {file}")
