"""
Convert FBX model to GLB for Three.js
=======================================
Usage in Blender:
1. Open Blender > Scripting tab
2. Paste this script
3. Update paths if needed
4. Run Script (Alt+P)

The script imports an FBX file and exports as GLB with:
- Dense morph targets (no sparse accessors)
- Proper material conversion
- Correct scaling and orientation
"""

import bpy
import sys
import os

INPUT_PATH = r"D:\projectiqram\AI\AI-Interview-Agent\frontend\public\models\model.fbx"
OUTPUT_PATH = r"D:\projectiqram\AI\AI-Interview-Agent\frontend\public\models\avatar.glb"

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)

def main():
    print("\n" + "=" * 60)
    print("FBX to GLB Converter")
    print("=" * 60)

    print("\n[1/4] Clearing scene...")
    clear_scene()

    print(f"\n[2/4] Importing FBX: {INPUT_PATH}")
    bpy.ops.import_scene.fbx(filepath=INPUT_PATH)

    obj = None
    for o in bpy.context.selected_objects:
        if o.type == 'MESH':
            obj = o
            break
    if not obj:
        for o in bpy.data.objects:
            if o.type == 'MESH':
                obj = o
                break

    if not obj:
        print("ERROR: No mesh found in FBX!")
        return

    print(f"  Imported: {obj.name}")
    print(f"  Vertices: {len(obj.data.vertices)}")
    print(f"  Faces: {len(obj.data.polygons)}")
    
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Check for existing shape keys
    if obj.data.shape_keys:
        print(f"  Shape keys found: {len(obj.data.shape_keys.key_blocks)}")
        for kb in obj.data.shape_keys.key_blocks:
            print(f"    - {kb.name}")
    else:
        print("  No shape keys found on this model.")
        print("  You can:")
        print("  1. Use the model as-is (no facial animation)")
        print("  2. Run create_shapekeys.py after this conversion")

    # Force dense morph targets by ensuring every vertex has at least epsilon delta
    if obj.data.shape_keys:
        basis = obj.data.shape_keys.key_blocks[0]
        for kb in obj.data.shape_keys.key_blocks[1:]:
            for i, v in enumerate(obj.data.vertices):
                co = kb.data[i].co
                bc = basis.data[i].co
                if (co - bc).length < 0.00001:
                    kb.data[i].co = co + bpy.mathutils.Vector((0.00001, 0, 0))

    print(f"\n[3/4] Exporting GLB: {OUTPUT_PATH}")
    bpy.ops.export_scene.gltf(
        filepath=OUTPUT_PATH,
        export_format='GLB',
        export_morph=True,
        export_normals=True,
        export_materials='EXPORT',
        export_apply=True,
    )

    print(f"\n[4/4] Done!")
    print(f"  Output: {OUTPUT_PATH}")
    print(f"  Copy to frontend/public/models/avatar.glb and refresh the browser.")
    print("=" * 60)

if __name__ == "__main__":
    main()
