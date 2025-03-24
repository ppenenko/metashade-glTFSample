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

import math, sys
from metashade.modules import export

@export
def D_Ggx(sh, NdotH : 'Float', fAlphaRoughness : 'Float') -> 'Float':
    sh // "https://google.github.io/filament/Filament.md.html#materialsystem/specularbrdf/normaldistributionfunction(speculard)"
    sh // ""
    sh.fASqr = fAlphaRoughness * fAlphaRoughness
    sh.fF = (NdotH * sh.fASqr - NdotH) * NdotH + sh.Float(1.0)
    sh.return_(
        (sh.fASqr / (sh.Float(math.pi) * sh.fF * sh.fF )).saturate()
    )

@export
def F_Schlick(sh, LdotH : 'Float', rgbF0 : 'RgbF') -> 'RgbF':
    sh.return_(
        rgbF0 + (sh.RgbF(1.0) - rgbF0)
            * (sh.Float(1.0) - LdotH).pow(sh.Float(5.0))
    )

@export
def V_SmithGgxCorrelated(
    sh,
    NdotV : 'Float',
    NdotL : 'Float',
    fAlphaRoughness : 'Float'
) -> 'Float':
    sh // "https://google.github.io/filament/Filament.md.html#materialsystem/specularbrdf/geometricshadowing(specularg)"
    sh // ""
    sh.fASqr = fAlphaRoughness * fAlphaRoughness
    sh.fGgxL = NdotV * (
        (NdotL - NdotL * sh.fASqr) * NdotL + sh.fASqr
    ).sqrt()
    sh.fGgxV = NdotL * (
        (NdotV - NdotV * sh.fASqr) * NdotV + sh.fASqr
    ).sqrt()
    sh.fV = sh.Float(0.5) / (sh.fGgxL + sh.fGgxV)
    sh.return_(sh.fV.saturate())

@export
def Fd_Lambert(sh) -> 'Float':
    sh.return_( sh.Float( 1.0 / math.pi ) )

@export
def pbrBrdf(
    sh, L : 'Vector3f', N : 'Vector3f', V : 'Vector3f', pbrParams : 'PbrParams'
) -> 'RgbF':
    sh.NdotV = (N @ V).abs()
    sh.NdotL = (N @ L).saturate()

    sh.H = (V + L).normalize()
    sh.NdotH = (N @ sh.H).saturate()
    sh.LdotH = (L @ sh.H).saturate()

    sh.fAlphaRoughness = ( pbrParams.fPerceptualRoughness
        * pbrParams.fPerceptualRoughness
    )

    sh.fD = sh.D_Ggx(
        NdotH = sh.NdotH,
        fAlphaRoughness = sh.fAlphaRoughness
    )
    sh.rgbF = sh.F_Schlick(
        LdotH = sh.LdotH, rgbF0 = pbrParams.rgbF0
    )
    sh.fV = sh.V_SmithGgxCorrelated(
        NdotV = sh.NdotV,
        NdotL = sh.NdotL,
        fAlphaRoughness = sh.fAlphaRoughness
    )

    sh.rgbFr = (sh.fD * sh.fV) * sh.rgbF
    sh.rgbFd = pbrParams.rgbDiffuse * sh.Fd_Lambert()
    
    sh.return_(sh.NdotL * (sh.rgbFr + sh.rgbFd))

@export
def getRangeAttenuation(sh, light : 'Light', d : 'Float') -> 'Float':
    # https://github.com/KhronosGroup/glTF/blob/master/extensions/2.0/Khronos/KHR_lights_punctual/README.md#range-property
    # TODO: handle undefined/unlimited ranges
    sh.return_(
        (d / light.fRange).lerp(sh.Float(1), sh.Float(0)).saturate()
    )

def generate(sh):
    sh.struct('PbrParams')(
        rgbDiffuse = sh.RgbF,
        rgbF0 = sh.RgbF,
        fPerceptualRoughness = sh.Float,
        fOpacity = sh.Float
    )

    this_module = sys.modules[globals()['__name__']]
    sh.instantiate(this_module)
