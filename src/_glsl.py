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

from pathlib import Path
from metashade.glsl.util import glslang
import _shader_base, _impl
import subprocess

class Shader(_shader_base.Shader):
    def _compile(self, to_glsl : bool) -> bool:
        try:
            glsl_output_path = Path(self._file_path).with_suffix('.spv')
            glslang.compile(
                src_path = self._file_path,
                target_env = 'vulkan1.1',
                shader_stage = 'frag',
                output_path = glsl_output_path
            )
            return True
        except subprocess.CalledProcessError as err:
            return False
    
class FragmentShader(Shader):
    def __init__(
        self,
        out_dir : Path,
        shader_name : str
    ):
        super().__init__(out_dir, shader_name, 'frag.glsl')

    @staticmethod
    def _get_glslc_stage():
        return 'fragment'

    def _generate(self, shader_file, material, primitive):
        _impl.generate_frag(shader_file, material, primitive)
