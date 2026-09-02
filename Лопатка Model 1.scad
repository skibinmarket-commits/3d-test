// Sculptural 60 mm miniature scoop inspired by a carved branch.
// The Python generator adds fine printable bark and bowl grain to the STL.
$fn=96;

module ellipsoid(size,pos) { translate(pos) scale(size) sphere(1); }

module twig() {
    pts=[[0,23.5,0.1],[0.5,30,0.8],[-0.6,37,0.2],[0.4,44,0.9],[0,51,0.5],[0.6,56.7,0.8]];
    rs=[3.75,3.55,3.35,3.25,3.15,3.3];
    for(i=[0:len(pts)-2]) hull() {
        translate(pts[i]) sphere(rs[i]);
        translate(pts[i+1]) sphere(rs[i+1]);
    }
}

module branch(points,radii) {
    for(i=[0:len(points)-2]) hull() {
        translate(points[i]) sphere(radii[i]);
        translate(points[i+1]) sphere(radii[i+1]);
    }
}

module torus_y(R,r,pos) {
    translate(pos) rotate([90,0,0]) rotate_extrude()
        translate([R,0]) circle(r);
}

outer_pts=[[-7,0],[-8,2],[-8,13],[-7.4,17],[-5.8,21.5],[-3.5,27],
           [3.5,27],[5.8,21.5],[7.4,17],[8,13],[8,2],[7,0]];
inner_pts=[[-5.2,2],[-6,3],[-6,13],[-5.2,16.5],[-3.4,21],[-2.6,23.5],
           [2.6,23.5],[3.4,21],[5.2,16.5],[6,13],[6,3],[5.2,2]];

module outline_layer(points,s,z,cy) {
    translate([0,0,z]) linear_extrude(0.02)
        translate([0,cy]) scale([s,s]) translate([0,-cy]) polygon(points);
}

module outer_volume() {
    hull() { outline_layer(outer_pts,0.78,-5.3,13.75); outline_layer(outer_pts,1,-1,13.75); }
    hull() { outline_layer(outer_pts,1,-1,13.75); outline_layer(outer_pts,1,1.5,13.75); }
    hull() { outline_layer(outer_pts,1,1.5,13.75); outline_layer(outer_pts,0.82,5,13.75); }
}

module inner_volume() {
    hull() { outline_layer(inner_pts,0.55,-2.25,12.75); outline_layer(inner_pts,0.92,1,12.75); }
    hull() { outline_layer(inner_pts,0.92,1,12.75); outline_layer(inner_pts,1.08,7,12.75); }
}

module scoop_shell() { difference() { outer_volume(); inner_volume(); } }

difference() {
    union() {
        scoop_shell();
        twig();
        branch([[-0.1,45,0.7],[-3.3,48.3,0.8],[-5.1,50,0.6]],[1.8,1.45,1.05]);
        branch([[0.1,35,0.4],[3,38,0.8],[4.6,39.5,0.7]],[1.65,1.3,0.95]);
        for(i=[0:3]) torus_y(3.90-0.06*i,0.45,[0.15,25.3+1.05*i,0.15]);
    }
    inner_volume();
}
