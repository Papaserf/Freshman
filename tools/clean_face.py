"""Clean a ChatGPT face drawing for FRESHMAN's head texture.

The face kit layout is 2:1 (any size): face centered at x~25%, eye line at y~45%.
Drawings often come with a lighter panel, dark edges and a halftone strip; wrapped
around a head those read as a stripe. This keeps only the face (soft oval mask),
fills everything else with the face's own skin tone, and prints that tone so the
character's body skin can be set to match (CFG[key].skin in index.html).

usage: python3 clean_face.py input.png output.jpg
"""
import sys, statistics
from PIL import Image, ImageDraw, ImageFilter
W, H = 1774, 887
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB').resize((W, H))
mask = Image.new('L', (W, H), 0); ImageDraw.Draw(mask).ellipse((235, 225, 665, 720), fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(30))
core = Image.new('L', (W, H), 0); ImageDraw.Draw(core).ellipse((280, 270, 620, 670), fill=255)
px = [im.getpixel((x, y)) for x in range(282, 620, 5) for y in range(272, 670, 5) if core.getpixel((x, y))]
px.sort(key=sum); mid = px[int(len(px) * .35):int(len(px) * .8)]
c = tuple(int(statistics.median(p[i] for p in mid)) for i in range(3))
bg = Image.new('RGB', (W, H), c); bg.paste(im, (0, 0), mask)
bg.resize((1024, 512), Image.LANCZOS).save(dst, quality=86)
print('skin: 0x%02x%02x%02x' % c)
