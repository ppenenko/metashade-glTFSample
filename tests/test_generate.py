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
src_dir_path = (repo_root_dir_path / 'src').resolve()
metashade_dir_path = (repo_root_dir_path / 'metashade').resolve()

sys.path += [str(src_dir_path), str(metashade_dir_path)]

import generate

class TestGenerate:
    def test_generate(self):
        gltf_sample_dir_path = repo_root_dir_path / 'glTFSample'
        gltf_dir_path = gltf_sample_dir_path / 'media' / 'Cauldron-Media'
        out_dir_path = gltf_sample_dir_path / 'build' / 'DX12' / 'metashade-out'

        generate.generate(
            gltf_dir_path = gltf_dir_path,
            out_dir_path = out_dir_path,
            compile = True,
            to_glsl = False,
            skip_codegen = False,
            serial = False
        )
