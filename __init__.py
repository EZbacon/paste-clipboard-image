bl_info = {
    "name": "Paste Clipboard Image to Shader Editor",
    "author": "Ryan",
    "version": (1, 0, 0),
    "blender": (4, 4, 0),
    "location": "Shader Editor",
    "description": "Paste an image from clipboard into the Shader Editor as Image Texture.",
    "tagline": "Quickly paste clipboard images as Shader nodes",
    "category": "Node",
}

import bpy, os, tempfile, time, shutil, traceback
from bpy.props import StringProperty, BoolProperty
from bpy.types import AddonPreferences, Operator

# ---------------------------
# Pillow import with auto install
# ---------------------------
_PIL_OK = True
try:
    from PIL import ImageGrab, Image
except Exception:
    _PIL_OK = False
    try:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import ImageGrab, Image
        _PIL_OK = True
    except Exception:
        _PIL_OK = False

# ---------------------------
# Addon Preferences
# ---------------------------
class PASTEIMG_AddonPrefs(AddonPreferences):
    bl_idname = __name__
    storage_dir: StringProperty(
        name="Storage Folder",
        subtype='DIR_PATH',
        description="Folder to save pasted images. Empty = system TEMP",
        default=""
    )

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(self, "storage_dir")
        col.operator("pasteimg.reset_storage_to_temp", icon="TRASH")
        col.separator()
        col.label(text="Notes", icon='INFO')
        col.label(text="- Clipboard image paste requires Pillow.")
        col.label(text="- Linux: Clipboard may require X11; Wayland may fail.")
        col.label(text="- Drag & drop is not used.")

class PASTEIMG_OT_ResetStorageToTemp(Operator):
    bl_idname = "pasteimg.reset_storage_to_temp"
    bl_label = "Reset To TEMP Folder"
    bl_description = "Reset storage folder to system TEMP"

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        prefs.storage_dir = ""
        self.report({'INFO'}, "Storage folder reset to system TEMP")
        return {'FINISHED'}

# ---------------------------
# Helpers
# ---------------------------
def _get_storage_folder(context):
    prefs = context.preferences.addons[__name__].preferences
    path = (prefs.storage_dir or "").strip()
    if path:
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except Exception:
            pass
    return tempfile.gettempdir()

def _sanitize_filename(name):
    keep = "-_.() "
    return "".join(c for c in name if c.isalnum() or c in keep)

def _timestamp_name(ext=".png"):
    return f"clipboard_{time.strftime('%Y%m%d_%H%M%S')}{ext}"

def _ensure_active_material(context):
    obj = context.active_object
    if not obj or obj.type not in {'MESH','CURVE','SURFACE','META','FONT','VOLUME','GPENCIL'}:
        return None, None, "No valid active object for shader nodes."
    mat = obj.active_material
    if not mat:
        mat = bpy.data.materials.new("PastedImageMaterial")
        obj.active_material = mat
    if not mat.use_nodes:
        mat.use_nodes = True
    return mat, mat.node_tree.nodes, None

def _node_tree_from_context(context):
    space = context.space_data
    if getattr(space, "type", None) == 'NODE_EDITOR' and getattr(space, "tree_type", "") == 'ShaderNodeTree':
        if getattr(space, "edit_tree", None):
            return space.edit_tree
    mat, _, err = _ensure_active_material(context)
    return mat.node_tree if mat else None

def _cursor_location(context):
    space = context.space_data
    if getattr(space, "type", None) == 'NODE_EDITOR':
        try:
            return space.cursor_location
        except Exception:
            pass
    return (0.0, 0.0)

def _create_image_node(context, image_path):
    ntree = _node_tree_from_context(context)
    if not ntree:
        raise RuntimeError("No valid Shader node tree.")
    nodes = ntree.nodes
    image = None
    for img in bpy.data.images:
        if bpy.path.abspath(img.filepath) == bpy.path.abspath(image_path):
            image = img
            break
    if not image:
        image = bpy.data.images.load(image_path)
    node = nodes.new("ShaderNodeTexImage")
    node.image = image
    display_name = os.path.splitext(os.path.basename(image_path))[0]
    node.label = display_name
    node.name = f"Image Texture ({display_name})"
    loc = _cursor_location(context)
    try:
        node.location = (loc[0], loc[1])
    except Exception:
        pass
    return node

