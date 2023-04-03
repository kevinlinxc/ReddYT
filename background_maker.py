# this shit does not work, waiting on https://stackoverflow.com/questions/75915710/tiling-svg-into-an-image-and-saving-it-in-python
from geopatterns import GeoPattern
from PIL import Image
import base64
from io import BytesIO
import cairosvg

# Generate the pattern as an SVG string
pattern = GeoPattern('A string for your consideration.', generator='xes')
cairosvg.svg2png(bytestring=pattern.svg_string, write_to="output.png")


image = Image.open('output.png')

# Get the size of the area to tile
width, height = 1920, 1080

# Calculate the number of times to repeat the image horizontally and vertically
repeat_x = width // image.width + 1
repeat_y = height // image.height + 1

# Create a new image that fits the specified size
new_width = repeat_x * image.width
new_height = repeat_y * image.height
new_image = Image.new('RGBA', (new_width, new_height))

# Paste the image repeatedly to tile it
for x in range(repeat_x):
    for y in range(repeat_y):
        new_image.paste(image, (x * image.width, y * image.height))

# Resize the tiled image to fit the area exactly
new_image = new_image.resize((width, height))

# Save the tiled image
new_image.save('output.png')