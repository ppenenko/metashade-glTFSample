"""
Common PBR surface functions that don't change with permutations.
TODO: generate once and include in all pixel shaders.
"""

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

import math

def generate(sh):
    sh.struct('PbrParams')(
        rgbDiffuse = sh.RgbF,
        rgbF0 = sh.RgbF,
        fPerceptualRoughness = sh.Float,
        fOpacity = sh.Float
    )

    sh // "https://google.github.io/filament/Filament.md.html#materialsystem/specularbrdf/normaldistributionfunction(speculard)"
    sh // ""
    with sh.function('D_Ggx', sh.Float)(
        NdotH = sh.Float, fAlphaRoughness = sh.Float
    ):
        sh.fASqr = sh.fAlphaRoughness * sh.fAlphaRoughness
        sh.fF = (sh.NdotH * sh.fASqr - sh.NdotH) * sh.NdotH + sh.Float(1.0)
        sh.return_(
            (sh.fASqr / (sh.Float(math.pi) * sh.fF * sh.fF )).saturate()
        )

    with sh.function('F_Schlick', sh.RgbF)(LdotH = sh.Float, rgbF0 = sh.RgbF):
        sh.return_(
            sh.rgbF0 + (sh.RgbF(1.0) - sh.rgbF0)
                * (sh.Float(1.0) - sh.LdotH).pow(sh.Float(5.0))
        )

    sh // "https://google.github.io/filament/Filament.md.html#materialsystem/specularbrdf/geometricshadowing(specularg)"
    sh // ""
    with sh.function('V_SmithGgxCorrelated', sh.Float)(
        NdotV = sh.Float, NdotL = sh.Float, fAlphaRoughness = sh.Float
    ):
        sh.fASqr = sh.fAlphaRoughness * sh.fAlphaRoughness
        sh.fGgxL = sh.NdotV * (
            (sh.NdotL - sh.NdotL * sh.fASqr) * sh.NdotL + sh.fASqr
        ).sqrt()
        sh.fGgxV = sh.NdotL * (
            (sh.NdotV - sh.NdotV * sh.fASqr) * sh.NdotV + sh.fASqr
        ).sqrt()
        sh.fV = sh.Float(0.5) / (sh.fGgxL + sh.fGgxV)
        sh.return_(sh.fV.saturate())

    with sh.function('Fd_Lambert', sh.Float)():
        sh.return_( sh.Float( 1.0 / math.pi ) )

    with sh.function('pbrBrdf', sh.RgbF)(
        L = sh.Vector3f, N = sh.Vector3f, V = sh.Vector3f,
        pbrParams = sh.PbrParams
    ):
        sh.NdotV = (sh.N @ sh.V).abs()
        sh.NdotL = (sh.N @ sh.L).saturate()

        sh.H = (sh.V + sh.L).normalize()
        sh.NdotH = (sh.N @ sh.H).saturate()
        sh.LdotH = (sh.L @ sh.H).saturate()

        sh.fAlphaRoughness = ( sh.pbrParams.fPerceptualRoughness
            * sh.pbrParams.fPerceptualRoughness
        )

        sh.fD = sh.D_Ggx(
            NdotH = sh.NdotH,
            fAlphaRoughness = sh.fAlphaRoughness
        )
        sh.rgbF = sh.F_Schlick(
            LdotH = sh.LdotH, rgbF0 = sh.pbrParams.rgbF0
        )
        sh.fV = sh.V_SmithGgxCorrelated(
            NdotV = sh.NdotV,
            NdotL = sh.NdotL,
            fAlphaRoughness = sh.fAlphaRoughness
        )

        sh.rgbFr = (sh.fD * sh.fV) * sh.rgbF
        sh.rgbFd = sh.pbrParams.rgbDiffuse * sh.Fd_Lambert()
        
        sh.return_(sh.NdotL * (sh.rgbFr + sh.rgbFd))

    with sh.function('getRangeAttenuation', sh.Float)(
        light = sh.Light, d = sh.Float
    ):
        # https://github.com/KhronosGroup/glTF/blob/master/extensions/2.0/Khronos/KHR_lights_punctual/README.md#range-property
        # TODO: handle undefined/unlimited ranges
        sh.return_(
            (sh.d / sh.light.fRange).lerp(sh.Float(1), sh.Float(0)).saturate()
        )
