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

from typing import NamedTuple

from metashade.hlsl.sm6 import vs_6_0
from . import common, _uniforms

class VertexData:
    class _AttributeDef(NamedTuple):
        gltf_name : str
        sl_name : str
        hlsl_semantic : str
        dtype : str

    _optional_attribute_defs = (
        _AttributeDef('TANGENT',     'Tobj',         'tangent',  'Vector4f'),
        _AttributeDef('TEXCOORD_0',  'uv0',          'texCoord', 'Point2f'),
        _AttributeDef('TEXCOORD_1',  'uv1',          'texCoord', 'Point2f'),
        _AttributeDef('COLOR_0',     'rgbaColor0',   'color',    'RgbaF')
    )

    def __init__(self, primitive):
        attributes = primitive.attributes

        for mandatory_attr in ('POSITION', 'NORMAL'):
            if getattr(attributes, mandatory_attr) is None:
                raise RuntimeError(f"Mandatory attribute '{mandatory_attr}' is missing")

        for unsupported_attr in ('JOINTS_0', 'WEIGHTS_0'):
            if getattr(attributes, unsupported_attr) is not None:
                raise RuntimeError(f"Unsupported attribute '{unsupported_attr}'")

        self._optional_attributes = set()

        for attr in self._optional_attribute_defs:
            if getattr(attributes, attr.gltf_name) is not None:
                self._optional_attributes.add(attr.sl_name)
    
    def get_id(self) -> str:
        return '_'.join(self._optional_attributes)

    def _generate_vs_in(self, sh):
        with sh.vs_input('VsIn') as VsIn:
            VsIn.position('Pobj', sh.Point3f)
            VsIn.normal('Nobj', sh.Vector3f)

            for attr in self._optional_attribute_defs:
                if attr.sl_name in self._optional_attributes:
                    getattr(VsIn, attr.hlsl_semantic)(
                        attr.sl_name, getattr(sh, attr.dtype)
                    )

    def generate_vs_out(self, sh):
        with sh.vs_output('VsOut') as VsOut:
            VsOut.SV_Position('Pclip', sh.Vector4f)
            
            VsOut.texCoord('Pw', sh.Point3f)
            VsOut.texCoord('Nw', sh.Vector3f)

            if 'Tobj' in self._optional_attributes:
                VsOut.texCoord('Tw', sh.Vector3f)
                VsOut.texCoord('Bw', sh.Vector3f)

            for attr in self._optional_attribute_defs:
                if ( attr.sl_name != 'Tobj'
                    and attr.sl_name in self._optional_attributes
                ):
                    getattr(VsOut, attr.hlsl_semantic)(
                        attr.sl_name, getattr(sh, attr.dtype)
                    )

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
            
            if hasattr(sh.vsIn, 'Tobj'):
                sh.vsOut.Tw = sh.g_WorldXf.xform(sh.vsIn.Tobj.xyz).xyz.normalize()
                sh.vsOut.Bw = sh.vsOut.Nw.cross(sh.vsOut.Tw) * sh.vsIn.Tobj.w

            # Simple passthrough for these attributes
            for attr in self._optional_attribute_defs:
                if ( attr.sl_name != 'Tobj'
                    and attr.sl_name in self._optional_attributes
                ):
                    setattr(sh.vsOut, attr.sl_name, getattr(sh.vsIn, attr.sl_name))

            sh.return_(sh.vsOut)
