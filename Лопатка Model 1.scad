// 60 mm support-free miniature scoop with a branch-shaped handle.
// Print flat back down, cavity facing up. All dimensions are millimetres.
$fn = 96;

module path_hull(points, r, h) {
    linear_extrude(h)
        hull() for (p=points) translate(p) circle(r=r);
}

module scoop_body() {
    linear_extrude(6)
        polygon([
            [-6.8,0],[-7.6,0.5],[-8,2],[-8,12],[-7.5,16],[-6,20],
            [-4.2,24],[-3.4,26],[3.4,26],[4.2,24],[6,20],[7.5,16],
            [8,12],[8,2],[7.6,0.5],[6.8,0]
        ]);
}

module cavity() {
    translate([0,0,2]) linear_extrude(5)
        polygon([
            [-5,2],[-5.8,3],[-5.8,12],[-5.2,15.5],[-3.8,19],[-2.6,22],
            [2.6,22],[3.8,19],[5.2,15.5],[5.8,12],[5.8,3],[5,2]
        ]);
}

module model() {
    difference() {
        union() {
            scoop_body();
            path_hull([[0,23],[0.4,30],[-0.6,38],[0.2,46],[0.9,53],[0.3,56.7]],3.3,6);
            translate([0,0,0.2]) path_hull([[-0.3,44],[-4.7,49]],1.55,5.5);
            translate([0,0,0.2]) path_hull([[0,35],[4.2,39]],1.45,5.3);
            for (y=[25,26.4,27.8])
                translate([0,y,5.8]) rotate([0,90,0]) cylinder(r=0.58,h=8.5,center=true);
            for (k=[[-0.8,33,1],[0.9,42,0.9],[-0.5,52,0.85]])
                translate([k[0],k[1],6]) cylinder(r=k[2],h=0.7);
        }
        cavity();
    }
}

model();
