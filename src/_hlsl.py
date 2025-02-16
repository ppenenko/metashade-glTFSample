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

import abc, os, subprocess
from pathlib import Path

import _shader_base

import _impl.ps as impl_ps
import _impl.common as common

from metashade.hlsl.util import dxc
from metashade.glsl.util import glslang
from metashade.util.tests import RefDiffer
from metashade.util import spirv_cross

class Shader(_shader_base.Shader):
    @staticmethod
    @abc.abstractmethod
    def _get_hlsl_profile() -> str:
        pass

    @staticmethod
    def _get_src_extension() -> str:
        return 'hlsl'

    @staticmethod
    def _get_bin_extension() -> str:
        return 'cso'
    
    @staticmethod
    @abc.abstractmethod
    def _get_glslang_stage() -> str:
        pass

    def _compile(self, ref_differ : RefDiffer) -> bool:
        try:
            def dxc_compile(to_spirv, output_path):
                dxc.compile(
                    src_path = self._src_path,
                    entry_point_name = common.entry_point_name,
                    profile = self._get_hlsl_profile(),
                    to_spirv = to_spirv,
                    o0 = to_spirv,
                    output_path = output_path
                )

            # Compile to DXIL for consumption by the DX12 host app
            dxc_compile(
                to_spirv = False,
                output_path = self._bin_path
            )

            # Transpile to GLSL for reference while bringing up the GLSL
            # backend
            spirv_path = self._src_path.parent / (self._src_path.name + '.spv')
            dxc_compile(
                to_spirv = True,
                output_path = spirv_path
            )

            glsl_path = self._src_path.parent / (self._src_path.name + '.glsl')
            spirv_cross.spirv_to_glsl(
                spirv_path = spirv_path,
                glsl_path = glsl_path
            )

            if ref_differ is not None:
                ref_differ(glsl_path)

            glslang.compile(
                src_path = glsl_path,
                target_env = 'vulkan1.1',
                shader_stage = self._get_glslang_stage(),
                output_path = os.devnull
            )
            
            return True
        except subprocess.CalledProcessError as err:
            return False

class VertexShader(Shader):
    def __init__(self, out_dir, vertex_data):
        self._vertex_data = vertex_data
        
        shader_name = common.filename_prefix
        vd_id = vertex_data.get_id()
        if vd_id != '':
            shader_name += f'-{vd_id}'
        shader_name += '-VS'

        super().__init__(out_dir, shader_name)

    @staticmethod
    def _get_hlsl_profile() -> str:
        return 'vs_6_0'
    
    @staticmethod
    def _get_glslang_stage() -> str:
        return 'vert'
    
    def _generate(self, ref_differ):
        self._generate_wrapped(
            self._vertex_data.generate_vs,
            ref_differ
        )

class PixelShader(Shader):
    def __init__(self, out_dir, material, vertex_data):
        self._ps_impl = impl_ps.ps(
            material = material,
            vertex_data = vertex_data
        )
        super().__init__(
            out_dir = out_dir,
            shader_name = self._ps_impl.get_id()
        )

    @staticmethod
    def _get_hlsl_profile():
        return 'ps_6_0'

    @staticmethod
    def _get_glslang_stage() -> str:
        return 'frag'

    def _generate(self, ref_differ):
        self._generate_wrapped(
            self._ps_impl.generate,
            ref_differ
        )
