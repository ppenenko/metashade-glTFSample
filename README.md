# glTF Demo

This demo uses the third-party [pygltflib](https://pypi.org/project/pygltflib/) to parse glTF assets and generate HLSL shaders that can be rendered with [a fork of the Cauldron glTFSample](https://github.com/ppenenko/glTFSample/tree/metashade_demo).
The goal is to demonstrate that Metashade can generate sufficiently complex renderable shaders and that it can be integrated with other Python libraries and content production pipelines.

## Getting started

First, clone the repo, recursing into submodules, e.g.

```bash
git clone --recurse-submodules https://github.com/ppenenko/metashade-glTFSample.git
```

This will create the following top-level directory structure:

   * [glTFSample](glTFSample) - submodule pointing at https://github.com/ppenenko/glTFSample. That repo is a fork of https://github.com/GPUOpen-LibrariesAndSDKs/glTFSample - a C++ host app, originally developed by AMD to demo the rendering of glTF assets in DX12 and Vulkan. You can read more about the functionality of the fork and the build instructions in the respective README.
      * [build](glTFSample/build) - the build directory for the above repo.
         * [DX12](glTFSample/build/DX12) - the directory where the DX12-specific solution of glTFSample is generated with CMake. It's added to [.gitignore](glTFSample/.gitignore)
      * [libs/cauldron](glTFSample/libs/cauldron) - submodule pointing at https://github.com/ppenenko/Cauldron, a fork of https://github.com/GPUOpen-LibrariesAndSDKs/Cauldron, AMD's demo rendering library.
      * [media/Cauldron-Media](glTFSample/media/Cauldron-Media) - submodule pointing at https://github.com/ppenenko/Cauldron-Media, cloned from https://github.com/GPUOpen-LibrariesAndSDKs/Cauldron-Media, which contains the glTF assets used in the demo.
   * [metashade](metashade) - submodule pointing at https://github.com/ppenenko/metashade
   * [src](src) - the code generating shaders with [metashade](metashade) which [glTFSample](glTFSample) can render with.

## generate.py usage

```
--gltf-dir  GLTF_DIR  Path to the source glTF assets
--out-dir   OUT_DIR    Path to the output directory
```

The script processes all glTF asset files it finds under the directory specified by `GLTF_DIR` and writes the generated shader files in the directory specified by `OUT_DIR`.

In order to use the generated shaders with [glTFSample](https://github.com/ppenenko/glTFSample/tree/metashade_demo),
`GLTF_DIR` has to be set to the local clone of the [Cauldron-Media](https://github.com/GPUOpen-LibrariesAndSDKs/Cauldron-Media) submodule of the glTFSample repo.

The shader files generated in `OUT_DIR` can be fed to glTFSample via a [command-line argument](https://github.com/ppenenko/glTFSample/tree/metashade_demo#command-line-interface). The names of the generated shader files are derived from the names of glTF meshes and primitives. [glTFSample](https://github.com/ppenenko/glTFSample/tree/metashade_demo) uses the same naming convention to find the right shaders at runtime and use them for rendering.
