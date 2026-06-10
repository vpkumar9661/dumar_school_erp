import os
from PIL import Image

def make_white_transparent_aggressive(img_path, output_path):
    print(f"Opening original image: {img_path}")
    img = Image.open(img_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    for item in datas:
        r, g, b, a = item
        # If the pixel is distinctly red (part of the stencil artwork)
        # Swami Vivekananda's stencil is red, so G and B channels are very low.
        if r > 100 and g < 110 and b < 110:
            # Keep the red pixel as is
            new_data.append(item)
        else:
            # Make any other pixel (white, gray, border antialiasing) completely transparent
            new_data.append((255, 255, 255, 0))
            
    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Saved aggressively transparent image to: {output_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original_logo_path = os.path.join(base_dir, "static", "images", "school_logo_original.png")
    target_logo_path = os.path.join(base_dir, "static", "images", "school_logo.png")
    
    if os.path.exists(original_logo_path):
        make_white_transparent_aggressive(original_logo_path, target_logo_path)
    else:
        print(f"Error: Original logo file not found at {original_logo_path}")
