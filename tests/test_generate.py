# Copyright 2024 Pavlo Penenko
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

import os, sys
from pathlib import Path

tests_dir_path = Path(__file__).parent
repo_root_dir_path = tests_dir_path.parent

# Add these directories to PYTHONPATH
src_dir_path = (repo_root_dir_path / 'src').resolve()
metashade_dir_path = (repo_root_dir_path / 'metashade').resolve()
sys.path += [str(src_dir_path), str(metashade_dir_path)]

from metashade.util.tests import RefDiffer
import generate

class TestGenerate:
    @classmethod
    def setup_class(cls):
        out_dir = os.getenv('METASHADE_GLTFSAMPLE_PYTEST_OUT_DIR', None)
        ref_dir = repo_root_dir_path / 'tests' / 'ref' / 'content'

        if out_dir is None:
            # Don't compare against references explicitly in the script.
            # Instead, overwrite the references with the generated files.
            # This is useful for diffing or updating the references manually with
            # git.
            cls._out_dir = ref_dir
            cls._ref_differ = None
        else:
            cls._out_dir = Path(out_dir).resolve()
            print(f'Reference directory: {ref_dir}')
            cls._ref_differ = RefDiffer(ref_dir)

        print(f'Test output directory: {cls._out_dir}')
        os.makedirs(cls._out_dir, exist_ok = True)

    def test_generate(self):
        gltf_sample_dir_path = repo_root_dir_path / 'glTFSample'
        gltf_dir_path = gltf_sample_dir_path / 'media' / 'Cauldron-Media'

        generate.generate(
            gltf_dir_path = gltf_dir_path,
            out_dir_path = self._out_dir,
            compile = True,
            serial = False,
            ref_differ = self._ref_differ
        )
