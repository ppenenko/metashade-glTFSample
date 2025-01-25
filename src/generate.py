# Copyright 2020 Pavlo Penenko
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse, functools, io, json, os, sys
from pathlib import Path
import multiprocessing as mp
from typing import List, NamedTuple
from pygltflib import GLTF2

from metashade.util import perf, spirv_cross
from metashade.hlsl.util import dxc
from metashade.glsl.util import glslang, glslc
from metashade.util.tests import RefDiffer

import _shader_base, _hlsl, _glsl

def _compile_shader(
    shader,
    ref_differ : RefDiffer
) -> _shader_base.Shader.CompileResult:
    '''
    Helper function to compile a shader in a process pool.
    Without it, the pool would not be able to pickle the method.
    '''
    return shader.compile(ref_differ)

class _AssetResult(NamedTuple):
    log : io.StringIO
    shaders : List[_shader_base.Shader]

def _process_asset(
    gltf_file_path : str,
    out_dir : Path
) -> _AssetResult:
    log = io.StringIO()
    log, sys.stdout = sys.stdout, log

    per_asset_shader_list = []  # List of shaders to compile by this script
    per_asset_shader_index = [] # Dictionary of shaders per mesh and primitive

    with perf.TimedScope(f'Loading glTF asset {gltf_file_path} '):
        gltf_asset = GLTF2().load(gltf_file_path)

    for mesh_idx, mesh in enumerate(gltf_asset.meshes):
        mesh_name = ( mesh.name if mesh.name is not None
            else f'UnnamedMesh{mesh_idx}'
        )

        per_mesh_shader_index = []

        for primitive_idx, primitive in enumerate(mesh.primitives):
            shader_base_name = f'{mesh_name}-{primitive_idx}'

            per_primitive_shader_list = []
            per_primitive_shader_index = dict()

            dx_vs = _hlsl.VertexShader(out_dir, shader_base_name)
            dx_ps = _hlsl.PixelShader(out_dir, shader_base_name)

            per_primitive_shader_list += [dx_vs, dx_ps]

            per_primitive_shader_index['dx'] = {
                'vs': dx_vs.bin_path.name,
                'ps': dx_ps.bin_path.name
            }

            vk_frag = _glsl.FragmentShader(out_dir, shader_base_name)
            per_primitive_shader_list.append(vk_frag)
            per_primitive_shader_index['vk'] = { 'frag' : vk_frag.bin_path.name }

            material = gltf_asset.materials[primitive.material]
            for shader in per_primitive_shader_list:
                shader.generate(
                    material,
                    primitive
                )
            per_asset_shader_list += per_primitive_shader_list
            per_mesh_shader_index.append(per_primitive_shader_index)

        per_asset_shader_index.append(per_mesh_shader_index)
        shader_index_file_path = (
            out_dir / gltf_file_path.with_suffix('.json').name
        )
        with open(shader_index_file_path, 'w') as shader_index_file:
            json.dump(
                per_asset_shader_index,
                shader_index_file,
                indent = 4
            )
        print(f'Shader index written to {shader_index_file_path}\n')

    log, sys.stdout = sys.stdout, log
    return _AssetResult(
        log = log.getvalue(),
        shaders = per_asset_shader_list
    )

def generate(
    gltf_dir_path : Path,
    out_dir_path : Path,
    compile : bool,
    serial : bool,
    ref_differ : RefDiffer
):
    if not gltf_dir_path.is_dir():
        raise NotADirectoryError(gltf_dir_path)

    os.makedirs(out_dir_path, exist_ok = True)

    shaders = []

    process_asset_partial = functools.partial(
        _process_asset,
        out_dir = out_dir_path
    )
    gltf_files_glob = gltf_dir_path.glob('**/*.gltf')

    if serial:
        for gltf_path in gltf_files_glob:
            asset_result = process_asset_partial(gltf_file_path = gltf_path)
            print(asset_result.log)
            shaders += asset_result.shaders
    else:
        with mp.Pool() as pool:
            for asset_result in pool.imap_unordered(
                process_asset_partial,
                gltf_files_glob
            ):
                print(asset_result.log)
                shaders += asset_result.shaders

    if compile:
        print()
        dxc.identify()
        glslang.identify()

        num_failed = 0

        if serial:
            for shader in shaders:
                result = shader.compile(ref_differ = ref_differ)
                if not result.success:
                    num_failed += 1
                print(result.log, end = '')
        else:
            with mp.Pool() as pool:
                for result in pool.imap_unordered(
                    functools.partial(
                        _compile_shader,
                        ref_differ = ref_differ
                    ),
                    shaders
                ):
                    if not result.success:
                        num_failed += 1
                    print(result.log, end = '')

        if num_failed > 0:
            raise RuntimeError(
                f'{num_failed} out of {len(shaders)} shaders failed to '
                'compile - see the log above.'
            )
        else:
            print(f'\nAll {len(shaders)} shaders compiled successfully.')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "Generate shaders from glTF materials."
    )
    parser.add_argument("--gltf-dir", help = "Path to the source glTF assets")
    parser.add_argument("--out-dir", help = "Path to the output directory")
    parser.add_argument("--ref-dir", help = "Path to the test references")
    
    parser.add_argument(
        "--compile",
        action = 'store_true',
        help = "Compile the generated shaders with DXC (has to be in PATH)"
    )
    parser.add_argument(
        "--serial",
        action = 'store_true',
        help = "Disable parallelization to facilitate debugging."
    )
    args = parser.parse_args()

    generate(
        gltf_dir_path = Path(args.gltf_dir),
        out_dir_path = Path(args.out_dir),
        compile = args.compile,
        serial = args.serial,
        ref_differ = RefDiffer(Path(args.ref_dir)) if args.ref_dir else None
    )