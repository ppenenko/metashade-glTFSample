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

from metashade.hlsl.sm6 import ps_6_0
from metashade.glsl import frag

from . import common, _pbr_surf_lib, _uniforms
from .material_textures import MaterialTextures
from .vertex_data import VertexData

class ps:
    def __init__(
        self,
        material,
        vertex_data : VertexData
    ):
        self._vertex_data = vertex_data
        self._material_textures = MaterialTextures(material)

        self._alpha_mode = material.alphaMode
        self._alpha_cutoff = material.alphaCutoff

    def get_id(self) -> str:
        shader_name = common.filename_prefix

        def get_alpha_mode_id():
            if self._alpha_mode == 'BLEND':
                return self._alpha_mode
            elif self._alpha_mode == 'MASK':
                return f'{self._alpha_mode}{self._alpha_cutoff}'
            else:
                return ''

        for id in (
            self._vertex_data.get_id(),
            self._material_textures.get_id(),
            get_alpha_mode_id()
        ):
            if id != '':
                shader_name += f'-{id}'
        
        shader_name += '-PS'
        return shader_name

    def generate(self, ps_file):
        sh = ps_6_0.Generator(
            ps_file,
            # the host app supplies transposed matrix uniforms
            matrix_post_multiplication = True
        )

        _uniforms.generate(sh, for_ps = True)
        self._vertex_data.generate_vs_out(sh)

        with sh.ps_output('PsOut') as PsOut:
            PsOut.SV_Target('rgbaColor', sh.RgbaF)

        _pbr_surf_lib.generate(sh)
        self._material_textures.generate_uniforms(sh)

        # continuing right after the material textures
        texture_idx = len(self._material_textures)

        # IBL texture/sampler definitions
        for ibl_texture_name, ibl_texture_type in {
            'iblBrdfLut'    : sh.Texture2d,
            'iblDiffuse'    : sh.TextureCube(sh.RgbaF),
            'iblSpecular'   : sh.TextureCube(sh.RgbaF)
        }.items():
            sh.uniform(
                common.get_texture_uniform_name(ibl_texture_name),
                ibl_texture_type,
                dx_register = texture_idx
            )
            sh.uniform(
                common.get_sampler_uniform_name(ibl_texture_name),
                sh.Sampler,
                dx_register = texture_idx
            )
            texture_idx += 1

        # The shadow map registers are hardcoded in the host app
        shadow_map_register = 9
        sh.uniform('g_tShadowMap', sh.Texture2d, dx_register = shadow_map_register)
        sh.uniform('g_sShadowMap', sh.SamplerCmp, dx_register = shadow_map_register)

        with sh.function('metallicRoughness', sh.PbrParams)(psIn = sh.VsOut):
            sh.rgbaBaseColor = (sh.g_sBaseColor @ sh.g_tBaseColor)(
                sh.psIn.uv0, lod_bias = sh.g_lodBias
            )
            sh.rgbaBaseColor *= sh.g_perObjectPbrFactors.rgbaBaseColor
            
            if hasattr(sh.psIn, 'rgbaColor0'):
                sh.rgbaBaseColor *= sh.psIn.rgbaColor0

            if self._alpha_mode == 'BLEND':
                sh.rgbaBaseColor.a.clip()
            elif self._alpha_mode == 'MASK':
                sh.fAlphaCutoff = sh.Float(float(self._alpha_cutoff))
                (sh.rgbaBaseColor.a - sh.fAlphaCutoff).clip()
            
            sh.fPerceptualRoughness = sh.g_perObjectPbrFactors.fRoughness
            sh.fMetallic = sh.g_perObjectPbrFactors.fMetallic

            metallicRoughnessSample = self._material_textures.sample_texture(
                sh, 'metallicRoughness'
            )
            if metallicRoughnessSample is not None:
                sh.fPerceptualRoughness *= metallicRoughnessSample.g
                sh.fMetallic *= metallicRoughnessSample.b

            sh.fMetallic = sh.fMetallic.saturate()
            sh.fMinF0 = sh.Float(0.04)

            sh.pbrParams = sh.PbrParams()
            sh.pbrParams.rgbDiffuse = (
                sh.rgbaBaseColor.rgb * (sh.Float(1.0) - sh.fMinF0)
                * (sh.Float(1.0) - sh.fMetallic)
            )
            sh.pbrParams.rgbF0 = sh.RgbF(sh.fMetallic).lerp(
                sh.RgbF(sh.fMinF0), sh.rgbaBaseColor.rgb
            )
            sh.pbrParams.fPerceptualRoughness = sh.fPerceptualRoughness.saturate()
            sh.pbrParams.fOpacity = sh.rgbaBaseColor.a
            sh.return_(sh.pbrParams)

        with sh.function('getPcfShadow', sh.Float)(
            uv = sh.Float2,
            fCompareValue = sh.Float
        ):
            sh.fResult = sh.Float(0)
            kernel_level = 2

            # Unrolling the loop right here in Metashade
            for i in range(-kernel_level, kernel_level + 1):
                for j in range(-kernel_level, kernel_level + 1):
                    sh.fResult += (sh.g_sShadowMap @ sh.g_tShadowMap)(
                        tex_coord = sh.uv,
                        offset = sh.Int2((i, j)),
                        cmp_value = sh.fCompareValue,
                        lod = 0
                    )

            kernel_width = 2 * kernel_level + 1
            sh.fResult /= kernel_width * kernel_width
            sh.return_(sh.fResult)

        with sh.function('getSpotShadow', sh.Float)(
            light = sh.Light, Pw = sh.Point3f
        ):
            sh.p4Shadow = sh.light.VpXf.xform(sh.Pw)
            sh.p4Shadow.xyz /= sh.p4Shadow.w
            
            sh.uvShadow = (
                sh.Point2f(1.0) + sh.Point2f((sh.p4Shadow.x, -sh.p4Shadow.y))
            ) * sh.Float(0.5)
            sh.fCompareValue = sh.p4Shadow.z - sh.light.fDepthBias
            
            sh.fShadow = sh.getPcfShadow(
                uv = sh.uvShadow,
                fCompareValue = sh.fCompareValue
            )
            sh.return_(sh.fShadow)

        with sh.function('applySpotLight', sh.RgbF)(
            light = sh.Light,
            Nw = sh.Vector3f,
            Vw = sh.Vector3f,
            Pw = sh.Point3f,
            pbrParams = sh.PbrParams
        ):
            sh.Lw = sh.light.Pw - sh.Pw
            sh.fRangeAttenuation = sh.getRangeAttenuation(
                light = sh.light, d = sh.Lw.length()
            )
            sh.Lw = sh.Lw.normalize()

            sh.DdotL = sh.light.v3DirectionW @ sh.Lw
            sh.fSpotAttenuation = sh.DdotL.smoothstep(
                sh.light.fOuterConeCos, sh.light.fInnerConeCos
            )

            sh.fLightAttenuation = sh.fRangeAttenuation * sh.fSpotAttenuation
            sh.rgbLightColor = sh.light.fIntensity * sh.light.rgbColor
            sh.fShadow = sh.getSpotShadow(light = sh.light, Pw = sh.Pw)

            sh.return_( sh.pbrBrdf(
                L = sh.Lw,
                N = sh.Nw,
                V = sh.Vw,
                pbrParams = sh.pbrParams
            ) * sh.fLightAttenuation * sh.rgbLightColor * sh.fShadow )

        with sh.function('getIbl', sh.RgbF)(
            pbrParams = sh.PbrParams,
            N = sh.Vector3f,
            V = sh.Vector3f
        ):
            sh.NdotV = (sh.N @ sh.V).saturate()
            sh.fNumMips = sh.Float(9)
            sh.fLod = sh.pbrParams.fPerceptualRoughness * sh.fNumMips
            sh.R = (-sh.V).reflect(sh.N).normalize()

            sh.f2BrdfSamplePoint = sh.Float2(
                (sh.NdotV, sh.pbrParams.fPerceptualRoughness)
            ).saturate()

            sh.f2Brdf = (sh.g_sIblBrdfLut @ sh.g_tIblBrdfLut)(sh.f2BrdfSamplePoint).xy

            sh.rgbDiffuseLight = (sh.g_sIblDiffuse @ sh.g_tIblDiffuse)(sh.N).rgb
            sh.rgbSpecularLight = (sh.g_sIblSpecular @ sh.g_tIblSpecular)(
                sh.R, lod = sh.fLod
            ).rgb

            sh.rgbDiffuse = sh.rgbDiffuseLight * sh.pbrParams.rgbDiffuse
            sh.rgbSpecular = sh.rgbSpecularLight * (
                sh.pbrParams.rgbF0 * sh.f2Brdf.x + sh.RgbF(sh.f2Brdf.y)
            )
            sh.return_(sh.rgbDiffuse + sh.rgbSpecular)

        with sh.function('getNormal', sh.Vector3f)(psIn = sh.VsOut):
            sh.Nw = sh.psIn.Nw.normalize()

            normalSample = self._material_textures.sample_texture(sh, 'normal')
            if normalSample is not None:
                if hasattr(sh.psIn, 'Tw'):
                    sh.tbn = sh.Matrix3x3f(
                        rows = (
                            sh.psIn.Tw.normalize(),
                            sh.psIn.Bw.normalize(),
                            sh.Nw
                        )
                    )
                else:
                    sh.PwDx = sh.psIn.Pw.ddx()
                    sh.PwDy = sh.psIn.Pw.ddy()

                    uv = self._material_textures.get_uv(sh, 'normal')
                    sh.uvDx = uv.ddx()
                    sh.uvDy = uv.ddy()

                    sh.Tw = ( (sh.uvDy.y * sh.PwDx - sh.uvDx.y * sh.PwDy)
                        / (sh.uvDx.x * sh.uvDy.y - sh.uvDy.x * sh.uvDx.y)
                    )
                    sh.Tw = (sh.Tw - sh.Nw * (sh.Nw @ sh.Tw)).normalize()
                    sh.Bw = sh.Nw.cross(sh.Tw).normalize()
                    sh.tbn = sh.Matrix3x3f(rows = (sh.Tw, sh.Bw, sh.Nw))

                sh.Nw = sh.tbn.transpose().xform(
                    2.0 * normalSample.xyz - sh.Vector3f(1.0)
                ).normalize()

            sh.return_(sh.Nw)

        # Finally, the pixel shader entry point
        with sh.entry_point(common.entry_point_name, sh.PsOut)(psIn = sh.VsOut):
            sh.Vw = (sh.g_cameraPw - sh.psIn.Pw).normalize()
            sh.Nw = sh.getNormal(psIn = sh.psIn)
            
            sh.pbrParams = sh.metallicRoughness(psIn = sh.psIn)

            sh.psOut = sh.PsOut()
            sh.psOut.rgbaColor.a = sh.pbrParams.fOpacity

            sh.psOut.rgbaColor.rgb = sh.applySpotLight(
                light = sh.g_light0,
                Pw = sh.psIn.Pw,
                Nw = sh.Nw,
                Vw = sh.Vw,
                pbrParams = sh.pbrParams
            )
            
            sh.psOut.rgbaColor.rgb += sh.getIbl(
                pbrParams = sh.pbrParams,
                N = sh.Nw,
                V = sh.Vw
            ) * sh.g_fIblFactor

            aoSample = self._material_textures.sample_texture(sh, 'occlusion')
            if aoSample is not None:
                sh.psOut.rgbaColor.rgb *= aoSample.x

            sh.rgbEmissive = ( sh.g_perObjectPbrFactors.rgbaEmissive.rgb
                * sh.g_fPerFrameEmissiveFactor
            )
            emissiveSample = self._material_textures.sample_texture(sh, 'emissive')
            if emissiveSample is not None:
                sh.rgbEmissive *= emissiveSample.rgb
            sh.psOut.rgbaColor.rgb += sh.rgbEmissive

            sh.return_(sh.psOut)

def generate_frag(frag_file):
    sh = frag.Generator(frag_file, '450')

    sh.out_f4Color = sh.stage_output(sh.Float4, location = 0)

    with sh.entry_point('main')():
        sh.out_f4Color = sh.Float4((1.0, 0.0, 0.0, 1.0))
