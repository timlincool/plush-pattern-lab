"""Render a saved Blender scene to a new PNG without saving modifications to it."""

import argparse
import sys
from pathlib import Path

import bpy


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--resolution", type=int, default=512)
    p.add_argument("--samples", type=int, default=12)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if (
        not a.input.is_file()
        or a.output.exists()
        or not 256 <= a.resolution <= 1000
        or not 8 <= a.samples <= 128
    ):
        raise RuntimeError("Invalid source, existing output, or render parameters")
    bpy.ops.wm.open_mainfile(filepath=str(a.input.resolve()), load_ui=False)
    s = bpy.context.scene
    if s.camera is None or s.camera.name != "Camera":
        raise RuntimeError("Camera missing")
    s.render.engine = "CYCLES"
    s.cycles.samples = a.samples
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = a.resolution
    s.render.resolution_percentage = 100
    s.render.use_border = s.render.use_crop_to_border = False
    s.render.image_settings.file_format = "PNG"
    a.output.parent.mkdir(parents=True, exist_ok=True)
    s.render.filepath = str(a.output.resolve())
    bpy.ops.render.render(write_still=True)
    if not a.output.is_file() or a.output.stat().st_size < 10000:
        raise RuntimeError("PNG not created")
    print("RENDER_SAVED", a.output, flush=True)


if __name__ == "__main__":
    main()
