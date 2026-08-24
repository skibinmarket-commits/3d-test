// 100 mm cube with a centered through-hole, diameter 50 mm
size = 100;          // mm
hole_diameter = 50;  // mm
$fn = 96;

difference() {
    cube([size, size, size], center=false);
    translate([size/2, size/2, -1])
        cylinder(h=size + 2, d=hole_diameter, center=false);
}
