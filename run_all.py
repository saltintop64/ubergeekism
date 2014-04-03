#!/usr/bin/env python

import sys
import turtle
import argparse
import matplotlib.pyplot as plot
from itertools import ifilterfalse as filter_if_not

import ants
import utils
from utils import LOG,LOGN
import hull
import uberplot
import shortpath
import lindenmayer
import triangulation

parser = argparse.ArgumentParser()

parser.add_argument('-p', "--penrose", help="Do not compute the Penrose tiling but load it from a file",
        default=None, action='store', type=str, metavar="SEGMENTS")
parser.add_argument( '-d', '--depth', help="Recursive depth of the Lindenmayer computations = size of the Penrose tiling",
        default=1, type=int, metavar="DEPTH")

parser.add_argument('-t', "--notsp", help="Do not compute the TSP",
        default=False, action='store_true')
parser.add_argument('-r', "--tour", help="Load several TSP tour from a file",
        default=[None], action='store', type=str, nargs="*", metavar="POINTS")
parser.add_argument('-m', "--pheromones", help="Load a pheromones matrix from a file",
        default=None, action='store', type=str, metavar="MATRIX")

parser.add_argument('-g', "--triangulation", help="Do not compute the Delaunay triangulation but load it from a file",
        default=None, action='store', type=str, metavar="SEGMENTS")

args = parser.parse_args()


error_codes = {"NOTSP":100}

depth = args.depth
LOGN( "depth",depth )

########################################################################
# PENROSE TILING
########################################################################

penrose_segments = set()

if args.penrose:
    LOGN( "Load the penrose tiling" )
    penrose_segments = utils.load_segments(args.penrose)

else:
    LOGN( "Draw the penrose tiling" )


    segment_size = 10
    float_rounding = 10

    ttl = turtle.Turtle()
    ttl.speed('fastest')
    penrose = lindenmayer.DumpTurtleLSystem(ttl, 
            axiom="[X]++[X]++[X]++[X]++[X]", 
            rules={
                'F': "",
                'W': "YF++ZF----XF[-YF----WF]++",
                'X': "+YF--ZF[---WF--XF]+",
                'Y': "-WF++XF[+++YF++ZF]-",
                'Z': "--YF++++WF[+ZF++++XF]--XF"
            }, 
            angle=36, heading=0, size=segment_size, rounding=float_rounding )

    # actually do something
    penrose.draw( depth )

    # save this intermediate step
    LOGN( "\tsegments",len(penrose.segments) )
    with open("d%i_penrose.segments" % depth, "w") as fd:
        fd.write( str(penrose) )

    penrose_segments = penrose.segments


########################################################################
# TSP
########################################################################

trajs = []

if args.tour != [None]:
    for tour in args.tour:
        trajs.append( utils.load_points(tour) )

if args.notsp:
    if args.tour == [None] or not args.pheromones:
        LOGN( "If you do not want to solve the TSP, you must provide a solution tour (--tour) and a pheromones matrix (--pheromones)" )
        sys.exit(error_codes["NO-TSP"])

    if args.pheromones:
        phero = utils.load_matrix(args.pheromones)

else:
    LOGN( "Solve the TSP with an Ant Colony Algorithm" )

    LOGN( "\tConvert the segment list into an adjacency list graph" )
    G = utils.adjacency_from_set( penrose_segments )

    LOGN( "\tCompute a tour" )
    max_it = 10
    num_ants = 10 #* depth
    decay = 0.1
    w_heur = 2.5
    w_local_phero = 0.1
    c_greed = 0.9
    w_history = 1.0

    best,phero = ants.search( G, max_it, num_ants, decay, w_heur, w_local_phero, w_history, c_greed, cost_func = ants.graph_distance )

    LOGN( "\tTransform the resulting nodes permutation into a path on the graph" )
    # by finding the shortest path between two cities.
    traj = []
    for start,end in utils.tour(best["permutation"]):
        p,c = shortpath.astar( G, start, end )
        traj += p
    trajs.append(traj)

    with open("d%i_tour.points" % depth, "w") as fd:
        for p in traj:
            fd.write("%f %f\n" % p)
    with open("d%i_pheromones.mat" % depth, "w") as fd:
        for row in phero:
            key = "%f,%f:" % row
            line = key
            for k in phero[row]:
                val = phero[row][k]
                line += "%f,%f=%f " % (k[0],k[1],val)
            fd.write( line + "\n" )


########################################################################
# TRIANGULATION
########################################################################

if args.triangulation:
    triangulation_edges = utils.load_segments(args.triangulation)

else:
    LOGN( "Compute the triangulation of the penrose vertices" )
    points = utils.vertices_from_set(penrose_segments)
    triangles = triangulation.delaunay_bowyer_watson( points, do_plot = False )

    LOGN( "\tCompute the convex hull of",len(points),"points" )
    # Should convert the set into a list
    hull = hull.convex_hull( list(points) )
    hull_edges = list(utils.tour(hull))
    LOGN( "\t\tHull of",len(hull_edges),"edges" )

    LOGN( "\tRemove triangles that have at least one edge in common with the convex hull" )
    def adjoin_hull(triangle):
        for (p,q) in utils.tour(list(triangle)):
            if (p,q) in hull_edges or (q,p) in hull_edges:
                return True
        return False

    # Filter out edges that are in hull_edges
    triangulated = list(filter_if_not( adjoin_hull, triangles ))
    LOGN( "\t\tRemoved", len(triangles)-len(triangulated), "triangles" )

    triangulation_edges = triangulation.edges_of( triangulated )
    with open("d%i_triangulation.segments" % depth, "w") as fd:
        for p0,p1 in triangulation_edges:
            fd.write("%f %f %f %f\n" % (p0[0],p0[1],p1[0],p1[1]) )


########################################################################
# PLOT
########################################################################

LOGN( "Plot the resulting tour" )
fig = plot.figure()
ax = fig.add_subplot(111)

LOGN( "\tpheromones",len(phero) )#,"x",len(phero[traj[0]]) )
maxph=0
for i in phero:
    maxph = max( maxph, max(phero[i].values()))

# ant colony
# pheromones
for i in phero:
    for j in phero[i]:
        if i == j:
            continue
        nph = phero[i][j]/maxph
        seg = [(i,j)]
        # LOGN( nph,seg )
        uberplot.plot_segments( ax, seg, edgecolor="blue", alpha=0.01*nph, linewidth=1*nph )
        # uberplot.scatter_segments( ax, seg, color="red", alpha=0.5, linewidth=nph )

for traj in trajs:
    LOGN( "\ttraj",len(traj) )
    # best tour
    uberplot.plot_segments( ax, utils.tour(traj), edgecolor="red",  alpha=0.9, linewidth=3 )

LOGN( "\ttiling",len(penrose_segments) )
tcol = "black"
uberplot.plot_segments( ax, penrose_segments, edgecolor=tcol, alpha=0.9, linewidth=2 )
uberplot.scatter_segments( ax, penrose_segments, edgecolor=tcol, alpha=0.9, linewidth=1 )

# triangulation
uberplot.plot_segments( ax, triangulation_edges, edgecolor="green", alpha=0.2, linewidth=1 )

ax.set_aspect('equal')

plot.show()

