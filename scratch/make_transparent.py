import os
from PIL import Image

def make_white_transparent(img_path, output_path):
    print(f"Opening image: {img_path}")
    img = Image.open(img_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    for item in datas:
        # Check if the pixel is white or very close to white
        # item is (r, g, b, a)
        r, g, b, a = item
        if r > 240 and g > 240 and b > 240:
            # Set alpha to 0 (fully transparent)
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Saved transparent image to: {output_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, "static", "images", "school_logo.png")
    
    if os.path.exists(logo_path):
        # Backup the original logo first
        backup_path = os.path.join(base_dir, "static", "images", "school_logo_original.png")
        if not os.path.exists(backup_path):
            import shutil
            shutil.copyfile(logo_path, backup_path)
            print(f"Created backup of original logo at: {backup_path}")
            
        make_white_transparent(logo_path, logo_path)
    else:
        print(f"Error: Logo file not found at {logo_path}")
