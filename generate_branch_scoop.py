"""Generate a detailed 90 mm carved-branch scoop and breakaway support set."""

from pathlib import Path
import os
import time

import manifold3d
import numpy as np
import trimesh
from shapely.geometry import Polygon


ROOT = Path(__file__).parent
MODEL_OUT = ROOT / "Лопатка Model 1.stl"
SUPPORT_OUT = ROOT / "Лопатка Model 1 Support.stl"
PRINT_OUT = ROOT / "Лопатка Model 1 Print Set.stl"
SECTIONS = 56


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


def organic_branch(points, radii, round_start=True, round_end=True):
    parts = [
        frustum_between(points[i], points[i + 1], radii[i], radii[i + 1])
        for i in range(len(points) - 1)
    ]
    for i, (point, radius) in enumerate(zip(points, radii)):
        if (i == 0 and not round_start) or (i == len(points) - 1 and not round_end):
            continue
        parts.append(sphere(radius, point))
    return trimesh.boolean.union(parts, engine="manifold")


def tube_path(points, radius, sections=24):
    parts = [
        frustum_between(start, end, radius, radius, sections)
        for start, end in zip(points[:-1], points[1:])
    ]
    parts.extend(sphere(radius, point, subdivisions=2) for point in points)
    return trimesh.boolean.union(parts, engine="manifold")


def rounded_outline(points, target_width, target_length, y_min, count=144):
    polygon = Polygon(points).buffer(0.9, join_style="round", resolution=24)
    ring = polygon.exterior
    sampled = np.array(
        [ring.interpolate(d).coords[0] for d in np.linspace(0, ring.length, count, endpoint=False)]
    )
    sampled[:, 0] -= (sampled[:, 0].min() + sampled[:, 0].max()) / 2
    sampled[:, 0] *= target_width / np.ptp(sampled[:, 0])
    sampled[:, 1] -= sampled[:, 1].min()
    sampled[:, 1] *= target_length / np.ptp(sampled[:, 1])
    sampled[:, 1] += y_min
    return sampled


def loft_solid(outline, layers):
    centre = np.array([0.0, (outline[:, 1].min() + outline[:, 1].max()) / 2])
    rings = []
    for z_value, scale in layers:
        xy = centre + (outline - centre) * scale
        rings.append(np.column_stack((xy, np.full(len(xy), z_value))))
    vertices = np.vstack(
        (*rings, [centre[0], centre[1], layers[0][0]], [centre[0], centre[1], layers[-1][0]])
    )
    count = len(outline)
    faces = []
    for layer_index in range(len(layers) - 1):
        a0 = layer_index * count
        b0 = (layer_index + 1) * count
        for i in range(count):
            j = (i + 1) % count
            faces.extend(((a0 + i, a0 + j, b0 + j), (a0 + i, b0 + j, b0 + i)))
    bottom = count * len(layers)
    top = bottom + 1
    top_ring = count * (len(layers) - 1)
    for i in range(count):
        j = (i + 1) % count
        faces.extend(((bottom, j, i), (top, top_ring + i, top_ring + j)))
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=True)
    if mesh.volume < 0:
        mesh.invert()
    return mesh


