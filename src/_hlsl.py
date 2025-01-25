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
    @staticmethod
    @abc.abstractmethod
    def _get_hlsl_profile() -> str:
        pass

    @staticmethod
    @abc.abstractmethod
    def _get_stage_name() -> str:
        pass

    def _generate_src_path(self, out_dir : Path, shader_name : str) -> Path:
        return out_dir / f'{shader_name}-{self._get_stage_name()}.hlsl'

    def _generate_bin_path(self, out_dir : Path, shader_name : str) -> Path:
        return out_dir / f'{shader_name}-{self._get_stage_name()}.cso'

    def _compile(self) -> bool:
        try:
            dxc.compile(
                src_path = self.src_path,
                entry_point_name = _impl.entry_point_name,
                profile = self._get_hlsl_profile(),
                to_spirv = False,
                o0 = False,
                output_path = self.bin_path
            )
            return True
        except subprocess.CalledProcessError as err:
            return False

class VertexShader(Shader):
    @staticmethod
    def _get_hlsl_profile() -> str:
        return 'vs_6_0'
    
    @staticmethod
    def _get_stage_name() -> str:
        return 'VS'

    def _generate(self, shader_file, material, primitive):
        _impl.generate_vs(shader_file, primitive)

class PixelShader(Shader):
    @staticmethod
    def _get_hlsl_profile():
        return 'ps_6_0'
    
    @staticmethod
    def _get_stage_name() -> str:
        return 'PS'

    def _generate(self, shader_file, material, primitive):
        _impl.generate_ps(
            shader_file,
            material,
            primitive
        )
