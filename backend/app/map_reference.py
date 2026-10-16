"""Offline Baidu observations; projected POI anchors guide the illustrative layout."""
import json
import math
from pathlib import Path

WALKING_ROUTES=json.loads((Path(__file__).resolve().parents[2]/'data/verified-walking-routes.json').read_text(encoding='utf-8'))
# Coordinates transcribed from the public route share URLs, in Baidu's projected system.
# These are POI positions, not surveyed footprints or accessible entrance coordinates.
POIS={
    'LIB':((420,517),(13494586.9897,3617226.25399)),
    'INFO':((420,400),(13494649.120572,3617335.470297)),
    'GYM':((715,251),(13495079.732924,3617490.846128)),
    'LQ':((270,295),(13494693.487357,3617650.799909)),
    'XUESI':((633,399),(13494789.148678,3617215.965484)),
}

def raw_position(px,py):
    dx=px-540; dy=py-360
    return ((dx/2+dy)*.84,(-dx/2+dy)*.84)

def reference_position(px,py):
    x,z=raw_position(px,py); origin=POIS['LIB'][1]; base=raw_position(*POIS['LIB'][0])
    offsets=[]
    for pixel,projected in POIS.values():
        old=raw_position(*pixel); east=projected[0]-origin[0]; north=projected[1]-origin[1]
        target=(base[0]+(east-north)*.8/math.sqrt(2),base[1]-(east+north)*.8/math.sqrt(2))
        radius=math.hypot(x-old[0],z-old[1])
        if radius<.01: return dict(x=round(target[0],1),z=round(target[1],1),imageX=px,imageY=py)
        offsets.append((1/radius**4,target[0]-old[0],target[1]-old[1]))
    weight=sum(r[0] for r in offsets)
    return dict(x=round(x+sum(w*dx for w,dx,dz in offsets)/weight,1),z=round(z+sum(w*dz for w,dx,dz in offsets)/weight,1),imageX=px,imageY=py)
