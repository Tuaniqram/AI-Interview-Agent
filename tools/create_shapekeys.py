"""
Avatar Shape Key Generator for Blender
========================================
Creates facial morph targets (shape keys) on a GLB/GLTF mesh automatically.
Designed for Meshy-generated humanoid avatars with no existing shape keys.

HOW TO USE:
1. Open Blender
2. Go to the "Scripting" tab (top menu bar)
3. Click "New" to create a new text block
4. Paste this entire script
5. Change INPUT_PATH and OUTPUT_PATH below to your file paths
6. Click "Run Script" (play button) or press Alt+P

The script will import your GLB, create all shape keys, and export a new GLB.
"""

import bpy
import bmesh
import math
from mathutils import Vector, kdtree

# ============================================================
# CONFIGURATION — Change these paths
# ============================================================
INPUT_PATH = r"D:\projectiqram\AI\AI-Interview-Agent\frontend\public\models\avatar.glb"
OUTPUT_PATH = r"D:\projectiqram\AI\AI-Interview-Agent\frontend\public\models\avatar.glb"

# Deformation strength (adjust if shapes look too strong/weak)
DEFORM = {
    "jawOpen":        0.12,
    "mouthOpen":      0.10,
    "mouthSmile":     0.08,
    "mouthPucker":    0.06,
    "mouthFunnel":    0.06,
    "mouthClose":     0.04,
    "eyeBlinkLeft":   0.08,
    "eyeBlinkRight":  0.08,
    "browInnerUp":    0.06,
    "browDownLeft":   0.05,
    "browDownRight":  0.05,
    "smileLeft":      0.06,
    "smileRight":     0.06,
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clear_scene():
    """Remove all objects from the scene."""
    # Check if there's already a mesh we can reuse
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            return  # Don't clear — reuse existing mesh
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat)


