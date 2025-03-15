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

from collections import OrderedDict
from typing import NamedTuple

from metashade.hlsl.sm6 import vs_6_0
from . import common, _uniforms

class VertexData:
    class _PassthruAttrDef(NamedTuple):
        gltf_name : str
        hlsl_semantic : str
        dtype : str

    def __init__(self, primitive):
        gltf_attrs = primitive.attributes

        for mandatory_attr in ('POSITION', 'NORMAL'):
            if getattr(gltf_attrs, mandatory_attr) is None:
                raise RuntimeError(f"Mandatory attribute '{mandatory_attr}' is missing")

        for unsupported_attr in ('JOINTS_0', 'WEIGHTS_0'):
            if getattr(gltf_attrs, unsupported_attr) is not None:
                raise RuntimeError(f"Unsupported attribute '{unsupported_attr}'")

        self._has_tangent = gltf_attrs.TANGENT is not None

        self._passthru_attrs = OrderedDict()
        for sl_name, attr_def in (
            ('uv0', self._PassthruAttrDef(
                'TEXCOORD_0',   'texCoord', 'Point2f'
            )),
            ('uv1', self._PassthruAttrDef(
                'TEXCOORD_1',   'texCoord', 'Point2f'
            )),
            ('rgbaColor0', self._PassthruAttrDef(
                'COLOR_0',     'color',     'RgbaF'
            ))
        ):
            if getattr(gltf_attrs, attr_def.gltf_name) is not None:
                self._passthru_attrs[sl_name] = attr_def
    
    def get_id(self) -> str:
        optional_attrs = list(self._passthru_attrs.keys())
        if self._has_tangent:
            optional_attrs.append('Tobj')
        return '_'.join(sorted(optional_attrs))

    def _generate_vs_in(self, sh):
        # TODO: for Vulkan, the attributes' locations follow the order of the attributes in the glTF asset:
        # https://github.com/metashade/Cauldron/blob/metashade_demo/src/VK/GLTF/GltfPbrPass.cpp#L204
        # https://github.com/metashade/Cauldron/blob/metashade_demo/src/VK/GLTF/GLTFTexturesAndBuffers.cpp#L207
        #
        with sh.vs_input('VsIn') as VsIn:
            VsIn.position('Pobj', sh.Point3f)
            VsIn.normal('Nobj', sh.Vector3f)

            if self._has_tangent:
                VsIn.tangent('Tobj', sh.Vector4f)

            for sl_name, attr_def in self._passthru_attrs.items():
                semantic_func = getattr(VsIn, attr_def.hlsl_semantic)
                semantic_func(
                    sl_name, getattr(sh, attr_def.dtype)
                )

    _vs_out_attr_dtypes = {
        'Pclip' : 'Vector4f',
        'Pw'    : 'Point3f',
        'Nw'    : 'Vector3f',
        'Tw'    : 'Vector3f',
        'Bw'    : 'Vector3f'
    }

    def generate_vs_out(self, sh):
        with sh.vs_output('VsOut') as VsOut:
            def add_attr(semantic_name, attr_name):
                dtype = self._vs_out_attr_dtypes[attr_name]
                dtype = getattr(sh, dtype)
                semantic_func = getattr(VsOut, semantic_name)
                semantic_func(attr_name, dtype)

            add_attr('SV_Position', 'Pclip')

            add_attr('texCoord', 'Pw')
            add_attr('texCoord', 'Nw')

            if self._has_tangent:
                add_attr('texCoord', 'Tw')
                add_attr('texCoord', 'Bw')

            for sl_name, attr_def in self._passthru_attrs.items():
                dtype = getattr(sh, attr_def.dtype)
                semantic_func = getattr(VsOut, attr_def.hlsl_semantic)
                semantic_func( sl_name, dtype )

    def generate_legacy_vs_out(self, sh):
        # TODO: for compatibility with the original Vulkan demo, we should
        # generate a regular struct with an instance at location 0
        # https://github.com/metashade/Cauldron/blob/metashade_demo/src/VK/shaders/GLTF_VS2PS_IO.glsl
        #
        
        struct_members = OrderedDict()

    def generate_vs(self, vs_file):
        sh = vs_6_0.Generator(
            vs_file,
            # the host app supplies transposed matrix uniforms
            matrix_post_multiplication = True
        )

        _uniforms.generate(sh, for_ps = False)

        self._generate_vs_in(sh)
        self.generate_vs_out(sh)

        with sh.entry_point(common.entry_point_name, sh.VsOut)(vsIn = sh.VsIn):
            sh.Pw = sh.g_WorldXf.xform(sh.vsIn.Pobj)
            sh.vsOut = sh.VsOut()
            sh.vsOut.Pclip = sh.g_VpXf.xform(sh.Pw)
            sh.vsOut.Pw = sh.Pw.xyz
            sh.vsOut.Nw = sh.g_WorldXf.xform(sh.vsIn.Nobj).xyz.normalize()
            
            if self._has_tangent:
                sh.vsOut.Tw = sh.g_WorldXf.xform(sh.vsIn.Tobj.xyz).xyz.normalize()
                sh.vsOut.Bw = sh.vsOut.Nw.cross(sh.vsOut.Tw) * sh.vsIn.Tobj.w

            # Simple passthrough for these attributes
            for sl_name in self._passthru_attrs.keys():
                setattr(sh.vsOut, sl_name, getattr(sh.vsIn, sl_name))

            sh.return_(sh.vsOut)