def open_leading_edge_cutter():
    """Cut an open scoop mouth with a smooth floor running into a thin lip."""
    # Each station is (Y, half width, floor Z).  The cutter starts outside the
    # scoop and follows a single continuous ramp into the existing bowl.  Its
    # width leaves the side walls intact, while allowing them to taper to almost
    # nothing at the working edge.
    stations = [
        (-3.0, 14.0, -0.55),
        (0.0, 13.2, -0.72),
        (2.5, 12.3, -1.62),
        (5.5, 10.9, -2.48),
        (9.0, 9.50, -3.02),
    ]
    top_z = 10.0
    vertices = []
    for y_value, half_width, floor_z in stations:
        vertices.extend(
            [
                (-half_width, y_value, floor_z),
                (half_width, y_value, floor_z),
                (-half_width, y_value, top_z),
                (half_width, y_value, top_z),
            ]
        )

    faces = []
    for station_index in range(len(stations) - 1):
        a = station_index * 4
        b = (station_index + 1) * 4
        # Sloping cutter floor, top, and both continuous side faces.
        faces.extend(
            [
                (a, b + 1, a + 1), (a, b, b + 1),
                (a + 2, a + 3, b + 3), (a + 2, b + 3, b + 2),
                (a, a + 2, b + 2), (a, b + 2, b),
                (a + 1, b + 1, b + 3), (a + 1, b + 3, a + 3),
            ]
        )
    last = (len(stations) - 1) * 4
    faces.extend(
        [
            (0, 1, 3), (0, 3, 2),
            (last, last + 2, last + 3), (last, last + 3, last + 1),
        ]
    )
    cutter = trimesh.Trimesh(
        vertices=np.asarray(vertices), faces=np.asarray(faces), process=True
    )
    if cutter.volume < 0:
        cutter.invert()
    return cutter


def helix_wrap(turns, y_start, y_end, centre, major_radius, tube_radius):
    count = int(turns * 56) + 1
    values = np.linspace(0, 2 * np.pi * turns, count)
    cx, cz = centre
    points = []
    for i, value in enumerate(values):
        fraction = i / (count - 1)
        points.append(
            (
                cx + major_radius * np.cos(value),
                y_start + fraction * (y_end - y_start),
                cz + major_radius * np.sin(value),
            )
        )
    return tube_path(points, tube_radius, sections=18)


def handle_center(y):
    control = np.array(
        [
            [35.5, 0.0, 0.0], [45.0, 0.8, 1.0], [56.0, -0.9, 0.3],
            [66.0, 0.6, 1.2], [76.0, 0.0, 0.5], [85.1, 0.8, 0.8],
        ]
    )
    return (
        np.interp(y, control[:, 0], control[:, 1]),
        np.interp(y, control[:, 0], control[:, 2]),
    )


def handle_radius(y):
    return np.interp(y, [35.5, 45.0, 56.0, 66.0, 76.0, 85.1], [5.4, 5.2, 5.0, 4.8, 4.7, 4.9])


def clean_mesh(mesh, tolerance=2e-5):
    source = manifold3d.Mesh(
        np.asarray(mesh.vertices, dtype=np.float32),
        np.asarray(mesh.faces, dtype=np.uint32),
    )
    rebuilt = manifold3d.Manifold(source).simplify(tolerance).to_mesh()
    return trimesh.Trimesh(
        vertices=np.asarray(rebuilt.vert_properties)[:, :3],
        faces=np.asarray(rebuilt.tri_verts),
        process=True,
    )


