"""Generate a support-free 60 mm branch-handled miniature scoop STL."""

from pathlib import Path

import manifold3d
import numpy as np
import trimesh
from shapely.geometry import LineString, Polygon


OUT = Path(__file__).with_name("Branch_Scoop_60mm.stl")


def extrude(shape, height, z=0.0):
    mesh = trimesh.creation.extrude_polygon(shape, height=height, engine="earcut")
    mesh.apply_translation((0, 0, z))
    return mesh


def capsule_path(points, radius, height, z=0.0):
    outline = LineString(points).buffer(radius, cap_style="round", join_style="round", resolution=32)
    return extrude(outline, height, z)


def horizontal_cylinder(length, radius, center):
    mesh = trimesh.creation.cylinder(radius=radius, height=length, sections=64)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0)))
    mesh.apply_translation(center)
    return mesh


def main():
    # Scoop silhouette: 26 mm long, 16 mm maximum width.
    scoop_outline = Polygon(
        [
            (-6.8, 0.0), (-7.6, 0.5), (-8.0, 2.0), (-8.0, 12.0),
            (-7.5, 16.0), (-6.0, 20.0), (-4.2, 24.0), (-3.4, 26.0),
            (3.4, 26.0), (4.2, 24.0), (6.0, 20.0), (7.5, 16.0),
            (8.0, 12.0), (8.0, 2.0), (7.6, 0.5), (6.8, 0.0),
        ]
    )
    scoop = extrude(scoop_outline, 6.0)

    # Open bowl, leaving a 2 mm printable floor and roughly 2 mm rim.
    cavity_outline = Polygon(
        [
            (-5.0, 2.0), (-5.8, 3.0), (-5.8, 12.0), (-5.2, 15.5),
            (-3.8, 19.0), (-2.6, 22.0), (2.6, 22.0), (3.8, 19.0),
            (5.2, 15.5), (5.8, 12.0), (5.8, 3.0), (5.0, 2.0),
        ]
    )
    cavity = extrude(cavity_outline, 5.0, 2.0)

    # Flat-backed curved twig handle. Endpoint + radius gives exactly 60 mm.
    handle_points = [
        (0.0, 23.0), (0.4, 30.0), (-0.6, 38.0),
        (0.2, 46.0), (0.9, 53.0), (0.3, 56.7),
    ]
    handle = capsule_path(handle_points, 3.3, 6.0)

    # Two branch nubs based on the reference image, thick enough for a 0.4 mm nozzle.
    branch_a = capsule_path([(-0.3, 44.0), (-4.7, 49.0)], 1.55, 5.5, 0.2)
    branch_b = capsule_path([(0.0, 35.0), (4.2, 39.0)], 1.45, 5.3, 0.2)

    # Three raised wrap bands reinforce and visually join scoop to handle.
    bands = [
        horizontal_cylinder(8.5, 0.58, (0.0, y, 5.8))
        for y in (25.0, 26.4, 27.8)
    ]

    # Subtle printable knots; no fragile bark texture at this scale.
    knots = []
    for x, y, radius in ((-0.8, 33.0, 1.0), (0.9, 42.0, 0.9), (-0.5, 52.0, 0.85)):
        knot = trimesh.creation.cylinder(radius=radius, height=0.7, sections=48)
        knot.apply_translation((x, y, 6.0))
        knots.append(knot)

    body = trimesh.boolean.union(
        [scoop, handle, branch_a, branch_b, *bands, *knots], engine="manifold"
    )
    body = trimesh.boolean.difference([body, cavity], engine="manifold")

    # Rebuild/simplify boolean seams while retaining the exact 60 mm length.
    source = manifold3d.Mesh(
        np.asarray(body.vertices, dtype=np.float32),
        np.asarray(body.faces, dtype=np.uint32),
    )
    rebuilt = manifold3d.Manifold(source).simplify(1e-5).to_mesh()
    body = trimesh.Trimesh(
        vertices=np.asarray(rebuilt.vert_properties)[:, :3],
        faces=np.asarray(rebuilt.tri_verts),
        process=True,
    )
    body.export(OUT)
    print(f"Wrote {OUT.name}")
    print(f"vertices={len(body.vertices)} faces={len(body.faces)}")
    print(f"watertight={body.is_watertight} volume_mm3={body.volume:.1f}")
    print(f"bounds_mm={np.round(body.bounds, 2).tolist()}")


if __name__ == "__main__":
    main()
