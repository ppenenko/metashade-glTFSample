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

import argparse, os, pathlib
from pygltflib import GLTF2

from metashade.hlsl.sm6 import ps_6_0, vs_6_0
import metashade.hlsl.common as hlsl_common
import metashade.util as util

def _generate_vs_out(sh, primitive):
    with sh.vs_output('VsOut') as VsOut:
        VsOut.SV_Position('Pclip', sh.Vector4f)
        
        VsOut.texCoord('Nw', sh.Vector3f)
        if primitive.attributes.TANGENT is not None:
            VsOut.texCoord('Tw', sh.Vector3f)
            VsOut.texCoord('Bw', sh.Vector3f)

        VsOut.texCoord('UV0', sh.Point2f)

def _generate_per_frame_uniform_buffer(sh):
    sh.struct('Light')(
        VpXf = sh.Matrix4x4f,
        ViewXf = sh.Matrix4x4f,
        direction = sh.Vector3f,
        range = sh.Float,
        color = sh.RgbF,
        intensity = sh.Float,
        position = sh.Point3f,
        innerConeCos = sh.Float,
        outerConeCos = sh.Float,
        type_ = sh.Float, # should be an int, but we assume a spotlight anyway
        depthBias = sh.Float,
        shadowMapIndex = sh.Float # should be an int, unused for now
    )

    with sh.uniform_buffer(register = 0, name = 'cbPerFrame'):
        sh.uniform('g_VpXf', sh.Matrix4x4f)
        sh.uniform('g_prevVpXf', sh.Matrix4x4f)
        sh.uniform('g_VpIXf', sh.Matrix4x4f)
        sh.uniform('g_cameraPos', sh.Vector4f)
        sh.uniform('g_iblFactor', sh.Float)
        sh.uniform('g_perFrameEmissiveFactor', sh.Float)
        sh.uniform('g_invScreenResolution', sh.Float2)
        sh.uniform('g_wireframeOptions', sh.Float4)
        sh.uniform('g_mCameraCurrJitter', sh.Float2)
        sh.uniform('g_mCameraPrevJitter', sh.Float2)

        # should be an array
        for light_idx in range(0, 80):
            sh.uniform(f'g_light{light_idx}', sh.Light)

        sh.uniform('g_nLights', sh.Float)   # should be int
        sh.uniform('g_lodBias', sh.Float)

def _generate_per_object_uniform_buffer(sh, is_ps : bool):
    if is_ps:
        # https://github.com/ppenenko/Cauldron/blob/master/src/DX12/shaders/PBRPixelParams.hlsl#L33
        sh.struct('PbrFactors')(
            rgbaEmissive = sh.RgbaF,

            # pbrMetallicRoughness
            rgbaBaseColor = sh.RgbaF,
            fMetallic = sh.Float,
            fRoughness = sh.Float,

            f2Padding = sh.Float2,

            # KHR_materials_pbrSpecularGlossiness
            rgbaDiffuse = sh.RgbaF,
            rgbSpecular = sh.RgbF,
            fGlossiness = sh.Float
        )

    with sh.uniform_buffer(register = 1, name = 'cbPerObject'):
        sh.uniform('g_WorldXf', sh.Matrix4x4f) # should be 3x3
        sh.uniform('g_prevWorldXf', sh.Matrix4x4f) # should be 3x3
        if is_ps:
            sh.uniform('g_perObjectPbrFactors', sh.PbrFactors)

_vs_main = 'mainVS'

def _generate_vs(vs_file, primitive):
    sh = vs_6_0.Generator(vs_file)

    _generate_per_frame_uniform_buffer(sh)
    _generate_per_object_uniform_buffer(sh, is_ps = False)

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
            VsIn.texCoord('UV0', sh.Point2f)

        if attributes.TEXCOORD_1 is not None:
            VsIn.texCoord('UV1', sh.Point2f)

        if attributes.COLOR_0 is not None:
            VsIn.color('Color0', sh.RgbaF)

        if attributes.JOINTS_0 is not None:
            raise RuntimeError('Unsupported attribute JOINTS_0')

        if attributes.WEIGHTS_0 is not None:
            raise RuntimeError('Unsupported attribute WEIGHTS_0')

    _generate_vs_out(sh, primitive)

    with sh.main(_vs_main, sh.VsOut)(vsIn = sh.VsIn):
        sh.Pw = sh.g_WorldXf.xform(sh.vsIn.Pobj)

        sh.vsOut = sh.VsOut()
        sh.vsOut.Pclip = sh.g_VpXf.xform(sh.Pw)
        sh.vsOut.Nw = sh.g_WorldXf.xform(sh.vsIn.Nobj).xyz.normalize()
        
        if attributes.TANGENT is not None:
            sh.vsOut.Tw = sh.g_WorldXf.xform(
                sh.vsIn.Tobj.xyz.as_vector4()
            ).xyz.normalize()
            sh.vsOut.Bw = sh.vsOut.Nw.cross(sh.vsOut.Tw) * sh.vsIn.Tobj.w

        sh.vsOut.UV0 = sh.vsIn.UV0

        sh.return_(sh.vsOut)

_ps_main = 'mainPS'

