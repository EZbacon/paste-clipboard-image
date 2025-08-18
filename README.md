
# Paste Clipboard Image to Shader Editor

## Description

This Blender addon lets you paste an image directly from your clipboard into the Shader Editor as an **Image Texture node**.  

It automatically installs **Pillow** if it is missing, ensuring cross-platform clipboard support.

---

## Features

- Paste images from clipboard into Shader Editor nodes.  
- Auto-install **Pillow** if not already installed.  
- Assigns pasted images to a new or active material.  
- Clean, minimal UI via addon preferences.  
- Keymap support: `Ctrl + V` in Shader Editor for quick pasting.  
- Cross-platform support: Windows, macOS, Linux.

---

## Installation

### Windows

1. Open Blender.  
2. Go to **Edit → Preferences → Add-ons → Install**.  
3. Select the `.zip` file of this addon.  
4. Enable the addon.  
5. The addon will automatically install Pillow if missing.

### macOS

1. Open Blender.  
2. Navigate to **Blender → Preferences → Add-ons → Install**.  
3. Select the `.zip` file of the addon.  
4. Enable the addon.  
5. Pillow will auto-install if needed.

### Linux

1. Open Blender.  
2. Go to **Edit → Preferences → Add-ons → Install**.  
3. Choose the `.zip` file of the addon.  
4. Enable the addon.  
5. Pillow will be installed automatically if absent.  
**Note:** Clipboard image capture may require X11; Wayland may fail.

---

## Usage

1. Select or create a mesh object in Blender.  
2. Open the Shader Editor.  
3. Paste an image from your clipboard using:
   - `Ctrl + V` (keymap)
   - Or via **Add → Paste Clipboard Image** menu.  
4. The addon will automatically:
   - Save the image in your storage folder (system TEMP by default).  
   - Create a new Image Texture node in the Shader Editor.  
   - Assign the image to an active material.

### Preferences

- **Storage Folder:** Set a custom directory to save pasted images.  

---