# mocap-browser
WIP standalone fbx viewer tool

![tool header image](docs/header_image.png)

# Requires
PyOpenGL, Python FBX SDK, numpy

numpy is only needed for the skinned mesh preview - without it the viewport falls back to
drawing skeletons on their own.

# Previewing a skinned mesh
Bones on their own are hard to read, so the viewport can drape a character over whichever
clip is loaded. Pick one through **Display > Set preview mesh...**, or right click a file
in the tree and choose **Use as preview mesh**. The mesh is matched to the clip by bone
name, so any skinned FBX built on the same skeleton works, and the choice is remembered
between sessions. Clips that carry their own meshes draw those instead.

Bones the clip doesn't have, like twist or other deformation bones, follow their nearest
parent that it does have, so they move with the limb instead of staying in bind pose.

## Per project preview mesh
Point the `MOCAP_BROWSER_CONFIG` environment variable at a json file to give a project a
default preview mesh. Depot paths are synced from perforce before they are loaded, and
`__THIS_FILE__` is replaced with the config's own path, same as in script-panel.

```json
{
  "preview_mesh": "//depot/Characters/SK_PreviewMesh.fbx"
}
```

`preview_mesh` can also be a list of paths. The first one is the default, and each one
gets its own **Display > Use project preview mesh: ...** entry.

A mesh picked by hand, or a project mesh other than the default, is remembered per
project and wins over the default. Picking the default again goes back to it.

# Install

<pre>
1. Download this package and unzip it in a good location 
    1.B (or git clone it directly if you have git installed)
2. Run installer.bat (will walk you through some options for install)
3. Restart the DCC
</pre>

# Start the tool
1. Run this script in a python tab in maya

<pre>

import mocap_browser
mocap_browser.main()

</pre>