def import_glb(filepath):
    """Import a GLB file and return the first mesh object. Uses existing if available."""
    # Check if there's already a mesh in the scene
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            print(f"  Found existing mesh: {obj.name}")
            return obj
    
    # No mesh found, import
    bpy.ops.import_scene.gltf(filepath=filepath)
    obj = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def get_vertex_data(obj):
    """Get all vertex positions and normals from a mesh object."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    
    positions = [v.co.copy() for v in bm.verts]
    normals = [v.normal.copy() for v in bm.verts]
    
    bm.free()
    return positions, normals


def compute_bounds(positions):
    """Compute bounding box from a list of Vectors."""
    xs = [p.x for p in positions]
    ys = [p.y for p in positions]
    zs = [p.z for p in positions]
    return {
        'min_x': min(xs), 'max_x': max(xs),
        'min_y': min(ys), 'max_y': max(ys),
        'min_z': min(zs), 'max_z': max(zs),
        'center_x': (min(xs) + max(xs)) / 2,
        'center_y': (min(ys) + max(ys)) / 2,
        'center_z': (min(zs) + max(zs)) / 2,
        'width': max(xs) - min(xs),
        'height': max(ys) - min(ys),
        'depth': max(zs) - min(zs),
    }


def compute_head_region(positions, normals, body_bounds):
    """
    Identify the head/face region within the full body mesh.
    Strategy:
    1. Head is in the upper portion of the body (Y > 40% of height)
    2. Front-facing normals indicate the face side
    3. Compute head bounding box from filtered vertices
    """
    # Find the head: upper 50% of body, front-facing
    y_threshold = body_bounds['min_y'] + body_bounds['height'] * 0.45
    
    head_positions = []
    head_indices = []
    
    for i, (pos, norm) in enumerate(zip(positions, normals)):
        if pos.y > y_threshold:
            head_positions.append(pos)
            head_indices.append(i)
    
    if not head_positions:
        print("WARNING: No head vertices found, using top 40% of all vertices")
        for i, pos in enumerate(positions):
            if pos.y > body_bounds['min_y'] + body_bounds['height'] * 0.6:
                head_positions.append(pos)
                head_indices.append(i)
    
    head_bounds = compute_bounds(head_positions)
    
    # Determine which Z direction is "front" (face direction)
    # Count front-facing vertices on each side
    front_count = 0
    back_count = 0
    for pos in head_positions:
        z_ratio = (pos.z - head_bounds['min_z']) / max(head_bounds['depth'], 0.001)
        if z_ratio > 0.5:
            front_count += 1
        else:
            back_count += 1
    
    face_z_direction = 1.0 if front_count >= back_count else -1.0
    
    print(f"Head bounds: Y [{head_bounds['min_y']:.3f} to {head_bounds['max_y']:.3f}]")
    print(f"Head bounds: Z [{head_bounds['min_z']:.3f} to {head_bounds['max_z']:.3f}]")
    print(f"Face Z direction: {'positive' if face_z_direction > 0 else 'negative'}")
    print(f"Head vertices: {len(head_positions)}")
    
    return head_indices, head_bounds, face_z_direction


def is_face_vertex(pos, head_bounds, face_z_direction, margin=0.15):
    """
    Check if a vertex is on the front of the face.
    Uses both position and requires it to be in the front half of the head.
    """
    hw = head_bounds['width']
    hh = head_bounds['height']
    hd = head_bounds['depth']
    
    # X within head bounds (with some margin)
    if abs(pos.x - head_bounds['center_x']) > hw * (0.5 + margin):
        return False
    
    # Y within head bounds
    if pos.y < head_bounds['min_y'] - hh * margin or pos.y > head_bounds['max_y'] + hh * margin:
        return False
    
    # Z: front-facing side
    if face_z_direction > 0:
        z_thresh = head_bounds['center_z'] - hd * 0.05
        return pos.z > z_thresh
    else:
        z_thresh = head_bounds['center_z'] + hd * 0.05
        return pos.z < z_thresh


def get_face_ratio(pos, head_bounds):
    """Get normalized ratios for a vertex within the head bounding box."""
    x_ratio = (pos.x - head_bounds['min_x']) / max(head_bounds['width'], 0.001)
    y_ratio = (pos.y - head_bounds['min_y']) / max(head_bounds['height'], 0.001)
    z_ratio = (pos.z - head_bounds['min_z']) / max(head_bounds['depth'], 0.001)
    return x_ratio, y_ratio, z_ratio


def smooth_weight(distance, radius):
    """
    Smooth falloff weight based on distance from center.
    Returns 1.0 at center, 0.0 at radius, smooth interpolation.
    """
    t = max(0.0, 1.0 - distance / radius)
    return t * t * (3.0 - 2.0 * t)  # smoothstep


def classify_vertex(x_ratio, y_ratio, z_ratio, face_z_dir):
    """
    Classify a face vertex into a facial feature region.
    Returns a dict of {feature_name: weight} for each feature.
    All ratios are 0-1 within the head bounding box.
    """
    regions = {}
    
    # Center X (0.5 = middle of face)
    cx = 0.5
    cy = 0.5
    x_dist_from_center = abs(x_ratio - cx)
    left_side = x_ratio < cx  # True = left side of face (viewer's right in Blender)
    right_side = x_ratio > cx
    
    # --- JAW / CHIN: bottom 25% of face, front ---
    if y_ratio < 0.25 and z_ratio > 0.4:
        jaw_w = smooth_weight(y_ratio, 0.25) * smooth_weight(abs(z_ratio - 0.7), 0.4)
        regions['jaw'] = jaw_w
    
    # --- MOUTH: rows 25-45% of face, center, front ---
    if 0.20 < y_ratio < 0.45 and x_dist_from_center < 0.25 and z_ratio > 0.5:
        mouth_y_w = smooth_weight(abs(y_ratio - 0.32), 0.15)
        mouth_x_w = smooth_weight(x_dist_from_center, 0.25)
        mouth_z_w = smooth_weight(abs(z_ratio - 0.75), 0.3)
        regions['mouth'] = mouth_y_w * mouth_x_w * mouth_z_w
        
        # Mouth corners (for smile)
        if x_dist_from_center > 0.12:
            corner_w = smooth_weight(abs(x_dist_from_center - 0.18), 0.1)
            regions['mouth_corner'] = corner_w * mouth_y_w * mouth_z_w
        
        # Lips (for pucker/funnel) - more central
        if x_dist_from_center < 0.15:
            lip_w = smooth_weight(x_dist_from_center, 0.15)
            regions['lips'] = lip_w * mouth_y_w * mouth_z_w
    
    # --- EYES: rows 50-65% of face ---
    if 0.45 < y_ratio < 0.68 and z_ratio > 0.45:
        eye_y_w = smooth_weight(abs(y_ratio - 0.57), 0.12)
        eye_z_w = smooth_weight(abs(z_ratio - 0.75), 0.3)
        
        # Left eye: x < 0.4
        if left_side and x_ratio < 0.42:
            eye_x_w = smooth_weight(abs(x_ratio - 0.3), 0.15)
            regions['eye_left'] = eye_y_w * eye_x_w * eye_z_w
        
        # Right eye: x > 0.6
        if right_side and x_ratio > 0.58:
            eye_x_w = smooth_weight(abs(x_ratio - 0.7), 0.15)
            regions['eye_right'] = eye_y_w * eye_x_w * eye_z_w
    
    # --- EYEBROWS: rows 65-80% of face ---
    if 0.62 < y_ratio < 0.82 and z_ratio > 0.45:
        brow_y_w = smooth_weight(abs(y_ratio - 0.72), 0.1)
        brow_z_w = smooth_weight(abs(z_ratio - 0.75), 0.3)
        
        # Inner brows (closer to center)
        if x_dist_from_center < 0.22:
            inner_w = smooth_weight(abs(x_dist_from_center - 0.1), 0.15)
            regions['brow_inner'] = brow_y_w * inner_w * brow_z_w
        
        # Left brow
        if left_side and x_ratio < 0.42:
            brow_x_w = smooth_weight(abs(x_ratio - 0.28), 0.18)
            regions['brow_left'] = brow_y_w * brow_x_w * brow_z_w
        
        # Right brow
        if right_side and x_ratio > 0.58:
            brow_x_w = smooth_weight(abs(x_ratio - 0.72), 0.18)
            regions['brow_right'] = brow_y_w * brow_x_w * brow_z_w
    
    # --- CHEEKS: rows 30-55%, sides ---
    if 0.30 < y_ratio < 0.55 and x_dist_from_center > 0.15 and z_ratio > 0.4:
        cheek_y_w = smooth_weight(abs(y_ratio - 0.42), 0.15)
        cheek_z_w = smooth_weight(abs(z_ratio - 0.7), 0.3)
        
        if left_side:
            cheek_x_w = smooth_weight(abs(x_ratio - 0.2), 0.2)
            regions['cheek_left'] = cheek_y_w * cheek_x_w * cheek_z_w
        if right_side:
            cheek_x_w = smooth_weight(abs(x_ratio - 0.8), 0.2)
            regions['cheek_right'] = cheek_y_w * cheek_x_w * cheek_z_w
    
    return regions


def create_shape_key_deformation(obj, name, positions, normals, head_indices, 
                                  head_bounds, face_z_dir, deform_func):
    """
    Create a shape key by applying deform_func to qualifying vertices.
    Forces EVERY vertex to have at least an epsilon delta so the GLTF exporter
    uses dense (not sparse) accessors — Three.js can't decode sparse morph targets.
    
    deform_func(pos, x_ratio, y_ratio, z_ratio, regions) -> Vector offset or None
    """
    sk = obj.shape_key_add(name=name, from_mix=False)
    
    head_set = set(head_indices)
    EPSILON = 0.00001
    
    for i, (pos, norm) in enumerate(zip(positions, normals)):
        if i not in head_set:
            sk.data[i].co = pos + Vector((EPSILON, 0, 0))
            continue
        
        if not is_face_vertex(pos, head_bounds, face_z_dir):
            sk.data[i].co = pos + Vector((0, EPSILON, 0))
            continue
        
        x_ratio, y_ratio, z_ratio = get_face_ratio(pos, head_bounds)
        regions = classify_vertex(x_ratio, y_ratio, z_ratio, face_z_dir)
        
        offset = deform_func(pos, x_ratio, y_ratio, z_ratio, regions)
        if offset:
            sk.data[i].co = pos + offset
        else:
            sk.data[i].co = pos + Vector((0, 0, EPSILON))
    
    return sk


# ============================================================
# SHAPE KEY DEFORMATION FUNCTIONS
# ============================================================

def deform_jaw_open(pos, xr, yr, zr, regions):
    """Jaw drops down and slightly forward."""
    w = regions.get('jaw', 0)
    if w < 0.05:
        return None
    d = DEFORM['jawOpen'] * w
    return Vector((0, -d * 0.3, -d))


def deform_mouth_open(pos, xr, yr, zr, regions):
    """Mouth opens (upper lip lifts, lower lip drops)."""
    w = regions.get('mouth', 0)
    if w < 0.05:
        return None
    # Upper vs lower half of mouth region
    mouth_center_y = head_bounds_ref['min_y'] + head_bounds_ref['height'] * 0.32
    if pos.y > mouth_center_y:
        # Upper lip - slight upward
        return Vector((0, DEFORM['mouthOpen'] * w * 0.3, 0))
    else:
        # Lower lip - downward
        return Vector((0, -DEFORM['mouthOpen'] * w * 0.5, 0))


def deform_mouth_smile(pos, xr, yr, zr, regions):
    """Corners of mouth pull up and slightly out."""
    mc = regions.get('mouth_corner', 0)
    m = regions.get('mouth', 0)
    w = max(mc, m * 0.3)
    if w < 0.05:
        return None
    d = DEFORM['mouthSmile'] * w
    direction = 1.0 if xr > 0.5 else -1.0
    return Vector((direction * d * 0.4, d, 0))


def deform_mouth_pucker(pos, xr, yr, zr, regions):
    """Lips push forward and inward (kissing shape)."""
    w = regions.get('lips', 0)
    if w < 0.05:
        return None
    d = DEFORM['mouthPucker'] * w
    direction = 1.0 if xr > 0.5 else -1.0
    return Vector((-direction * d * 0.3, 0, d * 0.5))


def deform_mouth_funnel(pos, xr, yr, zr, regions):
    """Lips form an O shape."""
    w = regions.get('lips', 0)
    if w < 0.05:
        return None
    d = DEFORM['mouthFunnel'] * w
    direction = 1.0 if xr > 0.5 else -1.0
    return Vector((-direction * d * 0.4, 0, d * 0.3))


def deform_mouth_close(pos, xr, yr, zr, regions):
    """Lips press together."""
    w = regions.get('mouth', 0)
    if w < 0.05:
        return None
    d = DEFORM['mouthClose'] * w
    return Vector((0, 0, -d * 0.3))


def deform_eye_blink_left(pos, xr, yr, zr, regions):
    """Left eye closes (upper and lower lids meet)."""
    w = regions.get('eye_left', 0)
    if w < 0.05:
        return None
    d = DEFORM['eyeBlinkLeft'] * w
    # Move toward eye center vertically
    eye_center_y = head_bounds_ref['min_y'] + head_bounds_ref['height'] * 0.57
    direction = 1.0 if pos.y > eye_center_y else -1.0
    return Vector((0, -direction * d * 0.6, 0))


def deform_eye_blink_right(pos, xr, yr, zr, regions):
    """Right eye closes."""
    w = regions.get('eye_right', 0)
    if w < 0.05:
        return None
    d = DEFORM['eyeBlinkRight'] * w
    eye_center_y = head_bounds_ref['min_y'] + head_bounds_ref['height'] * 0.57
    direction = 1.0 if pos.y > eye_center_y else -1.0
    return Vector((0, -direction * d * 0.6, 0))


def deform_brow_inner_up(pos, xr, yr, zr, regions):
    """Inner eyebrows raise (surprise)."""
    w = regions.get('brow_inner', 0)
    if w < 0.05:
        return None
    d = DEFORM['browInnerUp'] * w
    return Vector((0, d, 0))


def deform_brow_down_left(pos, xr, yr, zr, regions):
    """Left eyebrow furrows down (angry)."""
    w = regions.get('brow_left', 0)
    if w < 0.05:
        return None
    d = DEFORM['browDownLeft'] * w
    return Vector((0, -d, 0))


def deform_brow_down_right(pos, xr, yr, zr, regions):
    """Right eyebrow furrows down."""
    w = regions.get('brow_right', 0)
    if w < 0.05:
        return None
    d = DEFORM['browDownRight'] * w
    return Vector((0, -d, 0))


def deform_smile_left(pos, xr, yr, zr, regions):
    """Left side of face smiles (cheek raises + mouth corner up)."""
    mc = regions.get('mouth_corner', 0)
    cl = regions.get('cheek_left', 0)
    w = max(mc, cl) 
    if w < 0.05:
        return None
    d = DEFORM['smileLeft'] * w
    return Vector((d * 0.2, d, 0))


def deform_smile_right(pos, xr, yr, zr, regions):
    """Right side of face smiles."""
    mc = regions.get('mouth_corner', 0)
    cr = regions.get('cheek_right', 0)
    w = max(mc, cr)
    if w < 0.05:
        return None
    d = DEFORM['smileRight'] * w
    return Vector((-d * 0.2, d, 0))


# ============================================================
# MAIN SCRIPT
# ============================================================

# Global reference for deform functions that need head_bounds
head_bounds_ref = {}

def main():
    global head_bounds_ref
    
    print("\n" + "=" * 60)
    print("AVATAR SHAPE KEY GENERATOR")
    print("=" * 60)
    
    # Step 1: Clear scene
    print("\n[1/6] Clearing scene...")
    clear_scene()
    
    # Step 2: Import GLB
    print(f"\n[2/6] Importing GLB from: {INPUT_PATH}")
    obj = import_glb(INPUT_PATH)
    print(f"  Object: {obj.name}, Type: {obj.type}")
    print(f"  Vertices: {len(obj.data.vertices)}")
    print(f"  Faces: {len(obj.data.polygons)}")
    
    # Step 3: Analyze mesh
    print("\n[3/6] Analyzing mesh geometry...")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Make sure we're in object mode
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    positions, normals = get_vertex_data(obj)
    body_bounds = compute_bounds(positions)
    print(f"  Body bounds: X[{body_bounds['min_x']:.3f}, {body_bounds['max_x']:.3f}] "
          f"Y[{body_bounds['min_y']:.3f}, {body_bounds['max_y']:.3f}] "
          f"Z[{body_bounds['min_z']:.3f}, {body_bounds['max_z']:.3f}]")
    
    head_indices, head_bounds, face_z_dir = compute_head_region(positions, normals, body_bounds)
    head_bounds_ref = head_bounds
    
    # Step 4: Create shape keys
    print("\n[4/6] Creating shape keys...")
    
    # Remove existing shape keys if any (from previous runs)
    if obj.data.shape_keys:
        existing_names = [kb.name for kb in obj.data.shape_keys.key_blocks]
        print(f"  Found {len(existing_names)} existing shape keys, removing...")
        # Remove in reverse order (can't remove Basis while others exist)
        for name in reversed(existing_names):
            if name == 'Basis':
                continue
            try:
                obj.shape_key_remove(obj.data.shape_keys.key_blocks[name])
            except:
                pass
        # Now remove Basis
        if obj.data.shape_keys:
            try:
                obj.shape_key_remove(obj.data.shape_keys.key_blocks['Basis'])
            except:
                pass
    
    # Create Basis first
    basis = obj.shape_key_add(name='Basis', from_mix=False)
    print("  Created: Basis (neutral)")
    
    shape_keys = [
        ("jawOpen",           deform_jaw_open),
        ("mouthOpen",         deform_mouth_open),
        ("mouthSmile",        deform_mouth_smile),
        ("mouthPucker",       deform_mouth_pucker),
        ("mouthFunnel",       deform_mouth_funnel),
        ("mouthClose",        deform_mouth_close),
        ("eyeBlinkLeft",      deform_eye_blink_left),
        ("eyeBlinkRight",     deform_eye_blink_right),
        ("browInnerUp",       deform_brow_inner_up),
        ("browDownLeft",      deform_brow_down_left),
        ("browDownRight",     deform_brow_down_right),
        ("smileLeft",         deform_smile_left),
        ("smileRight",        deform_smile_right),
    ]
    
    created_count = 0
    for name, deform_func in shape_keys:
        sk = create_shape_key_deformation(
            obj, name, positions, normals,
            head_indices, head_bounds, face_z_dir,
            deform_func
        )
        created_count += 1
        # Count non-zero vertices in this shape key
        active_verts = sum(1 for idx, d in enumerate(sk.data)
                          if abs(d.co.x - basis.data[idx].co.x) > 0.0001 or
                             abs(d.co.y - basis.data[idx].co.y) > 0.0001 or
                             abs(d.co.z - basis.data[idx].co.z) > 0.0001)
        print(f"  Created: {name} ({active_verts} vertices deformed)")
    
    print(f"\n  Total shape keys created: {created_count}")
    
    # Step 5: Export
    print(f"\n[5/6] Exporting GLB to: {OUTPUT_PATH}")
    bpy.ops.export_scene.gltf(
        filepath=OUTPUT_PATH,
        export_format='GLB',
        export_morph=True,
        export_normals=True,
        export_materials='EXPORT',
        export_apply=True,
    )
    
    # Step 6: Summary
    print(f"\n[6/6] Done!")
    print(f"  Input:  {INPUT_PATH}")
    print(f"  Output: {OUTPUT_PATH}")
    print(f"  Shape keys: {', '.join([sk[0] for sk in shape_keys])}")
    print(f"\n  Next step: Copy avatar_shapekeys.glb over avatar.glb and test in browser.")
    print("=" * 60)


if __name__ == "__main__":
    main()
