# Copyright 2020 Pavlo Penenko
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

entry_point_name = 'main'

def get_texture_uniform_name(name: str) -> str:
    return 'g_t' + name[0].upper() + name[1:]
    
def get_sampler_uniform_name(name: str) -> str:
    return 'g_s' + name[0].upper() + name[1:]
