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

import abc, subprocess
from pathlib import Path

from metashade.glsl.util import glslang

import _shader_base
import _impl.ps as impl_ps

class Shader(_shader_base.Shader, abc.ABC):
    @staticmethod
    def _get_src_extension() -> str:
        return 'glsl'

    @staticmethod
    def _get_bin_extension() -> str:
        return 'spv'
    
    def _compile(self, ref_differ) -> bool:
        try:
            glslang.compile(
                src_path = self._src_path,
                target_env = 'vulkan1.1',
                shader_stage = self._get_stage_name(),
                output_path = self._bin_path
            )
            return True
        except subprocess.CalledProcessError as err:
            return False

class FragmentShader(Shader):
    def __init__(self, out_dir):
        super().__init__(out_dir, 'GLTFPbrPass-frag')

    def _generate(self, ref_differ):
        self._generate_wrapped(impl_ps.generate_frag, ref_differ)

    @staticmethod
    def _get_stage_name() -> str:
        return 'frag'
