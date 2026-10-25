"""Analytical seam-vertex identification for a sewn cloth mesh (read-only).

Union paired vertices *by identity*, preserving the original Blender Cloth
output unchanged. Boundary/nonmanifold/orientation/Euler/volume are computed
on the hypothetical welded polygon mesh. This is NOT a proof of self-contact
freedom, safe seams, real fabric, or a physically welded Blender object.
"""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np


def _validated_inputs(vertices, faces, sewing_pairs, max_vertices):
    xyz=np.asarray(vertices,dtype=np.float64)
    if xyz.ndim!=2 or xyz.shape[1]!=3 or not np.isfinite(xyz).all():
        raise ValueError("vertices must be finite 3D positions")
    n=len(xyz)
    if not 4<=n<=max_vertices:
        raise ValueError("Out-of-bounds vertex count")
    ff=np.asarray(faces)
    if ff.ndim!=2 or ff.shape[1] not in (3,4) or not np.issubdtype(ff.dtype,np.integer):
        raise ValueError("faces must be triangle or quad integer indices")
    if len(ff)==0 or (ff<0).any() or (ff>=n).any():
        raise ValueError("Faces missing or out of range")
    if len(sewing_pairs)==0:
        pairs=np.empty((0,2),dtype=np.int64)
    else:
        pairs=np.asarray(sewing_pairs)
        if pairs.ndim!=2 or pairs.shape[1]!=2 or not np.issubdtype(pairs.dtype,np.integer):
            raise ValueError("Sewing identities must be integer edge pairs")
        if (pairs<0).any() or (pairs>=n).any() or (pairs[:,0]==pairs[:,1]).any():
            raise ValueError("Invalid sewing pair indexes")
        pairs=pairs.astype(np.int64,copy=False)
    ff=ff.astype(np.int64,copy=False)

    return xyz, ff, pairs


def inspect_welded_shell(vertices, faces, sewing_pairs, *, max_vertices=12000):
    xyz, ff, pairs = _validated_inputs(vertices, faces, sewing_pairs, max_vertices)
    n = len(xyz)
    parent=np.arange(n,dtype=np.int64)
    size=np.ones(n,dtype=np.int64)
    def root(x):
        x=int(x)
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=int(parent[x])
        return x
    for u,v in pairs:
        a,b=root(u),root(v)
        if a!=b:
            if size[a]<size[b]:a,b=b,a
            parent[b]=a
            size[a]+=size[b]
    remapped=np.asarray([root(i) for i in range(n)],dtype=np.int64)
    faces_after=remapped[ff]

    degenerate=int(sum(len(set(f.tolist()))!=len(f) for f in faces_after))
    edge_occurrence=Counter()
    directed=defaultdict(Counter)
    graph=defaultdict(set)
    for f in faces_after:
        if len(set(f.tolist()))!=len(f):
            continue
        for u,v in zip(f,np.roll(f,-1)):
            u,v=int(u),int(v)
            key=(min(u,v),max(u,v))
            edge_occurrence[key]+=1
            directed[key][(u,v)]+=1
            graph[u].add(v)
            graph[v].add(u)
    boundary=sum(count==1 for count in edge_occurrence.values())
    overfull=sum(count>2 for count in edge_occurrence.values())
    orientation_bad=sum(
        count==2 and (dir_counts.get((a,b),0)!=1 or dir_counts.get((b,a),0)!=1)
        for (a,b),count in edge_occurrence.items()
        for dir_counts in (directed[(a,b)],)
    )
    # Include isolated vertices in connectivity, since they make a mesh
    # unsuitable for a watertight shell even if all its used faces are fine.
    active=set(int(x) for x in np.unique(faces_after))
    unseen=active.copy()
    components=[]
    while unseen:
        start=unseen.pop()
        stack=[start]
        count=0
        while stack:
            at=stack.pop();count+=1
            adjacent=graph.get(at,())
            for other in adjacent:
                if other in unseen:
                    unseen.remove(other)
                    stack.append(other)
        components.append(count)
    # Conservatively report all collapsed equivalence classes as coordinates
    # of representative root vertices. This is a topological construction:
    # physical seam endpoints may still be separated by non-zero gaps.
    roots=set(int(x) for x in np.unique(remapped))
    unused_roots=roots-active

    # Volume on remapped reference coordinates is diagnostic only. Mean
    # endpoint coordinates reduce spurious volume dependence on union order.
    averaged=np.zeros((n,3),dtype=np.float64)
    counts=np.zeros(n,dtype=np.int64)
    np.add.at(averaged,remapped,xyz)
    np.add.at(counts,remapped,1)
    averaged[np.asarray(list(roots))] /= counts[np.asarray(list(roots)),None]
    signed_volume=0.0
    for f in faces_after:
        if len(set(f.tolist()))!=len(f):
            continue
        a=averaged[f[0]]
        for i in range(1,len(f)-1):
            b=averaged[f[i]]
            c=averaged[f[i+1]]
            signed_volume+=float(np.dot(a,np.cross(b,c))/6.0)
    max_distance_m=float(np.max(np.linalg.norm(
        xyz[pairs[:,0]]-xyz[pairs[:,1]],axis=1))) if len(pairs) else 0.0
    vcount=len(active)
    ecount=len(edge_occurrence)
    fcount=len(ff)-degenerate
    euler=vcount-ecount+fcount
    topological_closure=bool(
        boundary==0 and overfull==0 and orientation_bad==0
        and degenerate==0 and len(unused_roots)==0
        and len(components)==1 and euler==2 and signed_volume>0
    )
    return {
        "status":"ANALYTICAL_WELDED_PROXY_NOT_A_PHYSICAL_CLOTH_SHELL",
        "source_vertices":n,
        "source_faces":len(ff),
        "sewing_pairs_count":len(pairs),
        "identified_vertex_classes":len(roots),
        "used_welded_vertices":vcount,
        "unused_vertex_classes":len(unused_roots),
        "boundary_edges":boundary,
        "nonmanifold_edges_over_two_faces":overfull,
        "inconsistent_edge_winding":orientation_bad,
        "faces_collapsed_by_weld":degenerate,
        "connected_components":len(components),
        "component_vertices":sorted(components,reverse=True),
        "euler_characteristic":euler,
        "signed_volume_l":signed_volume*1000,
        "max_pair_gap_mm":max_distance_m*1000,
        "research_topological_sphere_screen_pass":topological_closure,
        "limitations":[
            "Sewing identities merged analytically; original Cloth scene unchanged",
            "No checks for self-intersections or collisions of nonadjacent faces",
            "No seam strength, filling constitutive law or verified manufactured toy",
            "Surface volume assumes locally planar polygon triangulation",
        ],
    }
