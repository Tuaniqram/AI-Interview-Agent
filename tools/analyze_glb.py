import struct, json

with open(r'D:\projectiqram\AI\AI-Interview-Agent\frontend\public\models\avatar.glb', 'rb') as f:
    magic, version, length = struct.unpack('<I I I', f.read(12))
    print(f'GLB: magic=0x{magic:08X} version={version} length={length}')

    chunk_len, chunk_type = struct.unpack('<I I', f.read(8))
    print(f'JSON chunk: len={chunk_len} type=0x{chunk_type:08X}')
    json_data = json.loads(f.read(chunk_len).decode('utf-8'))

    chunk_len, chunk_type = struct.unpack('<I I', f.read(8))
    print(f'BIN chunk: len={chunk_len} type=0x{chunk_type:08X}')
    buf = f.read(chunk_len)
    print(f'Buffer: {len(buf)} bytes\n')

    accessors = json_data.get('accessors', [])
    buffer_views = json_data.get('bufferViews', [])
    meshes = json_data.get('meshes', [])

    for mi, mesh in enumerate(meshes):
        print(f'Mesh {mi}: {mesh.get("name", "unnamed")}')
        for pi, prim in enumerate(mesh.get('primitives', [])):
            targets = prim.get('targets', [])
            print(f'  Targets: {len(targets)}')
            for ti, target in enumerate(targets):
                pos_idx = target.get('POSITION')
                if pos_idx is None:
                    continue
                acc = accessors[pos_idx]
                ct = acc['componentType']
                type_s = acc['type']
                cc = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}.get(type_s, 1)
                count = acc['count']
                bv = buffer_views[acc['bufferView']]
                offset = bv.get('byteOffset', 0)

                is_sparse = 'sparse' in acc
                print(f'  Target {ti}: accessor {pos_idx} type={type_s} count={count} {"SPARSE" if is_sparse else "DENSE"}')

                # Read first 10 vertex deltas (3 floats each)
                if not is_sparse:
                    fmt = '<' + 'f' * min(30, cc * count)
                    vals = struct.unpack_from(fmt, buf, offset)
                    print(f'    First deltas (x,y,z):', end='')
                    for vi in range(0, min(30, len(vals)), 3):
                        print(f' ({vals[vi]:.6f},{vals[vi+1]:.6f},{vals[vi+2]:.6f})', end='')
                    print()
                else:
                    s = acc['sparse']
                    sc = s['count']
                    # indices
                    i_bv = buffer_views[s['indices']['bufferView']]
                    i_off = s['indices'].get('byteOffset', 0)
                    i_ct = s['indices']['componentType']
                    i_fmt = '<' + ('H' if i_ct == 5123 else 'I')
                    i_sz = struct.calcsize(i_fmt)
                    # values
                    v_bv = buffer_views[s['values']['bufferView']]
                    v_off = s['values'].get('byteOffset', 0)
                    v_fmt = '<' + 'f' * cc
                    v_sz = struct.calcsize(v_fmt)

                    print(f'    Sparse: {sc} modified verts')
                    # Also compute from dense base (base might be all zeros or have data)
                    b_vals = struct.unpack_from('<' + 'f' * min(12, cc * count), buf, offset)
                    print(f'    Base first deltas:', [round(v, 8) for v in b_vals[:6]])

                    # Show first 10 sparse entries
                    sum_abs = 0
                    max_abs = 0
                    for si in range(min(20, sc)):
                        idx = struct.unpack_from(i_fmt, buf, i_bv['byteOffset'] + i_off + si * i_sz)[0]
                        vals = struct.unpack_from(v_fmt, buf, v_bv['byteOffset'] + v_off + si * v_sz)
                        for v in vals:
                            sum_abs += abs(v)
                            max_abs = max(max_abs, abs(v))
                    print(f'    Sparse first 20: sum_abs={sum_abs:.6f} max_abs={max_abs:.6f}')

            if not targets:
                print(f'  No morph targets')
    print()

    # Check first mesh's morph target non-zero counts
    for mi, mesh in enumerate(meshes):
        print(f'\n=== FULL MORPH TARGET ANALYSIS: Mesh {mi} ===')
        for pi, prim in enumerate(mesh.get('primitives', [])):
            targets = prim.get('targets', [])
            for ti, target in enumerate(targets):
                pos_idx = target.get('POSITION')
                if pos_idx is None:
                    continue
                acc = accessors[pos_idx]
                ct = acc['componentType']
                type_s = acc['type']
                cc = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}.get(type_s, 1)
                count = acc['count']
                bv = buffer_views[acc['bufferView']]
                offset = bv.get('byteOffset', 0)

                is_sparse = 'sparse' in acc

                if is_sparse:
                    # For sparse: read the SPARSE values, not the base
                    s = acc['sparse']
                    sc = s['count']
                    i_bv = buffer_views[s['indices']['bufferView']]
                    i_off = s['indices'].get('byteOffset', 0)
                    i_ct = s['indices']['componentType']
                    i_fmt = '<' + ('H' if i_ct == 5123 else 'I')
                    i_sz = struct.calcsize(i_fmt)
                    v_bv = buffer_views[s['values']['bufferView']]
                    v_off = s['values'].get('byteOffset', 0)

                    # Sample 500 sparse entries evenly
                    sample_step = max(1, sc // 500)
                    max_delta = 0
                    nz_count = 0
                    for si in range(0, min(sc, 50000), sample_step):
                        vals = struct.unpack_from('<3f', buf, v_bv['byteOffset'] + v_off + si * 12)
                        for v in vals:
                            if abs(v) > 0.0001:
                                nz_count += 1
                            if abs(v) > max_delta:
                                max_delta = abs(v)
                    print(f'  Target {ti}: sparse nz_samples={nz_count} max_delta={max_delta:.6f} (sampled {min(sc, 50000)//sample_step} of {sc})')
                else:
                    # Dense: sample every 50th vertex
                    sample_step = max(1, count // 1000)
                    max_delta = 0
                    nz_count = 0
                    for vi in range(0, min(count, 100000), sample_step):
                        vals = struct.unpack_from('<3f', buf, offset + vi * 12)
                        for v in vals:
                            if abs(v) > 0.0001:
                                nz_count += 1
                            if abs(v) > max_delta:
                                max_delta = abs(v)
                    print(f'  Target {ti}: dense nz_samples={nz_count} max_delta={max_delta:.6f} (sampled {min(count, 100000)//sample_step} of {count})')

print('\nDone.')
