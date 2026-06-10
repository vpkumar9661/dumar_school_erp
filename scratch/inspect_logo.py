from PIL import Image

img = Image.open("school_erp_v2/static/images/school_logo_original.png").convert("RGBA")
datas = img.getdata()

white_count = 0
red_count = 0
other_count = 0

for item in datas:
    r, g, b, a = item
    if r > 240 and g > 240 and b > 240:
        white_count += 1
    elif r > 100 and g < 50 and b < 50:
        red_count += 1
    else:
        other_count += 1

print(f"Total pixels: {len(datas)}")
print(f"White pixels (>240): {white_count}")
print(f"Red pixels: {red_count}")
print(f"Other pixels: {other_count}")
