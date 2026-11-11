"""Landmarks for solving the photo cameras (python3 lib/tools/solve_cameras.py <this file>).
Model points are in plan inches from layout.py's guesses; pixels are in web/before/photoN.jpg
(1600 x 1200, the park's 3:2 photos cut to 4:3). LENS: 15 mm on a full-frame Canon, 18 mm and
16.9 mm once each photo is cut to 4:3 (photo 1 was already cropped a little)."""
LENS = 18.0
SHOTS = dict(
    photo1=dict(start=(40, -150, 60), aim=(52, -40, 40), portrait=False, lens=18.0, marks=[
        ((74.5, -109, 36), (1190, 682)),     # counter nose, south end of the sink run, front corner
        ((100, -109, 36), (1468, 668)),      # the same edge at the wall
        ((100, -109, 0), (1400, 945)),       # end panel, bottom at the wall
        ((75.5, -109, 0), (1183, 950)),      # end panel, bottom front
        ((34, 0, 80), (757, 290)),           # hall opening, head, west side
        ((64, 0, 80), (905, 285)),           # hall opening, head, east side
        ((64, 0, 0), (897, 645)),            # hall opening, floor, east side
        ((27, -61, 36), (640, 645)),         # range top, front north corner
        ((27, -91, 36), (548, 738)),         # range top, front south corner
        ((1, -91, 36), (228, 740)),          # range top, back south corner
        ((26, -91, 0), (575, 1075)),         # range side, front bottom
        ((1, -91, 0), (290, 1082)),          # range side, back bottom
    ]),
    photo2=dict(start=(45, 2, 62), aim=(70, -120, 30), portrait=False, lens=16.87, marks=[
        ((74.5, -109, 36), (1058, 552)),     # counter nose, south end of the sink run
        ((75.5, -109, 4), (1048, 712)),      # base front at the end, top of the kick
        ((75.25, -15, 34.5), (515, 770)),    # dishwasher top, north
        ((75.25, -39, 34.5), (752, 672)),    # dishwasher top, south
        ((75.25, -39, 4), (762, 935)),       # dishwasher bottom, south
        ((100, -38, 43), (600, 515)),        # sink window opening, sill, north
        ((100, -68, 43), (765, 492)),        # sink window opening, sill, south
        ((100, -168, 0), (1100, 572)),       # SE corner at the floor
        ((100, -168, 96), (1128, 215)),      # SE corner at the ceiling
    ]),
)
