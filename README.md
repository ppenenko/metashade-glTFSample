# glTF Demo

This demo uses the third-party [pygltflib](https://pypi.org/project/pygltflib/) to parse glTF assets and generate HLSL shaders that can be rendered with [a fork of the Cauldron glTFSample](https://github.com/ppenenko/glTFSample/tree/metashade_demo).
The goal is to demonstrate that Metashade can generate sufficiently complex renderable shaders and that it can be integrated with other Python libraries and content production pipelines.

## Getting started

First, clone the repo, recursing into submodules, e.g.

```bash
git clone --recurse-submodules https://github.com/ppenenko/metashade-glTFSample.git
```

The demo uses the following directory structure:

   * [glTFSample](https://github.com/ppenenko/glTFSample/tree/metashade_demo) - submodule pointing at https://github.com/ppenenko/glTFSample/tree/metashade_demo, which is a fork of https://github.com/GPUOpen-LibrariesAndSDKs/glTFSample - a C++ host app, originally developed by AMD to demo the rendering of glTF assets in DX12 and Vulkan.
      * [build](https://github.com/ppenenko/glTFSample/tree/metashade_demo/build) - the build directory for the above repo.
         * [DX12](glTFSample/build/DX12) - this directory will be created later by the [glTFSample](https://github.com/ppenenko/glTFSample/tree/metashade_demo) build and will contain the DX12-specific Visual Studio solution generated with CMake. It's added to [.gitignore](https://github.com/ppenenko/glTFSample/tree/metashade_demo/.gitignore).
            * [metashade-out](glTFSample/build/DX12/metashade-out) - this is where the Metashade demo will generate the HLSL shaders.
      * [libs/cauldron](https://github.com/ppenenko/Cauldron/tree/metashade_demo) - submodule pointing at https://github.com/ppenenko/Cauldron/tree/metashade_demo, a fork of https://github.com/GPUOpen-LibrariesAndSDKs/Cauldron, AMD's demo rendering framework.
      * [media/Cauldron-Media](https://github.com/ppenenko/Cauldron-Media) - submodule pointing at https://github.com/ppenenko/Cauldron-Media, cloned from https://github.com/GPUOpen-LibrariesAndSDKs/Cauldron-Media, which contains the glTF assets used in the demo.
   * [metashade](https://github.com/ppenenko/metashade) - submodule pointing at https://github.com/ppenenko/metashade
   * [src](src) - the demo code generating shaders with [metashade](https://github.com/ppenenko/metashade) for rendering with [glTFSample](https://github.com/ppenenko/glTFSample/tree/metashade_demo).

## Building [glTFSample](https://github.com/ppenenko/glTFSample/tree/metashade_demo)

Follow the build instructions in [glTFSample/readme.md](https://github.com/ppenenko/glTFSample/blob/metashade_demo/readme.md#build-instructions).

## Generating the shaders

The Python implementation of the demo requires the [pygltflib](https://pypi.org/project/pygltflib/) to be installed:

```
pip install pygltflib
```

### [src/generate.py](src/generate.py) usage

```
--gltf-dir  Path to the source glTF assets
--out-dir   Path to the output directory
```

The script processes all glTF asset files it finds under the directory specified by `--gltf-dir` and writes the generated shader files to the directory specified by `--out-dir`.

The Visual Studio Code launch configurations in [.vscode/launch.json](.vscode/launch.json) execute the above script with the command-line arguments set to the appropriate paths in the demo's directory structure.

## Rendering with the generated shaders

In order to use the generated shaders with [glTFSample](https://github.com/ppenenko/glTFSample/tree/metashade_demo), their parent directory needs to be passed to the executable via a [command-line argument](https://github.com/ppenenko/glTFSample/blob/metashade_demo/readme.md#command-line-interface):

```
cd glTFSample\bin
GLTFSample_DX12.exe --metashade-out-dir=..\build\DX12\metashade-out
```

The names of the generated shader files are derived from the names of glTF meshes and primitives. [glTFSample](https://github.com/ppenenko/glTFSample/tree/metashade_demo) uses the same naming convention to find the right shaders at runtime and use them for rendering.
