# Copyright 2025 Pavlo Penenko
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

import abc
from pathlib import Path
import subprocess
import _shader_base, _impl
from metashade.hlsl.util import dxc
from metashade.glsl.util import glslc
from metashade.util import spirv_cross

class Shader(_shader_base.Shader):
    @abc.abstractmethod
    def _get_hlsl_profile():
        pass

    def _compile(self, to_glsl : bool) -> bool:
        try:
            dxc_output_path = Path(self._file_path).with_suffix(
                '.hlsl.spv' if to_glsl else '.cso'
            )
            
            dxc.compile(
                src_path = self._file_path,
                entry_point_name = _impl.entry_point_name,
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

                glslc.compile(
                    src_path = glsl_path,
                    target_env = 'vulkan1.1',
                    shader_stage = self._get_glslc_stage(),
                    entry_point_name = _impl.entry_point_name,
                    output_path = spv_path
                )
            return True
        except subprocess.CalledProcessError as err:
            return False

class VertexShader(Shader):
    def __init__(
        self,
        out_dir : Path,
        mesh_name : str,
        primitive_idx : int
    ):
        super().__init__(out_dir, mesh_name, primitive_idx, 'VS.hlsl')

    @staticmethod
    def _get_hlsl_profile():
        return 'vs_6_0'
    
    @staticmethod
    def _get_glslc_stage():
        return 'vertex'

    def _generate(self, shader_file, material, primitive):
        _impl.generate_vs(shader_file, primitive)

class PixelShader(Shader):
    def __init__(
        self,
        out_dir : Path,
        mesh_name : str,
        primitive_idx : int
    ):
        super().__init__(out_dir, mesh_name, primitive_idx, 'PS.hlsl')

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
