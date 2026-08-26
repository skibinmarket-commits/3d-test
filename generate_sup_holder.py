"""Generate Model4_SUP_holder.stl from the agreed dimensions.

Requires: trimesh and manifold3d.
All dimensions are millimetres.
"""

from pathlib import Path

import numpy as np
import trimesh
import manifold3d
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from shapely.geometry import GeometryCollection, Polygon


SEGMENTS = 128


def moved(mesh, xyz):
    mesh.apply_translation(xyz)
    return mesh


def box(size, center):
    return moved(trimesh.creation.box(extents=size), center)


def cylinder(radius, height, center):
    return moved(
        trimesh.creation.cylinder(radius=radius, height=height, sections=SEGMENTS),
        center,
    )


def frustum(radius_bottom, radius_top, height, center_z):
    """Closed vertical conical frustum."""
    angles = np.linspace(0, 2 * np.pi, SEGMENTS, endpoint=False)
    lower = np.column_stack((radius_bottom * np.cos(angles), radius_bottom * np.sin(angles), np.full(SEGMENTS, center_z - height / 2)))
    upper = np.column_stack((radius_top * np.cos(angles), radius_top * np.sin(angles), np.full(SEGMENTS, center_z + height / 2)))
    vertices = np.vstack((lower, upper, [[0, 0, center_z - height / 2], [0, 0, center_z + height / 2]]))
    faces = []
    for i in range(SEGMENTS):
        j = (i + 1) % SEGMENTS
        faces.extend(((i, j, SEGMENTS + j), (i, SEGMENTS + j, SEGMENTS + i)))
        faces.extend(((2 * SEGMENTS, j, i), (2 * SEGMENTS + 1, SEGMENTS + i, SEGMENTS + j)))
    return trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=True)


def pick_funnel(depth, surface_z, center_xy, rotation_deg, variation=0.0):
    """Asymmetric rounded-triangle collector lofted into a Ø4 outlet."""
    count = 96
    angles = np.linspace(0, 2 * np.pi, count, endpoint=False)
    rotation = np.radians(rotation_deg)
    # A rounded guitar-pick outline with deliberately mild asymmetry.
    top_radius = 6.15 * (
        1.0
        + 0.16 * np.cos(3 * (angles - rotation))
        + 0.045 * np.cos(2 * angles + variation)
        + 0.025 * np.sin(5 * angles - 0.7 * variation)
    )
    cx, cy = center_xy
    lower = np.column_stack(
        (
            cx + 2.0 * np.cos(angles),
            cy + 2.0 * np.sin(angles),
            np.full(count, surface_z - depth),
        )
    )
    upper = np.column_stack(
        (
            cx + top_radius * np.cos(angles),
            cy + top_radius * np.sin(angles),
            np.full(count, surface_z),
        )
    )
    vertices = np.vstack(
        (lower, upper, [[cx, cy, surface_z - depth], [cx, cy, surface_z]])
    )
    faces = []
    for i in range(count):
        j = (i + 1) % count
        faces.extend(((i, j, count + j), (i, count + j, count + i)))
        faces.extend(((2 * count, j, i), (2 * count + 1, count + i, count + j)))
    return trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=True)


def engraved_text(text, height, depth, center_x, front_y, center_z):
    """Create bold vector text cutter facing toward negative Y."""
    font = FontProperties(fname=r"C:\Windows\Fonts\arialbd.ttf")
    path = TextPath((0, 0), text, size=height, prop=font)
    polygons = [Polygon(p) for p in path.to_polygons() if len(p) >= 3]
    shape = GeometryCollection()
    for polygon in polygons:
        shape = shape.symmetric_difference(polygon)
    min_x, min_y, max_x, max_y = shape.bounds
    scale = height / (max_y - min_y)
    from shapely import affinity

    shape = affinity.scale(shape, xfact=scale, yfact=scale, origin=(0, 0))
    min_x, min_y, max_x, max_y = shape.bounds
    shape = affinity.translate(shape, xoff=-(min_x + max_x) / 2, yoff=-(min_y + max_y) / 2)
    meshes = []
    parts = list(shape.geoms) if hasattr(shape, "geoms") else [shape]
    for part in parts:
        if not part.is_empty:
            meshes.append(trimesh.creation.extrude_polygon(part, height=depth, engine="earcut"))
    result = trimesh.util.concatenate(meshes)
    result.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (1, 0, 0)))
    result.apply_translation((center_x, front_y + 0.1, center_z))
    return result