def build_model():
    # Front silhouette closely follows the straight-sided concept scoop.
    outer_outline = rounded_outline(
        [
            (-10.5, 0), (-12.5, 2.5), (-12.6, 19.5), (-11.5, 25.5),
            (-8.8, 32.0), (-5.0, 40.5), (5.0, 40.5), (8.8, 32.0),
            (11.5, 25.5), (12.6, 19.5), (12.5, 2.5), (10.5, 0),
        ],
        25.5,
        41.0,
        0.0,
    )
    outer = loft_solid(
        outer_outline,
        [(-6.0, 0.80), (-5.2, 0.90), (-3.7, 0.97), (-1.5, 1.0),
         (1.0, 1.0), (3.0, 0.96), (4.5, 0.84)],
    )

    inner_outline = rounded_outline(
        [
            (-7.6, 3.0), (-9.4, 4.5), (-9.4, 19.0), (-8.2, 24.0),
            (-5.2, 31.5), (-3.8, 35.0), (3.8, 35.0), (5.2, 31.5),
            (8.2, 24.0), (9.4, 19.0), (9.4, 4.5), (7.6, 3.0),
        ],
        19.0,
        32.5,
        3.0,
    )
    inner = loft_solid(
        inner_outline,
        [(-3.0, 0.56), (-2.2, 0.70), (-0.8, 0.83), (1.0, 0.93),
         (3.0, 1.0), (5.5, 1.04), (7.2, 1.07)],
    )
    nose_cutter = open_leading_edge_cutter()
    scoop_shell = trimesh.boolean.difference(
        [outer, inner, nose_cutter], engine="manifold"
    )

    handle_points = [
        (0.0, 35.5, 0.0), (0.8, 45.0, 1.0), (-0.9, 56.0, 0.3),
        (0.6, 66.0, 1.2), (0.0, 76.0, 0.5), (0.8, 85.1, 0.8),
    ]
    handle = organic_branch(handle_points, [5.4, 5.2, 5.0, 4.8, 4.7, 4.9])
    upper_branch = organic_branch(
        [(0.2, 68.0, 1.0), (-4.8, 73.0, 1.3), (-7.4, 75.5, 1.0)],
        [2.8, 2.2, 1.55],
        round_end=False,
    )
    middle_branch = organic_branch(
        [(0.2, 52.0, 0.6), (4.3, 56.2, 1.2), (6.8, 58.6, 1.0)],
        [2.5, 1.9, 1.4],
        round_end=False,
    )
    rope = helix_wrap(3.6, 37.0, 43.0, (0.2, 0.3), 5.55, 0.58)

    base = trimesh.boolean.union(
        [scoop_shell, handle, upper_branch, middle_branch, rope], engine="manifold"
    )
    base = trimesh.boolean.difference(
        [base, inner, nose_cutter], engine="manifold"
    )

    # Incised bark grooves, then raised fibres: both are physical geometry.
    groove_cutters = []
    for groove_index, angle in enumerate(np.linspace(-2.6, 2.6, 9)):
        points = []
        for y in np.linspace(45.0, 83.0, 13):
            cx, cz = handle_center(y)
            theta = angle + 0.12 * np.sin(y * 0.38 + groove_index)
            radius = handle_radius(y) - 0.04
            points.append((cx + radius * np.sin(theta), y, cz + radius * np.cos(theta)))
        groove_cutters.append(tube_path(points, 0.22, sections=16))
    base = trimesh.boolean.difference([base, *groove_cutters], engine="manifold")

    bark_ridges = []
    for ridge_index, angle in enumerate(np.linspace(-2.9, 2.9, 12)):
        points = []
        y0 = 44.0 + (ridge_index % 3) * 0.7
        for y in np.linspace(y0, 83.5, 14):
            cx, cz = handle_center(y)
            theta = angle + 0.11 * np.sin(y * 0.42 + ridge_index * 0.8)
            radius = handle_radius(y) - 0.10
            points.append((cx + radius * np.sin(theta), y, cz + radius * np.cos(theta)))
        bark_ridges.append(tube_path(points, 0.27, sections=18))

    # Branch bark follows each offshoot.
    branch_ridges = []
    for offset in (-0.7, 0.0, 0.7):
        branch_ridges.append(
            tube_path(
                [(-0.1 + offset, 68.0, 3.2), (-4.7 + offset * 0.5, 73.0, 2.9), (-7.1, 75.2, 2.0)],
                0.23,
                sections=16,
            )
        )
        branch_ridges.append(
            tube_path(
                [(0.2 + offset, 52.0, 2.8), (4.2 + offset * 0.5, 56.1, 2.7), (6.5, 58.4, 1.8)],
                0.22,
                sections=16,
            )
        )

    # Curved grain inside the bowl.
    bowl_grain = []
    for grain_index, x_base in enumerate(np.linspace(-7.0, 7.0, 9)):
        points = []
        for y in np.linspace(6.0, 32.5, 16):
            x = x_base + 0.28 * np.sin(y * 0.42 + grain_index)
            lateral = min(1.0, abs(x) / 9.5)
            longitudinal = min(1.0, abs(y - 19.25) / 16.25)
            z_floor = -3.0 + 2.8 * max(lateral ** 1.7, longitudinal ** 1.7)
            points.append((x, y, z_floor + 0.15))
        bowl_grain.append(tube_path(points, 0.25, sections=18))

    # Grain on the convex back for the printed physical texture.
    back_grain = []
    for grain_index, x_base in enumerate(np.linspace(-8.0, 8.0, 9)):
        points = []
        for y in np.linspace(5.0, 35.0, 15):
            x = x_base + 0.35 * np.sin(y * 0.34 + grain_index)
            lateral = min(1.0, abs(x) / 12.75)
            longitudinal = min(1.0, abs(y - 20.5) / 20.5)
            z_back = -6.0 + 2.0 * max(lateral ** 1.8, longitudinal ** 1.8)
            points.append((x, y, z_back - 0.05))
        back_grain.append(tube_path(points, 0.26, sections=18))

    knots = [
        ellipsoid((1.8, 2.3, 0.62), (-4.0, 48.0, 3.7), subdivisions=3),
        ellipsoid((1.5, 2.0, 0.55), (3.9, 61.0, 3.8), subdivisions=3),
        ellipsoid((1.35, 1.8, 0.50), (-3.7, 77.0, 3.4), subdivisions=3),
        ellipsoid((1.25, 1.6, 0.46), (3.5, 70.5, 3.2), subdivisions=3),
    ]

    model = trimesh.boolean.union(
        [base, *bark_ridges, *branch_ridges, *bowl_grain, *back_grain, *knots],
        engine="manifold",
    )
    # Re-cut after adding physical grain so the complete leading-edge route is
    # open and its floor has no transverse ridge or floating texture segment.
    model = trimesh.boolean.difference([model, nose_cutter], engine="manifold")
    # Exact requested 90 mm length.
    y_length = model.bounds[1, 1] - model.bounds[0, 1]
    model.apply_scale((1.0, 90.0 / y_length, 1.0))
    model.apply_translation((0.0, -model.bounds[0, 1], 0.0))
    return clean_mesh(model)