def _generate_ps(ps_file, material, primitive):
    sh = ps_6_0.Generator(ps_file)

    _generate_per_frame_uniform_buffer(sh)
    _generate_per_object_uniform_buffer(sh, is_ps = True)

    _generate_vs_out(sh, primitive)

    with sh.ps_output('PsOut') as PsOut:
        PsOut.SV_Target('color', sh.RgbaF)

    texture_dict = dict()

    def _add_texture(parent, name: str, texel_type = None):
        name += 'Texture'
        if getattr(parent, name) is not None:
            texture_dict[name] = texel_type

    _add_texture(material, 'normal')
    _add_texture(material, 'occlusion')
    _add_texture(material, 'emissive', sh.RgbaF)

    if material.pbrMetallicRoughness is not None:
        _add_texture(
            material.pbrMetallicRoughness, 'baseColor', sh.RgbaF
        )
        _add_texture(material.pbrMetallicRoughness, 'metallicRoughness')
    elif material.extensions is not None:
        specularGlossiness = \
            material.extensions.KHR_materials_pbrSpecularGlossiness
        if specularGlossiness is not None:
            _add_texture(specularGlossiness, 'diffuse', sh.RgbaF)
            _add_texture(specularGlossiness, 'specularGlossiness')
            assert (False,
                'KHR_materials_pbrSpecularGlossiness is not implemented yet, '
                'see https://github.com/ppenenko/metashade/issues/18'
            )

    # We're sorting material textures by name
    for texture_idx, texture_name in enumerate(sorted(texture_dict)):
        sh.combined_sampler_2d(
            texture_name = texture_name,
            texture_register = texture_idx,
            sampler_name = texture_name + 'Sampler',
            sampler_register = texture_idx,
            texel_type = texture_dict[texture_name]
        )

    with sh.main(_ps_main, sh.PsOut)(psIn = sh.VsOut):
        def _sample_texture(texture_name : str):
            texture_name += 'Texture'
            gltf_texture = getattr(material, texture_name)
            if gltf_texture is None:
                return None
            uv_set_idx = gltf_texture.texCoord
            if uv_set_idx is None:
                uv_set_idx = 0
            uv = getattr(sh.psIn, f'UV{uv_set_idx}')
            sampler = getattr(sh, texture_name + 'Sampler')
            return sampler(uv)

        normalSample = _sample_texture('normal')
        if (normalSample is not None
            and primitive.attributes.TANGENT is not None
        ):
            sh.tbn = sh.Matrix3x3f(rows = (sh.psIn.Tw, sh.psIn.Bw, sh.psIn.Nw))
            sh.tbn = sh.tbn.transpose()
            sh.Nw = sh.tbn.xform(2.0 * normalSample.xyz - sh.Float3(1.0))
        else:
            print ('TODO: https://github.com/ppenenko/metashade/issues/19')
            sh.Nw = sh.psIn.Nw
        sh.Nw = sh.Nw.normalize()

        sh.lambert = sh.g_light0.direction.dot(sh.Nw).saturate()
        sh.baseColor = sh.baseColorTextureSampler(sh.psIn.UV0)
        
        sh.psOut = sh.PsOut()
        sh.psOut.color.rgb = sh.lambert * sh.baseColor.rgb
        sh.psOut.color.a = sh.baseColor.a

        aoSample = _sample_texture('occlusion')
        if aoSample is not None:
            sh.psOut.color.rgb = sh.psOut.color.rgb * aoSample.x

        sh.emissive = sh.g_perObjectPbrFactors.rgbaEmissive.rgb * sh.g_perFrameEmissiveFactor
        emissiveSample = _sample_texture('emissive')
        if emissiveSample is not None:
            sh.emissive = sh.emissive * emissiveSample.rgb
        sh.psOut.color.rgb = sh.psOut.color.rgb + sh.emissive

        sh.return_(sh.psOut)

def main(gltf_dir : str, out_dir : str, compile : bool):
    os.makedirs(out_dir, exist_ok = True)

    for gltf_file_path in pathlib.Path(gltf_dir).glob('**/*.gltf'):
        with util.TimedScope(f'Loading glTF asset {gltf_file_path} '):
            gltf_asset = GLTF2().load(gltf_file_path)

        for mesh_idx, mesh in enumerate(gltf_asset.meshes):
            mesh_name = ( mesh.name if mesh.name is not None
                else f'UnnamedMesh{mesh_idx}'
            )

            for primitive_idx, primitive in enumerate(mesh.primitives):
                def _file_name(stage : str):
                    return os.path.join(
                        out_dir,
                        f'{mesh_name}-{primitive_idx}-{stage}.hlsl'
                    )

                file_name = _file_name('VS')
                with util.TimedScope(f'Generating {file_name} ', 'Done'), \
                    open(file_name, 'w') as vs_file:
                    _generate_vs(vs_file, primitive)
                if compile:
                    assert 0 == hlsl_common.compile(
                        path = file_name,
                        entry_point_name = _vs_main,
                        profile = 'vs_6_0'
                    )

                file_name = _file_name('PS')
                with util.TimedScope(f'Generating {file_name} ', 'Done'), \
                    open(file_name, 'w') as ps_file:
                    _generate_ps(
                        ps_file,
                        gltf_asset.materials[primitive.material],
                        primitive
                    )
                if compile:
                    assert 0 == hlsl_common.compile(
                        path = file_name,
                        entry_point_name = _ps_main,
                        profile = 'ps_6_0'
                    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "Generate shaders from glTF materials."
    )
    parser.add_argument("--gltf-dir", help = "Path to the source glTF assets")
    parser.add_argument("--out-dir", help = "Path to the output directory")
    parser.add_argument(
        "--compile",
        action = 'store_true',
        help = "Compile the generated shaders with DXC (has to be in PATH)"
    )
    args = parser.parse_args()
    
    if not os.path.isdir(args.gltf_dir):
        raise NotADirectoryError(args.gltf_dir)

    main(args.gltf_dir, args.out_dir, args.compile)
