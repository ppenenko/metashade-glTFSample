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
import _shader_base

from _impl.vertex_data import VertexData
import _impl.ps as impl_ps
import _impl.common as common

from metashade.hlsl.util import dxc

class Shader(_shader_base.Shader):
    @staticmethod
    @abc.abstractmethod
    def _get_hlsl_profile() -> str:
        pass

    def _generate_src_path(self, out_dir : Path, shader_name : str) -> Path:
        return out_dir / f'{shader_name}.hlsl'

    def _generate_bin_path(self, out_dir : Path, shader_name : str) -> Path:
        return out_dir / f'{shader_name}.cso'

    def _compile(self) -> bool:
        try:
            dxc.compile(
                src_path = self.src_path,
                entry_point_name = common.entry_point_name,
                profile = self._get_hlsl_profile(),
                to_spirv = False,
                o0 = False,
                output_path = self.bin_path
            )
            return True
        except subprocess.CalledProcessError as err:
            return False

class VertexShader(Shader):
    def __init__(self, out_dir, vertex_data):
        self._vertex_data = vertex_data
        shader_name = 'GltfPbr'
        vd_id = vertex_data.get_id()
        if vd_id != '':
            shader_name += f'-{vd_id}'
        shader_name += '-VS'

        super().__init__(out_dir, shader_name)

    @staticmethod
    def _get_hlsl_profile() -> str:
        return 'vs_6_0'
    
    def _generate_deferred(self):
        def generate(shader_file):
            self._vertex_data.generate_vs(shader_file)
        self._generate_wrapped(generate)

class PixelShader(Shader):
    def __init__(self, out_dir, primitive_id, material, vertex_data):
        self._vertex_data = vertex_data
        shader_name = f'{primitive_id}-PS'
        super().__init__(out_dir, shader_name)

        def generate(shader_file):
            impl_ps.generate_ps(
                shader_file,
                material,
                self._vertex_data
            )
        self._generate_wrapped(generate)

    def _generate_deferred(self):
        # Do nothing, because we generate the shader in the constructor for
        # now, before generation is decoupled from glTF parsing
        pass

    @staticmethod
    def _get_hlsl_profile():
        return 'ps_6_0'
