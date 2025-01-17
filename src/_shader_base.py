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
import io
from pathlib import Path
import sys
from typing import NamedTuple
from metashade.util.tests import RefDiffer
from metashade.util import perf

class Shader(abc.ABC):
    def __init__(
        self,
        out_dir : Path,
        shader_name : str,
        file_suffix : str
    ):
        self._file_path = (
            out_dir / f'{shader_name}-{file_suffix}'
        )

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

    class CompileResult(NamedTuple):
        log : str
        success : bool

    @abc.abstractmethod
    def _compile(self, to_glsl : bool) -> bool:
        pass

    def compile(self, to_glsl : bool, ref_differ : RefDiffer) -> CompileResult:
        log = io.StringIO()
        log, sys.stdout = sys.stdout, log

        if ref_differ is not None:
            ref_differ(self._file_path)

        success = self._compile(to_glsl)

        log, sys.stdout = sys.stdout, log
        return Shader.CompileResult(log.getvalue(), success)
