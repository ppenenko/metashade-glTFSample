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

import abc, argparse, functools, io, os, subprocess, sys
from pathlib import Path
import multiprocessing as mp
from typing import List, NamedTuple
from pygltflib import GLTF2

from metashade.hlsl.util import dxc
from metashade.util import perf, spirv_cross
from metashade.glsl.util import glslc

import _impl

class _Shader(abc.ABC):
    def __init__(
        self,
        out_dir : Path,
        mesh_name : str,
        primitive_idx : int,
        file_suffix : str
    ):
        self._file_path = out_dir / f'{mesh_name}-{primitive_idx}-{file_suffix}'

    @abc.abstractmethod
    def _get_entry_point_name():
        pass
    
    @abc.abstractmethod
    def _get_hlsl_profile():
        pass
    
    @abc.abstractmethod
    def _get_glslc_stage():
        pass

    @abc.abstractmethod
    def _generate(self, shader_file, material, primitive):
        pass

    def generate(self, material, primitive):
        with perf.TimedScope(f'Generating {self._file_path} ', 'Done'), \
            open(self._file_path, 'w') as shader_file:
            #
            self._generate(shader_file, material, primitive)

    @abc.abstractmethod
    def compile(self, to_glsl : bool) -> str:
        pass

def _compile_shader(shader, to_glsl):
    '''
    Helper function to compile a shader in a process pool.
    Without it, the pool would not be able to pickle the method.
    '''
    return shader.compile(to_glsl)

class _HlslShader(_Shader):
    def compile(self, to_glsl : bool) -> str:
        log = io.StringIO()
        log, sys.stdout = sys.stdout, log

        try:
            dxc_output_path = Path(self._file_path).with_suffix(
                '.hlsl.spv' if to_glsl else '.cso'
            )
            
            dxc.compile(
                src_path = self._file_path,
                entry_point_name = self._get_entry_point_name(),
                profile = self._get_hlsl_profile(),
                to_spirv = to_glsl,
                output_path = dxc_output_path
            )

            if to_glsl:
                glsl_path = Path(self._file_path).with_suffix('.glsl')
                spirv_cross.spirv_to_glsl(
                    spirv_path = dxc_output_path,
                    glsl_path = glsl_path
                )
                spv_path = Path(self._file_path).with_suffix('.spv')

                # this is the default produced by SPIRV-Cross
                glsl_entry_point_name = 'main'

                glslc.compile(
                    src_path = glsl_path,
                    target_env = 'vulkan1.1',
                    shader_stage = self._get_glslc_stage(),
                    entry_point_name = glsl_entry_point_name,
                    output_path = spv_path
                )
        except subprocess.CalledProcessError as err:
            pass

        log, sys.stdout = sys.stdout, log
        return log.getvalue()

class _HlslVertexShader(_HlslShader):
    def __init__(
        self,
        out_dir : Path,
        mesh_name : str,
        primitive_idx : int
    ):
        super().__init__(out_dir, mesh_name, primitive_idx, 'VS.hlsl')
    
    @staticmethod
    def _get_entry_point_name():
        return _impl.vs_main
    
    @staticmethod
    def _get_hlsl_profile():
        return 'vs_6_0'
    
    @staticmethod
    def _get_glslc_stage():
        return 'vertex'

    def _generate(self, shader_file, material, primitive):
        _impl.generate_vs(shader_file, primitive)

class _HlslPixelShader(_HlslShader):
    def __init__(
        self,
        out_dir : Path,
        mesh_name : str,
        primitive_idx : int
    ):
        super().__init__(out_dir, mesh_name, primitive_idx, 'PS.hlsl')

    @staticmethod
    def _get_entry_point_name():
        return _impl.ps_main
    
    @staticmethod
    def _get_hlsl_profile():
        return 'ps_6_0'
    
    @staticmethod
    def _get_glslc_stage():
        return 'fragment'
    
    def _generate(self, shader_file, material, primitive):
        _impl.generate_ps(
            shader_file,
            material,
            primitive
        )

class _AssetResult(NamedTuple):
    log : io.StringIO
    shaders : List[_Shader]

def _process_asset(
        gltf_file_path : str,
        out_dir : Path,
        skip_codegen : bool = False
) -> _AssetResult:
    log = io.StringIO()
    log, sys.stdout = sys.stdout, log

    per_asset_shaders = []

    with perf.TimedScope(f'Loading glTF asset {gltf_file_path} '):
        gltf_asset = GLTF2().load(gltf_file_path)

    for mesh_idx, mesh in enumerate(gltf_asset.meshes):
        mesh_name = ( mesh.name if mesh.name is not None
            else f'UnnamedMesh{mesh_idx}'
        )

        for primitive_idx, primitive in enumerate(mesh.primitives):
            per_primitive_shaders = [
                _HlslVertexShader(out_dir, mesh_name, primitive_idx),
                _HlslPixelShader(out_dir, mesh_name, primitive_idx)
            ]
            
            if not skip_codegen:
                material = gltf_asset.materials[primitive.material]
                for shader in per_primitive_shaders:
                    shader.generate(
                        material,
                        primitive
                    )
            per_asset_shaders += per_primitive_shaders

    log, sys.stdout = sys.stdout, log
    return _AssetResult(log.getvalue(), per_asset_shaders)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "Generate shaders from glTF materials."
    )
    parser.add_argument("--gltf-dir", help = "Path to the source glTF assets")
    parser.add_argument("--out-dir", help = "Path to the output directory")
    parser.add_argument(
        "--compile",
        action = 'store_true',
        help = "Compile the generated shaders with DXC (has to be in PATH)"
    )
    parser.add_argument(
        "--to-glsl",
        action = 'store_true',
        help = "Cross-compile to GLSL with SPIRV-Cross"
    )
    parser.add_argument(
        "--skip-codegen",
        action = 'store_true',
        help = "Assume that sources have been generated and proceed to "
               "compilation."
    )
    parser.add_argument(
        "--serial",
        action = 'store_true',
        help = "Disable parallelization to facilitate debugging."
    )
    args = parser.parse_args()

    gltf_dir_path = Path(args.gltf_dir)
    if not gltf_dir_path.is_dir():
        raise NotADirectoryError(gltf_dir_path)
    
    os.makedirs(args.out_dir, exist_ok = True)
    out_dir = Path(args.out_dir)

    shaders = []
    if args.serial:
        for gltf_path in gltf_dir_path.glob('**/*.gltf'):
            asset_result = _process_asset(
                gltf_file_path = gltf_path,
                out_dir = out_dir,
                skip_codegen = args.skip_codegen
            )
            print(asset_result.log)
            shaders += asset_result.shaders
    else:
        with mp.Pool() as pool:
            for asset_result in pool.imap_unordered(
                functools.partial(
                    _process_asset,
                    out_dir = out_dir,
                    skip_codegen = args.skip_codegen
                ),
                gltf_dir_path.glob('**/*.gltf')
            ):
                print(asset_result.log)
                shaders += asset_result.shaders

    if args.compile:
        print()
        dxc.identify()
        if args.to_glsl:
            spirv_cross.identify()
            glslc.identify()

        if args.serial:
            for shader in shaders:
                log = shader.compile(to_glsl = args.to_glsl)
                print(log, end = '')
        else:
            with mp.Pool() as pool:
                for log in pool.imap_unordered(
                    functools.partial(
                        _compile_shader,
                        to_glsl = args.to_glsl
                    ),
                    shaders
                ):
                    print(log, end = '')