def _save_clipboard_image(pil_image, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    filename = _timestamp_name(".png")
    dest_path = os.path.join(dest_dir, filename)
    base, ext = os.path.splitext(dest_path)
    i = 1
    while os.path.exists(dest_path):
        dest_path = f"{base}_{i}{ext}"
        i += 1
    pil_image.save(dest_path, format="PNG")
    return dest_path

def _copy_file_to_storage(src_path, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    base = _sanitize_filename(os.path.basename(src_path)) or _timestamp_name(".png")
    dest_path = os.path.join(dest_dir, base)
    base_name, ext = os.path.splitext(dest_path)
    i = 1
    while os.path.exists(dest_path):
        dest_path = f"{base_name}_{i}{ext}"
        i += 1
    shutil.copy2(src_path, dest_path)
    return dest_path

# ---------------------------
# Main Operator
# ---------------------------
class NODE_OT_paste_clipboard_image(Operator):
    bl_idname = "node.paste_clipboard_image"
    bl_label = "Paste Clipboard Image (Shader)"
    bl_options = {'REGISTER','UNDO'}

    verbose_errors: BoolProperty(default=False)

    def execute(self, context):
        if not _PIL_OK:
            self.report({'ERROR'}, "Pillow not available. Install Pillow to use clipboard paste.")
            return {'CANCELLED'}
        try:
            clip = ImageGrab.grabclipboard()
        except Exception as e:
            if self.verbose_errors: print(traceback.format_exc())
            self.report({'ERROR'}, f"Clipboard access failed: {e}")
            return {'CANCELLED'}
        if clip is None:
            self.report({'ERROR'}, "Clipboard has no image.")
            return {'CANCELLED'}
        dest_dir = _get_storage_folder(context)
        try:
            if isinstance(clip, list):
                image_files = [p for p in clip if isinstance(p,str) and os.path.isfile(p)]
                if not image_files:
                    self.report({'ERROR'}, "Clipboard list has no valid image files.")
                    return {'CANCELLED'}
                image_path = _copy_file_to_storage(image_files[0], dest_dir)
            elif isinstance(clip, Image.Image):
                image_path = _save_clipboard_image(clip, dest_dir)
            else:
                self.report({'ERROR'}, "Unsupported clipboard content.")
                return {'CANCELLED'}
            _ensure_active_material(context)
            _create_image_node(context, image_path)
        except Exception as e:
            if self.verbose_errors: print(traceback.format_exc())
            self.report({'ERROR'}, f"Failed to create node: {e}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Pasted image: {os.path.basename(image_path)}")
        return {'FINISHED'}

# ---------------------------
# Keymap
# ---------------------------
addon_keymaps = []
def register_keymap():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
        kmi = km.keymap_items.new(NODE_OT_paste_clipboard_image.bl_idname, 'V', 'PRESS', ctrl=True)
        addon_keymaps.append((km, kmi))

def unregister_keymap():
    for km,kmi in addon_keymaps: km.keymap_items.remove(kmi)
    addon_keymaps.clear()

# ---------------------------
# Register
# ---------------------------
classes = (PASTEIMG_AddonPrefs, PASTEIMG_OT_ResetStorageToTemp, NODE_OT_paste_clipboard_image)

def menu_func_node(self, context):
    if getattr(context.space_data, "tree_type", "") == 'ShaderNodeTree':
        self.layout.operator(NODE_OT_paste_clipboard_image.bl_idname, icon='PASTEDOWN')

def register():
    for cls in classes: bpy.utils.register_class(cls)
    bpy.types.NODE_MT_add.append(menu_func_node)
    register_keymap()

def unregister():
    unregister_keymap()
    bpy.types.NODE_MT_add.remove(menu_func_node)
    for cls in reversed(classes): bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
