# SWAMP — Surface Water Monitoring Platform

**User Guide** · SPARRSO

A web-based GIS viewer for analyzing rasters and vectors with a focus on surface water monitoring. SWAMP supports GeoTIFF, Shapefile (zipped), GeoJSON, and KML, with multi-band visualization, custom color ramps, data-driven styling, and per-pixel statistics.

---

## Table of contents

1. [Getting started](#getting-started)
2. [Accounts and roles](#accounts-and-roles)
3. [The interface at a glance](#the-interface-at-a-glance)
4. [Working with layers](#working-with-layers)
5. [Layer settings — styling and rendering](#layer-settings--styling-and-rendering)
   - [Raster: render mode and band selection](#raster-render-mode-and-band-selection)
   - [Vector: base style and width-by-attribute](#vector-base-style-and-width-by-attribute)
   - [Color: presets and custom stops](#color-presets-and-custom-stops)
   - [Outline: always-visible boundary](#outline-always-visible-boundary)
6. [Cursor statistics](#cursor-statistics)
7. [Exporting](#exporting)
8. [Admin features](#admin-features)
9. [Tips and troubleshooting](#tips-and-troubleshooting)

---

## Getting started

### First-time setup

The first user account must be created by an administrator from the command line:

```bash
venv/bin/python manage.py createsuperuser
```

Once at least one admin exists, additional users can sign up through the web interface.

### Signing in

1. Open the app in a browser. You will be redirected to `/login/`.
2. Enter your username and password and click **Sign in**.
3. New users can click **Create one** to register from the sign-in page (`/signup/`).

### Signing out

Click the door icon in the top-right of the toolbar.

---

## Accounts and roles

SWAMP has two roles:

| Role  | Capabilities |
|-------|-------------|
| **User**  | View all layers. Upload, style, and delete their own (unlocked) layers. |
| **Admin** | Everything a user can do, plus: lock layers, edit any layer regardless of lock or ownership, manage other users (promote/demote/deactivate). |

Your role is shown as a chip in the top-right (`USER` blue, `ADMIN` red).

---

## The interface at a glance

```
┌───────────────────────────────────────────────────────────────────────────┐
│ [💧] SWAMP   Map  Satellite  Terrain  Dark        [Users] [PNG] [you] [↪]│  ← Top bar
├──────────────┬────────────────────────────────────────────────────────────┤
│ Layers (n)   │                                              ┌──────────┐  │
│ ┌──────────┐ │                                              │ Cursor   │  │
│ │ Drop     │ │                                              │ stats    │  │
│ │ files    │ │                  Map area                    │ panel    │  │
│ └──────────┘ │                                              └──────────┘  │
│              │                                                            │
│ ◉ Layer 1    │                                                            │
│   Opacity ── │                                                            │
│ ◯ Layer 2 🔒 │                                                            │
│              │                                                            │
│ ── Export ── │                  Lat: …  Lng: …                            │
│ [Save PNG]   │                                                            │
└──────────────┴────────────────────────────────────────────────────────────┘
```

- **Top bar** — branding, base-map switcher, top-level actions (PNG export, user management, sign-out)
- **Sidebar** — file upload, layer list with per-layer controls, global export
- **Map** — Leaflet canvas with zoom controls, coordinates readout, cursor-stats panel

### Base maps

Switch the underlying basemap from the top bar:

- **Map** — OpenStreetMap
- **Satellite** — Esri World Imagery
- **Terrain** — OpenTopoMap
- **Dark** — CartoDB Dark

Only one basemap is shown at a time.

---

## Working with layers

### Uploading

Drop one or more files onto the upload area in the sidebar, or click to browse. Supported formats:

| Format | Extension | Notes |
|--------|-----------|-------|
| GeoTIFF | `.tif`, `.tiff` | Single- or multi-band; reprojected to EPSG:4326 if needed |
| ERDAS IMG | `.img` | Treated as raster |
| Shapefile | `.zip` | Zip the `.shp` together with `.dbf`, `.shx`, optional `.prj` |
| GeoJSON | `.geojson`, `.json` | Used directly |
| KML | `.kml` | Read via Fiona's KML driver |

While a file is being processed, the layer appears with a **Processing** badge. If processing fails, an **Error** badge appears (hover for details).

#### Locking on upload (admin only)

When signed in as an admin, a **Lock layer (admin-only edits)** checkbox appears below the drop zone. Layers uploaded with this option set become read-only for non-admins from the moment they appear in the list. Lock state can also be toggled later — see [Admin features](#admin-features).

### The layer item

Each layer in the sidebar is rendered as a row with two parts: a header row and an opacity slider. Hovering reveals action buttons on the right.

```
👁 [type-icon] Layer name [🔒]   [⚙][🔍][⤓][🗑]
   Opacity ────●──────────  60%
```

| Control | Action |
|---------|--------|
| **Eye** | Toggle visibility (also dims/restores the always-on outline) |
| **Type icon** | Quick visual cue: orange = raster, green = vector |
| **Lock badge 🔒** | Shown when the layer is admin-locked |
| **⚙ Sliders** | Open the per-layer settings panel ([details](#layer-settings--styling-and-rendering)) |
| **🔍 Expand** | Zoom and pan the map to the layer's bounding box |
| **⤓ Download** | Export the original file (GeoTIFF or GeoJSON) |
| **🗑 Trash** | Delete the layer (disabled when you can't edit it) |
| **🔒/🔓** | Admins only — toggle lock state |
| **Opacity slider** | 0–100%; persists between sessions for editable layers |

Locked layers display a left-edge yellow stripe so they are visually distinct in the list.

#### What changes when a layer is locked?

- Non-admins cannot change opacity, visibility-persisted-across-sessions, style, name, outline, or delete.
- Non-admins **can still toggle the layer on/off in their own session view** — the toggle just doesn't persist to the server.
- Admins can edit and delete any layer regardless of lock state.

---

## Layer settings — styling and rendering

Click the **⚙ sliders** icon on a layer to open the settings panel beneath it. The panel has tabs that vary by layer type:

- **Raster:** *Render · Color · Outline*
- **Vector:** *Style · Data Color · Outline*

If you don't have edit rights, the panel still opens (read-only) with a yellow "Locked by admin" notice and disabled controls.

### Raster: render mode and band selection

The **Render** tab controls how a multi-band raster is converted to pixels on the map.

| Setting | Description |
|---------|-------------|
| **Mode → Single band** | Pick one band; values are mapped through the color ramp from the **Color** tab |
| **Mode → RGB composite** | Pick three bands to drive the red, green, blue channels (requires ≥3 bands) |
| **Band** *(single mode)* | Index of the band to display (1 = first) |
| **Red / Green / Blue** *(RGB mode)* | Band index for each channel; per-channel values are stretched between the band's min/max |

Newly uploaded multi-band rasters default to RGB with bands 1/2/3; single-band rasters default to the **viridis** color ramp.

### Vector: base style and width-by-attribute

The **Style** tab provides a flat default style plus a data-driven width mapping.

#### Base style

| Setting | Description |
|---------|-------------|
| **Color** | Stroke and fill color (hex). The text input mirrors the picker for direct entry. |
| **Stroke** | Default line width in pixels (0.5–10) |
| **Fill α** | Polygon fill opacity (0–1, independent of layer opacity) |

#### Stroke width by attribute

Use this to make wider rivers render thicker, larger flooded polygons more emphasized, etc.

1. **Attribute** — select a numeric property from your features (auto-discovered from the first 50 features when the panel opens)
2. **Value range (min / max)** — the data range to map (e.g. discharge values 0–2000)
3. **Width range (min / max)** — the pixel width range to map onto (e.g. 1–8)

Higher attribute values become thicker strokes. Leave **Attribute** as `— none —` to use the flat **Stroke** width.

### Color: presets and custom stops

Both the raster **Color** tab and the vector **Data Color** tab share the same controls. For vectors, choose an **Attribute** first; for rasters, the active band's values drive the ramp.

#### Presets

Built-in color ramps:

| Preset | Use case |
|--------|----------|
| `viridis` | Default — perceptually uniform, colorblind-friendly |
| `magma` | Like viridis, warmer |
| `blues` | Sequential blue — classic for water depth |
| `reds` | Sequential red — emphasis for damage/hazard |
| `water` | Custom dark-blue → cyan, ideal for surface water extent |
| `flood` | Diverging brown ↔ teal, ideal for flood vs dry classification |
| `rainbow` | Full spectrum (use with caution; not perceptually uniform) |

#### Range

Two number inputs (`min` / `max`) define the data range mapped onto the ramp. For rasters, sensible defaults are pre-computed per band; you can clip to focus on a sub-range (e.g. show only flood values 0.5–1.0).

#### Custom stops

Switch the preset dropdown to **custom stops** to enable manual control:

```
[ value ] [ █ color ] [×]
[ value ] [ █ color ] [×]
[ + Add stop ]
```

- Each row pairs a numeric value with a color
- At least 2 stops are required
- Click a row's **×** to remove it; click **+ Add stop** to insert a new one (defaults to mid-range)
- Stops are automatically sorted and used as a multi-color gradient

A live preview bar above the stops reflects the current ramp.

### Outline: always-visible boundary

The **Outline** tab controls a thin reference rectangle drawn around the layer's bounding box. This rectangle is **always rendered at full opacity**, so even when the layer itself is faded to 5% opacity, the boundary stays clearly visible.

| Setting | Description |
|---------|-------------|
| **Visible** | Show or hide the boundary |
| **Color** | Outline color |
| **Width** | Stroke width in pixels (0.5–6) |

The outline auto-hides when the layer's eye toggle is off.

---

## Cursor statistics

When the mouse hovers over a visible raster, a panel appears in the top-right of the map with:

- **Layer** — name of the topmost raster under the cursor (highest `z_index` wins)
- **Value** *(or per-band values for multi-band rasters)* — pixel value at the cursor location
- **Pixel area** — physical area covered by one pixel, expressed in the most readable unit:
  - `m²` for very fine pixels
  - `ha` for medium pixels
  - `km²` for coarse pixels
- **Pixel** — `[row, col]` index in the source raster

Pixel area is computed from the raster's pixel size in degrees and converted using a latitude-corrected approximation (`1° lat ≈ 111,320 m`). For typical surface-water and flood rasters in EPSG:4326 this is accurate enough to inform decisions like *"how many km² of this flood polygon is one pixel?"*

The panel hides itself when the cursor moves off the map or onto an area not covered by any raster.

---

## Exporting

### Whole map as PNG

Two equivalent buttons:

- **Export PNG** in the top bar
- **Save map as PNG** at the bottom of the sidebar

Both render the current map view (basemap + all visible layers) to a PNG and download it as `swamp-map.png`. The export uses `leaflet-image` and includes vector overlays.

### Individual layer

Click the **⤓ Download** action on any layer to retrieve the source file:

- **Rasters** download the GeoTIFF as `<layer-name>.tif`
- **Vectors** (Shapefile / GeoJSON / KML) download the GeoJSON cache as `<layer-name>.geojson`

These are the original files (or processed-and-reprojected for rasters), not styled snapshots.

---

## Admin features

Admins (Django staff or superusers) see two extra UI elements:

1. **Lock toggle** on every layer item (next to the settings button)
2. **Users** button in the top-bar

### Locking and unlocking layers

Click the **🔓 / 🔒** icon on a layer's row to toggle its lock state. Locked layers:

- Show a yellow lock badge in the layer list
- Show a yellow left-edge stripe
- Reject style/opacity/name/delete operations from non-admins (HTTP 403)

Use this to publish reference layers (administrative boundaries, baseline surface-water extent) that all users see but no one can accidentally restyle or delete.

### User access management

Click the **Users** button to open the user management modal:

| Column | Description |
|--------|-------------|
| **Username** | The user's login name (your own row is marked "you") |
| **Email** | Optional contact email |
| **Admin** | Checkbox — promotes or demotes admin status (`is_staff`) |
| **Active** | Checkbox — uncheck to disable a user (they cannot log in) |

Changes are saved instantly. You cannot change your own admin/active flags from the UI; use `manage.py` for that to avoid locking yourself out.

For deeper user management (passwords, groups, permissions), use the Django admin at `/admin/`.

---

## Tips and troubleshooting

### Boundary still visible at low opacity?
That's the design — the **Outline** is rendered separately at full opacity so that even faded layers remain locatable. Hide it from the **Outline** tab if you want a fully fading layer.

### Cursor stats panel doesn't appear
- The cursor must be over a **visible** raster (not vector). Vector layers are not sampled.
- If multiple rasters overlap, the one with the highest **z_index** wins.
- Sampling is debounced 80ms — pause briefly over a pixel.

### Color ramp looks washed out
Open the **Color** tab and tighten the **Range** to match the data of interest. For example, if a flood-probability raster runs 0–1 but most pixels are 0.0, set range to 0.3–1.0 to focus the ramp.

### Vector attribute dropdown is empty
Attributes are auto-discovered from the first 50 features when the settings panel first opens. Wait a second after opening, then re-open the panel.

### Multi-band raster looks wrong as RGB
- Confirm at least 3 bands exist (the **Mode → RGB composite** option is disabled otherwise).
- Try different band combinations — for Sentinel-2, common composites are `4-3-2` (true color) and `8-4-3` (false color).
- Per-channel stretching uses the per-band min/max captured during upload. If a band is mostly cloud or no-data, switch to single-band mode and use a color ramp.

### My uploaded raster has no `band_stats`
Layers uploaded **before** the multi-band feature was added do not have band statistics cached. They still render via the color ramp using a default 0–1 range; tighten the range manually, or re-upload to capture stats.

### "This layer is locked. Only admins can modify it."
The layer was locked by an admin. Ask an admin to unlock it, or work on a copy you own.

### A layer fails to load
Click the layer to inspect the **Error** badge tooltip for the underlying cause. Common issues:

- Shapefile zip missing `.dbf` or `.shx`
- Raster has unsupported CRS (most should reproject automatically)
- File is corrupt or truncated

Re-upload after addressing the issue.

---

*Built on Django · Leaflet · GeoRaster · rasterio · Fiona · chroma-js*
