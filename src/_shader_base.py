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
        shader_name : str
    ):
        self.src_path = self._generate_src_path(out_dir, shader_name)
        self.bin_path = self._generate_bin_path(out_dir, shader_name)

    @abc.abstractmethod
    def _generate_src_path(self, out_dir : Path, shader_name : str) -> Path:
        pass

    @abc.abstractmethod
    def _generate_bin_path(self, out_dir : Path, shader_name : str) -> Path:
        pass

    # @abc.abstractmethod
    # def _generate_deferred(self):
    #     pass

    def _generate_wrapped(self, generate_func):
        with perf.TimedScope(f'Generating {self.src_path} ', 'Done'), \
            open(self.src_path, 'w') as shader_file:
            #
            generate_func(shader_file)

    class GenerateAndCompileResult(NamedTuple):
        log : str
        success : bool

    @abc.abstractmethod
    def _compile(self) -> bool:
        pass

    def generate_and_compile(
        self, ref_differ : RefDiffer
    ) -> GenerateAndCompileResult:
        log = io.StringIO()
        log, sys.stdout = sys.stdout, log

        if ref_differ is not None:
            ref_differ(self.src_path)

        success = self._compile()

        log, sys.stdout = sys.stdout, log
        return Shader.GenerateAndCompileResult(log.getvalue(), success)
