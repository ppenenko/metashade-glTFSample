# glTF Demo

This demo uses the third-party [pygltflib](https://pypi.org/project/pygltflib/) to parse glTF assets and generate HLSL shaders that can be rendered with [a fork of the Cauldron glTFSample](https://github.com/ppenenko/glTFSample/tree/metashade_demo).
The goal is to demonstrate that Metashade can generate sufficiently complex renderable shaders and that it can be integrated with other Python libraties and content production pipelines.

## generate.py usage

```
--gltf-dir GLTF_DIR  Path to the source glTF assets
--out-dir OUT_DIR    Path to the output directory
```

The script processes all glTF asset files it finds under the directory specified by `GLTF_DIR` (e.g. a local clone of the [Cauldron-Media repo](https://github.com/GPUOpen-LibrariesAndSDKs/Cauldron-Media)) and writes the generated shader files in the directory specified by `OUT_DIR`. The names of the shader files are derived from the names of glTF meshes and primitives.