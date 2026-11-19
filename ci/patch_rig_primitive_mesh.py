from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text()
old='''        for surf in source_mesh.get_surface_count():
            if source_mesh.surface_get_primitive_type(surf) != Mesh.PRIMITIVE_TRIANGLES:
                continue
            var arrays: Array = source_mesh.surface_get_arrays(surf)
'''
new='''        for surf in source_mesh.get_surface_count():
            # surface_get_primitive_type exists only on ArrayMesh, NOT Mesh/PrimitiveMesh.
            # CapsuleMesh, SphereMesh, etc. generate triangular surfaces themselves.
            if source_mesh is ArrayMesh:
                var array_source: ArrayMesh = source_mesh as ArrayMesh
                if array_source.surface_get_primitive_type(surf) != Mesh.PRIMITIVE_TRIANGLES:
                    continue
            var arrays: Array = source_mesh.surface_get_arrays(surf)
'''
assert s.count(old)==1
p.write_text(s.replace(old,new,1))
print("Patched PrimitiveMesh and ArrayMesh handling")
