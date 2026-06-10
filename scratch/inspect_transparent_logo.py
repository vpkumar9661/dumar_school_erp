from PIL import Image

img = Image.open("school_erp_v2/static/images/school_logo.png").convert("RGBA")
datas = img.getdata()

non_transparent_white = 0
transparent_count = 0

for item in datas:
    r, g, b, a = item
    if a == 0:
        transparent_count += 1
    elif r > 200 and g > 200 and b > 200:
        non_transparent_white += 1

print(f"Total pixels: {len(datas)}")
print(f"Transparent pixels: {transparent_count}")
print(f"Non-transparent near-white pixels (>200): {non_transparent_white}")
