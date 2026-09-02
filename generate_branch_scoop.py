"""Generate a sculptural 60 mm branch-handled scoop from the concept image."""

from pathlib import Path

import manifold3d
import numpy as np
import trimesh
from shapely.geometry import Polygon


OUT = Path(__file__).with_name("Лопатка Model 1.stl")
SECTIONS = 48


def ellipsoid(axes, center, subdivisions=4):
    mesh = trimesh.creation.icosphere(subdivisions=subdivisions, radius=1.0)
    mesh.apply_scale(axes)
    mesh.apply_translation(center)
    return mesh


def sphere(radius, center, subdivisions=3):
    mesh = trimesh.creation.icosphere(subdivisions=subdivisions, radius=radius)
    mesh.apply_translation(center)
    return mesh


def frustum_between(p0, p1, r0, r1, sections=SECTIONS):
    """Closed tapered tube between arbitrary 3D points."""
    p0 = np.asarray(p0, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    axis = p1 - p0
    axis /= np.linalg.norm(axis)
    helper = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(axis, helper)) > 0.9:
        helper = np.array([1.0, 0.0, 0.0])
    u = np.cross(axis, helper)
    u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    angles = np.linspace(0, 2 * np.pi, sections, endpoint=False)
    ring0 = np.array([p0 + r0 * (np.cos(a) * u + np.sin(a) * v) for a in angles])
    ring1 = np.array([p1 + r1 * (np.cos(a) * u + np.sin(a) * v) for a in angles])
    vertices = np.vstack((ring0, ring1, p0, p1))
    faces = []
    for i in range(sections):
        j = (i + 1) % sections
        faces.extend(((i, j, sections + j), (i, sections + j, sections + i)))
        faces.extend(((2 * sections, j, i), (2 * sections + 1, sections + i, sections + j)))
    return trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=True)


def organic_branch(points, radii):
    parts = []
    for index in range(len(points) - 1):
        parts.append(
            frustum_between(points[index], points[index + 1], radii[index], radii[index + 1])
        )
    for point, radius in zip(points, radii):
        parts.append(sphere(radius, point))
    return trimesh.boolean.union(parts, engine="manifold")


def tube_path(points, radius, sections=28):
    parts = []
    for start, end in zip(points[:-1], points[1:]):
        parts.append(frustum_between(start, end, radius, radius, sections))
    for point in points:
        parts.append(sphere(radius, point, subdivisions=2))
    return trimesh.boolean.union(parts, engine="manifold")


def torus_y(major_radius, minor_radius, center, major_sections=80, minor_sections=16):
    """Torus with its axis along Y, used for the rope wrapping."""
    cx, cy, cz = center
    vertices = []
    for i in range(major_sections):
        u = 2 * np.pi * i / major_sections
        for j in range(minor_sections):
            v = 2 * np.pi * j / minor_sections
            radial = major_radius + minor_radius * np.cos(v)
            vertices.append(
                (cx + radial * np.cos(u), cy + minor_radius * np.sin(v), cz + radial * np.sin(u))
            )
    faces = []
    for i in range(major_sections):
        ni = (i + 1) % major_sections
        for j in range(minor_sections):
            nj = (j + 1) % minor_sections
            a = i * minor_sections + j
            b = ni * minor_sections + j
            c = ni * minor_sections + nj
            d = i * minor_sections + nj
            faces.extend(((a, b, c), (a, c, d)))
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=True)
    if mesh.volume < 0:
        mesh.invert()
    return mesh


def rounded_outline(points, target_width, target_length, y_min, count=128):
    """Round and evenly resample a custom front silhouette."""
    polygon = Polygon(points).buffer(0.7, join_style="round", resolution=20)
    ring = polygon.exterior
    sampled = np.array(
        [ring.interpolate(distance).coords[0] for distance in np.linspace(0, ring.length, count, endpoint=False)]
    )
    sampled[:, 0] -= (sampled[:, 0].min() + sampled[:, 0].max()) / 2
    sampled[:, 0] *= target_width / np.ptp(sampled[:, 0])
    sampled[:, 1] -= sampled[:, 1].min()
    sampled[:, 1] *= target_length / np.ptp(sampled[:, 1])
    sampled[:, 1] += y_min
    return sampled


def loft_solid(outline, layers):
    """Loft one 2D outline through Z layers of (z, scale)."""
    centre = np.array([0.0, (outline[:, 1].min() + outline[:, 1].max()) / 2])
    rings = []
    for z_value, scale in layers:
        xy = centre + (outline - centre) * scale
        rings.append(np.column_stack((xy, np.full(len(xy), z_value))))
    vertices = np.vstack((*rings, [centre[0], centre[1], layers[0][0]], [centre[0], centre[1], layers[-1][0]]))
    count = len(outline)
    faces = []
    for layer_index in range(len(layers) - 1):
        offset = layer_index * count
        next_offset = (layer_index + 1) * count
        for i in range(count):
            j = (i + 1) % count
            faces.extend(((offset + i, offset + j, next_offset + j), (offset + i, next_offset + j, next_offset + i)))
    bottom_centre = count * len(layers)
    top_centre = bottom_centre + 1
    top_offset = count * (len(layers) - 1)
    for i in range(count):
        j = (i + 1) % count
        faces.extend(((bottom_centre, j, i), (top_centre, top_offset + i, top_offset + j)))
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=True)
    if mesh.volume < 0:
        mesh.invert()
    return mesh


def handle_center(y):
    control = np.array(
        [
            [24.0, 0.0, 0.1], [30.0, 0.5, 0.8], [37.0, -0.6, 0.2],
            [44.0, 0.4, 0.9], [51.0, 0.0, 0.5], [56.7, 0.6, 0.8],
        ]
    )
    return (
        np.interp(y, control[:, 0], control[:, 1]),
        np.interp(y, control[:, 0], control[:, 2]),
    )