def rounded_box(width, depth, height, radius, center):
    """Axis-aligned rounded rectangle extruded along Z."""
    x, y, z = center
    parts = [
        box((width - 2 * radius, depth, height), (x, y, z)),
        box((width, depth - 2 * radius, height), (x, y, z)),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(
                cylinder(
                    radius,
                    height,
                    (
                        x + sx * (width / 2 - radius),
                        y + sy * (depth / 2 - radius),
                        z,
                    ),
                )
            )
    return trimesh.boolean.union(parts, engine="manifold")


def main():
    # Agreed dimensions
    cup_inner_d = 76.0
    cup_wall = 3.0
    cup_outer_d = 82.0
    cup_inner_h = 100.0
    cup_floor = 3.0
    slot_width = 7.0
    slot_corner_r = 3.0
    platform_h = 5.0
    platform_d = 110.0

    phone_inner_w = 81.0
    phone_inner_d = 16.0
    phone_inner_h = 80.0
    phone_wall = 3.0
    phone_floor = 5.0
    phone_outer_w = phone_inner_w + 2 * phone_wall
    phone_outer_d = phone_inner_d + 2 * phone_wall

    cup_floor_z = platform_h + cup_floor
    cup_top_z = cup_floor_z + cup_inner_h

    # Phone pocket slightly overlaps the cup to make a single strong body.
    phone_x0 = cup_outer_d / 2 - 3.0
    phone_center_x = phone_x0 + phone_outer_w / 2
    phone_top_z = platform_h + phone_floor + phone_inner_h

    # 5 mm common platform: round under the cup, rounded extension under phone.
    platform_circle = cylinder(platform_d / 2, platform_h, (0, 0, platform_h / 2))
    platform_phone = rounded_box(
        phone_outer_w,
        phone_outer_d + 8.0,
        platform_h,
        5.0,
        (phone_center_x, 0, platform_h / 2),
    )
    solid = trimesh.boolean.union([platform_circle, platform_phone], engine="manifold")

    # Circular 45-degree reinforcement outside the cup only.  It must be an
    # annulus: a solid cone here would cover the cup drain holes from above.
    base_reinforcement_outer = frustum(50.0, 41.5, 8.5, platform_h + 4.25)
    base_reinforcement_inner = cylinder(40.5, 10.5, (0, 0, platform_h + 4.25))
    base_reinforcement = trimesh.boolean.difference(
        [base_reinforcement_outer, base_reinforcement_inner], engine="manifold"
    )
    solid = trimesh.boolean.union([solid, base_reinforcement], engine="manifold")

    # Cup shell and its separate 3 mm floor above the platform.
    cup_outer = cylinder(
        cup_outer_d / 2,
        cup_top_z - platform_h,
        (0, 0, (platform_h + cup_top_z) / 2),
    )
    cup_void = cylinder(
        cup_inner_d / 2,
        cup_inner_h + 0.6,
        (0, 0, cup_floor_z + cup_inner_h / 2 + 0.3),
    )
    cup = trimesh.boolean.difference([cup_outer, cup_void], engine="manifold")

    # Four 7 mm radial slots, equally spaced and rotated away from phone joint.
    cutters = []
    cutter_length = cup_outer_d + 8.0
    slot_bottom_center_z = cup_floor_z + slot_width / 2 - 2.0
    cutter_h = cup_top_z - slot_bottom_center_z + 0.4
    for angle in (45.0, 135.0, 225.0, 315.0):
        cutter = box(
            (cutter_length, slot_width, cutter_h),
            (
                cutter_length / 2 - 1.0,
                0,
                slot_bottom_center_z + cutter_h / 2,
            ),
        )
        cutter.apply_transform(trimesh.transformations.rotation_matrix(np.radians(angle), (0, 0, 1)))
        cutters.append(cutter)
        # Semicircular lower end makes the slot an open-top U-shaped rope seat.
        slot_bottom = cylinder(slot_width / 2, cutter_length, (0, 0, 0))
        slot_bottom.apply_transform(
            trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0))
        )
        slot_bottom.apply_translation(
            (cutter_length / 2 - 1.0, 0, slot_bottom_center_z)
        )
        slot_bottom.apply_transform(
            trimesh.transformations.rotation_matrix(np.radians(angle), (0, 0, 1))
        )
        cutters.append(slot_bottom)
        # Continue the rounded channel diagonally down the reinforcement and
        # all the way through the outer edge of the 110 mm platform.
        a = np.radians(angle)
        start = np.array([43.0 * np.cos(a), 43.0 * np.sin(a), slot_bottom_center_z])
        end = np.array([58.0 * np.cos(a), 58.0 * np.sin(a), platform_h + 1.5])
        slope_channel = trimesh.creation.cylinder(
            radius=slot_width / 2,
            sections=96,
            segment=np.vstack((start, end)),
        )
        cutters.append(slope_channel)
        # Round the two exposed top corners of each wall segment (R3).
        x_mid = (cup_inner_d / 2 + cup_outer_d / 2) / 2
        radial_depth = cup_wall + 4.0
        for side in (-1.0, 1.0):
            corner_box = box(
                (radial_depth, slot_corner_r, slot_corner_r),
                (x_mid, side * (slot_width / 2 + slot_corner_r / 2), cup_top_z - slot_corner_r / 2),
            )
            round_keep = cylinder(slot_corner_r, radial_depth + 2.0, (0, 0, 0))
            round_keep.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0)))
            round_keep.apply_translation((x_mid, side * (slot_width / 2 + slot_corner_r), cup_top_z - slot_corner_r))
            corner_cut = trimesh.boolean.difference([corner_box, round_keep], engine="manifold")
            corner_cut.apply_transform(trimesh.transformations.rotation_matrix(np.radians(angle), (0, 0, 1)))
            cutters.append(corner_cut)
    cup = trimesh.boolean.difference([cup, *cutters], engine="manifold")

    # Rounded phone pocket, open at the top.
    phone_outer = rounded_box(
        phone_outer_w,
        phone_outer_d,
        phone_top_z - platform_h,
        4.0,
        (phone_center_x, 0, (platform_h + phone_top_z) / 2),
    )
    phone_void = rounded_box(
        phone_inner_w,
        phone_inner_d,
        phone_inner_h + 0.6,
        2.0,
        (phone_center_x, 0, platform_h + phone_floor + phone_inner_h / 2 + 0.3),
    )
    phone = trimesh.boolean.difference([phone_outer, phone_void], engine="manifold")

    # Vertical rounded gussets reinforce the cup-to-pocket junction.
    gussets = []
    for y in (-phone_outer_d / 2 + 2.5, phone_outer_d / 2 - 2.5):
        gussets.append(cylinder(5.0, 70.0, (phone_x0 + 1.0, y, 40.0)))

    solid = trimesh.boolean.union([solid, cup, phone, *gussets], engine="manifold")

    # Re-cut the full Ø76 mm useful bore after every reinforcement and phone
    # part has been joined. This removes the two vertical intrusions which could
    # otherwise catch a bottle while preserving the 3 mm cup floor below Z=8.
    cup_clearance = cylinder(
        cup_inner_d / 2,
        cup_inner_h + 0.8,
        (0, 0, cup_floor_z + cup_inner_h / 2 + 0.4),
    )
    solid = trimesh.boolean.difference([solid, cup_clearance], engine="manifold")

    # 10 mm tall, 1 mm deep engraving on the broad front face.
    text_cut = engraved_text(
        "Red Rocket",
        10.0,
        1.2,
        phone_center_x,
        -phone_outer_d / 2,
        50.0,
    )
    solid = trimesh.boolean.difference([solid, text_cut], engine="manifold")

    # Drainage: each Ø4 through-hole has its own asymmetric rounded triangular
    # collector, similar to a guitar pick, lofted down into the outlet.
    drains = []
    collector_rotations = (12.0, 101.0, 207.0, 296.0)
    for index, angle in enumerate((0.0, 90.0, 180.0, 270.0)):
        a = np.radians(angle)
        drain_xy = (15 * np.cos(a), 15 * np.sin(a))
        drains.append(cylinder(2.0, cup_floor_z + 2.0, (*drain_xy, cup_floor_z / 2)))
        drains.append(
            pick_funnel(
                1.5,
                cup_floor_z,
                drain_xy,
                collector_rotations[index],
                variation=index * 0.8,
            )
        )
    for index, dx in enumerate((-22.0, 22.0)):
        drains.append(cylinder(2.0, platform_h + phone_floor + 2.0, (phone_center_x + dx, 0, (platform_h + phone_floor) / 2)))
        drains.append(
            pick_funnel(
                1.5,
                platform_h + phone_floor,
                (phone_center_x + dx, 0),
                (-18.0, 23.0)[index],
                variation=3.7 + index,
            )
        )
    solid = trimesh.boolean.difference([solid, *drains], engine="manifold")

    print(f"raw_watertight={solid.is_watertight} raw_degenerate={int(np.sum(solid.area_faces < 1e-10))}")
    # Rebuild once through Manifold and simplify only zero-length seams created
    # by coplanar booleans. This keeps the surface closed while removing them.
    source_mesh = manifold3d.Mesh(
        np.asarray(solid.vertices, dtype=np.float32),
        np.asarray(solid.faces, dtype=np.uint32),
    )
    rebuilt = manifold3d.Manifold(source_mesh).simplify(1e-5).to_mesh()
    solid = trimesh.Trimesh(
        vertices=np.asarray(rebuilt.vert_properties)[:, :3],
        faces=np.asarray(rebuilt.tri_verts),
        process=True,
    )
    output = Path(__file__).with_name("Model4_SUP_phone_cup_holder.stl")
    solid.export(output)
    print(f"Wrote {output.name}")
    print(f"vertices={len(solid.vertices)} faces={len(solid.faces)}")
    print(f"watertight={solid.is_watertight} volume_mm3={solid.volume:.1f}")
    print(f"bounds_mm={np.round(solid.bounds, 2).tolist()}")


if __name__ == "__main__":
    main()
