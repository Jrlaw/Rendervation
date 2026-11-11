"""Paint and tile colors measured from products, added to roomkit's tables so any room can use
them by name (--tile-color <name>). Colors are linear RGB; tile colors are (darker, lighter),
and tiles vary between the two. Finishes: (roughness, strong tile-to-tile variation, wavy glaze).
"""
from roomkit.materials import TILE_COLORS, TILE_FINISHES

TILE_COLORS.update({
    # Bedrosians Cloe 2.5x8 glossy, and the before photo's 4-1/4" wall tile, measured from the photos
    "cloegreen": ((0.026, 0.048, 0.031), (0.040, 0.070, 0.046)),   # deep forest green ~#32443A
    "cloebabyblue": ((0.53, 0.63, 0.64), (0.61, 0.71, 0.72)),      # pale aqua blue ~#C7D6D7
    "cloepink": ((0.73, 0.50, 0.48), (0.82, 0.59, 0.57)),          # soft blush ~#E4C3C0
    "cloewhite": ((0.79, 0.79, 0.76), (0.86, 0.86, 0.83)),         # gloss white ~#F0EFEA
    "retrogreen": ((0.070, 0.190, 0.037), (0.085, 0.230, 0.045)),  # ~#4F7F39
})
TILE_FINISHES.update({
    "cloegreen": (0.05, True, True),     # glossy, handmade look with a wavy face
    "cloebabyblue": (0.05, True, True),
    "cloepink": (0.05, True, True),
    "cloewhite": (0.05, True, True),
    "retrogreen": (0.12, False, False),  # old glazed wall tile, even color
})