def main():
    # A rounded rectangular shovel silhouette, lofted into a bulbous 3D back.
    outer_outline = rounded_outline(
        [
            (-7.0, 0.0), (-8.0, 2.0), (-8.0, 13.0), (-7.4, 17.0),
            (-5.8, 21.5), (-3.5, 27.0), (3.5, 27.0), (5.8, 21.5),
            (7.4, 17.0), (8.0, 13.0), (8.0, 2.0), (7.0, 0.0),
        ],
        17.0,
        27.5,
        0.0,
    )
    outer = loft_solid(
        outer_outline,
        [(-5.3, 0.78), (-4.5, 0.90), (-3.0, 0.97), (-1.0, 1.0),
         (1.5, 1.0), (3.8, 0.95), (5.0, 0.82)],
    )

    # The cavity begins 2 mm behind the leading edge, preserving a solid lip.
    inner_outline = rounded_outline(
        [
            (-5.2, 2.0), (-6.0, 3.0), (-6.0, 13.0), (-5.2, 16.5),
            (-3.4, 21.0), (-2.6, 23.5), (2.6, 23.5), (3.4, 21.0),
            (5.2, 16.5), (6.0, 13.0), (6.0, 3.0), (5.2, 2.0),
        ],
        12.4,
        21.5,
        2.0,
    )
    inner = loft_solid(
        inner_outline,
        [(-2.25, 0.55), (-1.6, 0.70), (-0.5, 0.82), (1.0, 0.92),
         (3.0, 1.0), (5.5, 1.05), (7.0, 1.08)],
    )
    scoop_shell = trimesh.boolean.difference([outer, inner], engine="manifold")

    handle_points = [
        (0.0, 23.5, 0.1), (0.5, 30.0, 0.8), (-0.6, 37.0, 0.2),
        (0.4, 44.0, 0.9), (0.0, 51.0, 0.5), (0.6, 56.7, 0.8),
    ]
    handle_radii = [3.75, 3.55, 3.35, 3.25, 3.15, 3.30]
    handle = organic_branch(handle_points, handle_radii)

    branch_left = organic_branch(
        [(-0.1, 45.0, 0.7), (-3.3, 48.3, 0.8), (-5.1, 50.0, 0.6)],
        [1.8, 1.45, 1.05],
    )
    branch_right = organic_branch(
        [(0.1, 35.0, 0.4), (3.0, 38.0, 0.8), (4.6, 39.5, 0.7)],
        [1.65, 1.30, 0.95],
    )

    wraps = [
        torus_y(3.90 - 0.06 * i, 0.45, (0.15, 25.3 + 1.05 * i, 0.15))
        for i in range(4)
    ]
    base = trimesh.boolean.union(
        [scoop_shell, handle, branch_left, branch_right, *wraps], engine="manifold"
    )
    # The lower handle overlaps the shell for strength; re-cut the bowl after
    # that union so it cannot leave a rounded intrusion inside the cavity.
    base = trimesh.boolean.difference([base, inner], engine="manifold")

    # Bark fibres, sized to remain printable with a 0.4 mm nozzle.
    bark_ridges = []
    for ridge_index, angle in enumerate((-1.15, -0.55, 0.05, 0.65, 1.22)):
        ridge_points = []
        for y in np.linspace(29.0, 55.0, 9):
            cx, cz = handle_center(y)
            theta = angle + 0.09 * np.sin(y * 0.55 + ridge_index)
            surface_r = 3.18
            ridge_points.append(
                (cx + surface_r * np.sin(theta), y, cz + surface_r * np.cos(theta))
            )
        bark_ridges.append(tube_path(ridge_points, 0.20, sections=18))

    # Raised wood grain follows the curved inner bowl floor.
    bowl_grain = []
    for grain_index, x_base in enumerate((-3.7, -1.9, 0.0, 1.9, 3.7)):
        points = []
        for y in np.linspace(3.0, 20.0, 10):
            x = x_base + 0.18 * np.sin(y * 0.65 + grain_index)
            # Approximate the lofted inner floor: deepest at the middle and
            # gradually rising toward the lip and sides.
            lateral = min(1.0, abs(x) / 6.2)
            longitudinal = min(1.0, abs(y - 12.75) / 10.75)
            z_floor = -2.25 + 2.1 * max(lateral ** 1.7, longitudinal ** 1.7)
            points.append((x, y, z_floor + 0.12))
        if len(points) > 1:
            bowl_grain.append(tube_path(points, 0.19, sections=18))

    knots = [
        ellipsoid((1.15, 1.55, 0.42), (-2.55, 33.5, 2.05), subdivisions=3),
        ellipsoid((0.95, 1.30, 0.38), (2.45, 42.0, 2.15), subdivisions=3),
        ellipsoid((0.85, 1.10, 0.34), (-2.35, 52.0, 1.85), subdivisions=3),
    ]
    body = trimesh.boolean.union(
        [base, *bark_ridges, *bowl_grain, *knots], engine="manifold"
    )

    # Preserve the requested exact overall length.
    y_length = body.bounds[1, 1] - body.bounds[0, 1]
    body.apply_scale((1.0, 60.0 / y_length, 1.0))
    body.apply_translation((0.0, -body.bounds[0, 1], 0.0))

    source = manifold3d.Mesh(
        np.asarray(body.vertices, dtype=np.float32),
        np.asarray(body.faces, dtype=np.uint32),
    )
    rebuilt = manifold3d.Manifold(source).simplify(1e-4).to_mesh()
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
