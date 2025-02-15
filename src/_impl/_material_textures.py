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

from typing import Any, NamedTuple
from . import common

class MaterialTextures:
    class _TextureDef(NamedTuple):
        texel_dtype_name : str
        uv_set_idx : int

    def __init__(self, material):
        self._texture_defs = dict()
        id_dict = dict()

        def _define(
            parent,
            name: str,
            id : str,
            texel_dtype_name = None
        ):
            gltf_texture = getattr(parent, name + 'Texture')
            if gltf_texture is not None:
                uv_set_idx = gltf_texture.texCoord
                if uv_set_idx is None:
                    uv_set_idx = 0

                self._texture_defs[name] = self._TextureDef(
                    texel_dtype_name, uv_set_idx
                )

                if id in id_dict:
                    raise RuntimeError(f'Material texture IDs must be unique')
                id_dict[id] = uv_set_idx

        _define(material, 'normal', 'n', 'Vector4f')
        _define(material, 'occlusion', 'o')
        _define(material, 'emissive', 'e', 'RgbaF')

        if material.pbrMetallicRoughness is not None:
            _define(
                material.pbrMetallicRoughness, 'baseColor', 'bc', 'RgbaF'
            )
            _define(
                material.pbrMetallicRoughness,
                'metallicRoughness',
                'mr',
                'RgbaF'
            )
        elif material.extensions is not None:
            specularGlossiness = \
                material.extensions.KHR_materials_pbrSpecularGlossiness
            if specularGlossiness is not None:
                assert False, \
                    ('KHR_materials_pbrSpecularGlossiness '
                     'is not implemented yet, '
                    'see https://github.com/metashade/metashade/issues/18')
            
        self._id = '_'.join([
            f'{id}{uv_set_idx}' for id, uv_set_idx
            in sorted(id_dict.items())
        ])

    def get_id(self) -> str:
        return self._id

    def __len__(self):
        return len(self._texture_defs)
    
    def generate_uniforms(self, sh):
        # The host app allocates texture and uniform registers for material
        # textures sorted by name
        for texture_idx, (texture_name, texture_def) in enumerate(
            sorted(self._texture_defs.items())
        ):
            texel_dtype = (
                getattr(sh, texture_def.texel_dtype_name)
                if texture_def.texel_dtype_name is not None
                else None
            )
            
            sh.uniform(
                common.get_texture_uniform_name(texture_name),
                sh.Texture2d(texel_type = texel_dtype),
                dx_register = texture_idx
            )
            sh.uniform(
                common.get_sampler_uniform_name(texture_name),
                sh.Sampler,
                dx_register = texture_idx
            )

    def get_uv(self, sh, texture_name : str):
        texture_def = self._texture_defs.get(texture_name)
        if texture_def is None:
            return None

        return getattr(sh.psIn, f'uv{texture_def.uv_set_idx}')

    def sample_texture(self, sh, texture_name : str):
        # Get the UV member of the input structure
        # corresponding to the glTF texture
        uv = self.get_uv(sh, texture_name)
        if uv is None:
            # The texture is not used in the material
            return None

        # Get the texture and sampler uniforms by the glTF texture name
        texture = getattr(sh, common.get_texture_uniform_name(texture_name))
        sampler = getattr(sh, common.get_sampler_uniform_name(texture_name))

        # Generate the expression sampling the texture
        sample = (sampler @ texture)(uv, lod_bias = sh.g_lodBias)

        # Create a unique variable name for the sample
        sample_var_name = texture_name + 'Sample'

        # Initialize a local sample variable with the expression
        setattr(sh, sample_var_name, sample)

        # Return a reference to the local variable
        return getattr(sh, sample_var_name)