def make_underside_sampler(mesh):
    """Cache triangle projections and return an exact underside-Z sampler."""
    triangles = mesh.vertices[mesh.faces]
    xy = triangles[:, :, :2]
    minimum = xy.min(axis=1)
    maximum = xy.max(axis=1)

    def sample(x, y):
        mask = (
            (minimum[:, 0] <= x) & (maximum[:, 0] >= x) &
            (minimum[:, 1] <= y) & (maximum[:, 1] >= y)
        )
        candidates = triangles[mask]
        if len(candidates) == 0:
            return None
        a = candidates[:, 0]
        b = candidates[:, 1]
        c = candidates[:, 2]
        v0 = b[:, :2] - a[:, :2]
        v1 = c[:, :2] - a[:, :2]
        v2 = np.array([x, y]) - a[:, :2]
        denominator = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
        valid = np.abs(denominator) > 1e-10
        u = np.zeros(len(candidates))
        v = np.zeros(len(candidates))
        u[valid] = (v2[valid, 0] * v1[valid, 1] - v1[valid, 0] * v2[valid, 1]) / denominator[valid]
        v[valid] = (v0[valid, 0] * v2[valid, 1] - v2[valid, 0] * v0[valid, 1]) / denominator[valid]
        inside = valid & (u >= -1e-7) & (v >= -1e-7) & (u + v <= 1.0 + 1e-7)
        if not np.any(inside):
            return None
        z_values = a[:, 2] + u * (b[:, 2] - a[:, 2]) + v * (c[:, 2] - a[:, 2])
        return float(np.min(z_values[inside]))

    return sample


