"""Generate Model4_SUP_holder.stl from the agreed dimensions.

Requires: trimesh and manifold3d.
All dimensions are millimetres.
"""

from pathlib import Path

import numpy as np
import trimesh


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
    cutter_h = cup_inner_h + 0.4
    for angle in (45.0, 135.0, 225.0, 315.0):
        cutter = box(
            (cutter_length, slot_width, cutter_h),
            (cutter_length / 2 - 1.0, 0, cup_floor_z + cutter_h / 2),
        )
        cutter.apply_transform(trimesh.transformations.rotation_matrix(np.radians(angle), (0, 0, 1)))
        cutters.append(cutter)
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

    # Drainage: four cup holes and two phone-pocket holes. Conical mouths soften edges.
    drains = []
    for angle in (0.0, 90.0, 180.0, 270.0):
        a = np.radians(angle)
        drains.append(cylinder(2.0, cup_floor_z + 2.0, (15 * np.cos(a), 15 * np.sin(a), cup_floor_z / 2)))
        chamfer = trimesh.creation.cone(radius=3.0, height=1.2, sections=64)
        chamfer.apply_transform(trimesh.transformations.rotation_matrix(np.pi, (1, 0, 0)))
        drains.append(moved(chamfer, (15 * np.cos(a), 15 * np.sin(a), cup_floor_z)))
    for dx in (-22.0, 22.0):
        drains.append(cylinder(2.0, platform_h + phone_floor + 2.0, (phone_center_x + dx, 0, (platform_h + phone_floor) / 2)))
        chamfer = trimesh.creation.cone(radius=3.0, height=1.2, sections=64)
        chamfer.apply_transform(trimesh.transformations.rotation_matrix(np.pi, (1, 0, 0)))
        drains.append(moved(chamfer, (phone_center_x + dx, 0, platform_h + phone_floor)))
    solid = trimesh.boolean.difference([solid, *drains], engine="manifold")

    # Manifold may retain zero-area triangles along coincident primitive seams.
    # Removing them before export preserves the same shape and closes STL edges.
    solid.update_faces(solid.nondegenerate_faces())
    solid.merge_vertices()
    solid.remove_unreferenced_vertices()
    output = Path(__file__).with_name("Model4_SUP_phone_cup_holder.stl")
    solid.export(output)
    print(f"Wrote {output.name}")
    print(f"vertices={len(solid.vertices)} faces={len(solid.faces)}")
    print(f"watertight={solid.is_watertight} volume_mm3={solid.volume:.1f}")
    print(f"bounds_mm={np.round(solid.bounds, 2).tolist()}")


if __name__ == "__main__":
    main()
