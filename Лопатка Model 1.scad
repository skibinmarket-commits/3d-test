// 90 mm carved-branch scoop. The Python generator adds printable bark/grain
// displacement and creates the separate breakaway lattice support STL.
$fn=128;

outer_pts=[[-10.5,0],[-12.5,2.5],[-12.6,19.5],[-11.5,25.5],[-8.8,32],[-5,40.5],
           [5,40.5],[8.8,32],[11.5,25.5],[12.6,19.5],[12.5,2.5],[10.5,0]];
inner_pts=[[-7.6,3],[-9.4,4.5],[-9.4,19],[-8.2,24],[-5.2,31.5],[-3.8,35],
           [3.8,35],[5.2,31.5],[8.2,24],[9.4,19],[9.4,4.5],[7.6,3]];

module outline_layer(points,s,z,cy) {
    translate([0,0,z]) linear_extrude(0.02)
        translate([0,cy]) scale([s,s]) translate([0,-cy]) polygon(points);
}

module outer_volume() {
    hull() { outline_layer(outer_pts,0.8,-6,20.5); outline_layer(outer_pts,1,-1.5,20.5); }
    hull() { outline_layer(outer_pts,1,-1.5,20.5); outline_layer(outer_pts,1,1,20.5); }
    hull() { outline_layer(outer_pts,1,1,20.5); outline_layer(outer_pts,0.84,4.5,20.5); }
}

module inner_volume() {
    hull() { outline_layer(inner_pts,0.56,-3,19.25); outline_layer(inner_pts,0.93,1,19.25); }
    hull() { outline_layer(inner_pts,0.93,1,19.25); outline_layer(inner_pts,1.07,7.2,19.25); }
}

// Open working mouth: a continuous ramp from the original bowl floor to a
// thin, flat leading edge.  Side walls remain, but taper down at the nose.
module open_leading_edge_cutter() {
    polyhedron(
        points=[
            [-14,-3,-0.55],[14,-3,-0.55],[-14,-3,10],[14,-3,10],
            [-13.2,0,-0.72],[13.2,0,-0.72],[-13.2,0,10],[13.2,0,10],
            [-12.3,2.5,-1.62],[12.3,2.5,-1.62],[-12.3,2.5,10],[12.3,2.5,10],
            [-10.9,5.5,-2.48],[10.9,5.5,-2.48],[-10.9,5.5,10],[10.9,5.5,10],
            [-9.5,9,-3.02],[9.5,9,-3.02],[-9.5,9,10],[9.5,9,10]
        ],
        faces=[
            [0,1,3,2],
            [0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3],
            [4,8,9,5],[6,7,11,10],[4,6,10,8],[5,9,11,7],
            [8,12,13,9],[10,11,15,14],[8,10,14,12],[9,13,15,11],
            [12,16,17,13],[14,15,19,18],[12,14,18,16],[13,17,19,15],
            [16,18,19,17]
        ], convexity=10
    );
}

module branch(points,radii) {
    for(i=[0:len(points)-2]) hull() {
        translate(points[i]) sphere(radii[i]);
        translate(points[i+1]) sphere(radii[i+1]);
    }
}

module handle() {
    branch([[0,35.5,0],[0.8,45,1],[-0.9,56,0.3],[0.6,66,1.2],[0,76,0.5],[0.8,85.1,0.8]],
           [5.4,5.2,5,4.8,4.7,4.9]);
}

module rope_helix() {
    turns=3.6; steps=160;
    for(i=[0:steps-1]) hull() {
        for(j=[i,i+1]) {
            a=360*turns*j/steps;
            y=37+6*j/steps;
            translate([0.2+5.55*cos(a),y,0.3+5.55*sin(a)]) sphere(0.58);
        }
    }
}

module core_model() {
    difference() {
        union() {
            difference() { outer_volume(); inner_volume(); }
            handle();
            branch([[0.2,68,1],[-4.8,73,1.3],[-7.4,75.5,1]],[2.8,2.2,1.55]);
            branch([[0.2,52,0.6],[4.3,56.2,1.2],[6.8,58.6,1]],[2.5,1.9,1.4]);
            rope_helix();
        }
        inner_volume();
        open_leading_edge_cutter();
    }
}

core_model();