def build_support_set(model):
    print_model = model.copy()
    z_shift = 3.0 - print_model.bounds[0, 2]
    print_model.apply_translation((0.0, 0.0, z_shift))
    # Rebuild after translation so float32 STL quantisation cannot collapse tiny
    # bark triangles when their Z coordinates become larger.
    print_model = clean_mesh(print_model, tolerance=2e-5)
    min_x, min_y = print_model.bounds[0, :2]
    max_x, max_y = print_model.bounds[1, :2]
    grid_parts = []
    # 0.7 mm breakaway lattice on the build plate.
    for x in np.arange(np.floor(min_x) - 1.5, np.ceil(max_x) + 1.6, 5.0):
        beam = trimesh.creation.box((0.7, max_y - min_y + 4.0, 0.55))
        beam.apply_translation((x, (min_y + max_y) / 2, 0.275))
        grid_parts.append(beam)
    for y in np.arange(np.floor(min_y) - 1.5, np.ceil(max_y) + 1.6, 5.0):
        beam = trimesh.creation.box((max_x - min_x + 4.0, 0.7, 0.55))
        beam.apply_translation(((min_x + max_x) / 2, y, 0.275))
        grid_parts.append(beam)

    contact_xy = []
    # Dense points below the convex scoop back.
    for y in [0.7, 2.2, *np.arange(4.0, 40.0, 4.5)]:
        half_width = 12.2 if y <= 20 else max(3.5, 12.2 - (y - 20) * 0.43)
        for x in np.arange(-10.0, 10.1, 4.0):
            if abs(x) > half_width - 0.7:
                continue
            contact_xy.append((x, y))

    # Three support rows follow the round crooked handle.
    for y in np.arange(40.0, 88.0, 4.5):
        cx, cz = handle_center(y)
        radius = handle_radius(y)
        for dx in (-2.8, 0.0, 2.8):
            if abs(dx) >= radius:
                continue
            contact_xy.append((cx + dx, y))

    # Extra contacts under both side branches.
    for fraction in np.linspace(0.2, 0.9, 5):
        x = -0.1 + fraction * (-7.4 + 0.1)
        y = 68.0 + fraction * (75.5 - 68.0)
        contact_xy.append((x, y))
        x = 0.2 + fraction * (6.8 - 0.2)
        y = 52.0 + fraction * (58.6 - 52.0)
        contact_xy.append((x, y))

    pillars = []
    underside = make_underside_sampler(print_model)
    for x, y in contact_xy:
        bottom = underside(x, y)
        if bottom is None:
            continue
        top = bottom - 0.24
        if top > 0.7:
            pillars.append(
                frustum_between((x, y, 0.55), (x, y, top), 0.62, 0.28, sections=20)
            )
    # Keep the breakaway lattice as overlapping closed shells. Slicers merge
    # these automatically; a huge boolean union adds no printing benefit and is
    # unnecessarily expensive for the many fine contact pillars.
    support = trimesh.util.concatenate([*grid_parts, *pillars])
    print_set = trimesh.util.concatenate((print_model, support))
    return support, print_set


def report(label, mesh):
    print(
        f"{label}: vertices={len(mesh.vertices)} faces={len(mesh.faces)} "
        f"watertight={mesh.is_watertight} bounds={np.round(mesh.bounds, 2).tolist()}"
    )


def export_stl(mesh, destination, temporary_name):
    """Write through an ASCII temporary file, then atomically replace output."""
    temporary = ROOT / temporary_name
    mesh.export(temporary, file_type="stl")
    for attempt in range(6):
        try:
            os.replace(temporary, destination)
            return
        except OSError:
            if attempt == 5:
                raise
            time.sleep(0.25)


def main():
    model = build_model()
    export_stl(model, MODEL_OUT, "lopatka-model.tmp.stl")
    report(MODEL_OUT.name, model)
    support, print_set = build_support_set(model)
    export_stl(support, SUPPORT_OUT, "lopatka-support.tmp.stl")
    export_stl(print_set, PRINT_OUT, "lopatka-print-set.tmp.stl")
    report(SUPPORT_OUT.name, support)
    report(PRINT_OUT.name, print_set)


if __name__ == "__main__":
    main()
