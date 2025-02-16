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
        self._src_path = out_dir / f'{shader_name}.{self._get_src_extension()}'
        self._bin_path = out_dir / f'{shader_name}.{self._get_bin_extension()}'

    def get_index_name(self) -> str:
        '''
        Tha name for the shader index
        '''
        return self._bin_path.name

    @staticmethod
    @abc.abstractmethod
    def _get_src_extension() -> str:
        pass

    @staticmethod
    @abc.abstractmethod
    def _get_bin_extension() -> str:
        pass

    @abc.abstractmethod
    def _generate(self, ref_differ : RefDiffer):
        pass

    def _generate_wrapped(
        self,
        generate_func,
        ref_differ : RefDiffer
    ):
        with perf.TimedScope(f'Generating {self._src_path} '), \
            open(self._src_path, 'w') as shader_file:
            #
            generate_func(shader_file)

        if ref_differ is not None:
            ref_differ(self._src_path)

    class GenerateAndCompileResult(NamedTuple):
        log : str
        success : bool

    @abc.abstractmethod
    def _compile(self, ref_differ : RefDiffer) -> bool:
        pass

    def generate_and_compile(
        self,
        ref_differ : RefDiffer
    ) -> GenerateAndCompileResult:
        log = io.StringIO()
        log, sys.stdout = sys.stdout, log

        self._generate(ref_differ)
        success = self._compile(ref_differ)

        log, sys.stdout = sys.stdout, log
        return Shader.GenerateAndCompileResult(log.getvalue(), success)
