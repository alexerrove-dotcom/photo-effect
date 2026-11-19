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
s=s.replace(old,new,1)
old_tangent='''            # Tangents in the old object space would no longer be correct after baking.
            arrays[Mesh.ARRAY_TANGENT] = PackedFloat32Array()
'''
new_tangent='''            # Godot requires a missing tangent attribute to be null, not a zero-length
            # PackedFloat32Array (which is treated as an invalid enabled tangent format).
            arrays[Mesh.ARRAY_TANGENT] = null
'''
assert s.count(old_tangent)==1
s=s.replace(old_tangent,new_tangent,1)
p.write_text(s)
print("Patched PrimitiveMesh and ArrayMesh handling")
