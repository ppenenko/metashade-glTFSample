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

from typing import Any
from metashade.hlsl.sm6 import vs_6_0

from . import common, _uniforms

def generate(vs_file, primitive):
    sh = vs_6_0.Generator(
        vs_file,
        # the host app supplies transposed matrix uniforms
        matrix_post_multiplication = True
    )

    _uniforms.generate(sh, for_ps = False)

    attributes = primitive.attributes

    with sh.vs_input('VsIn') as VsIn:
        if attributes.POSITION is None:
            raise RuntimeError('POSITION attribute is mandatory')
        VsIn.position('Pobj', sh.Point3f)

        if attributes.NORMAL is not None:
            VsIn.normal('Nobj', sh.Vector3f)

        if attributes.TANGENT is not None:
            VsIn.tangent('Tobj', sh.Vector4f)

        if attributes.TEXCOORD_0 is not None:
            VsIn.texCoord('uv0', sh.Point2f)

        if attributes.TEXCOORD_1 is not None:
            VsIn.texCoord('uv1', sh.Point2f)

        if attributes.COLOR_0 is not None:
            VsIn.color('rgbaColor0', sh.RgbaF)

        if attributes.JOINTS_0 is not None:
            raise RuntimeError('Unsupported attribute JOINTS_0')

        if attributes.WEIGHTS_0 is not None:
            raise RuntimeError('Unsupported attribute WEIGHTS_0')

    common.generate_vs_out(sh, primitive)

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
        for attr_name in ('uv0', 'uv1', 'rgbaColor0'):
            if hasattr(sh.vsIn, attr_name):
                setattr(sh.vsOut, attr_name, getattr(sh.vsIn, attr_name))

        sh.return_(sh.vsOut)
