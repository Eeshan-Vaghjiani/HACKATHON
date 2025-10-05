# Module Placement Guide - Fixing "Module extends outside habitat envelope" Error

## Problem
You were seeing the error "Module extends outside habitat envelope" because the generated layouts were placing modules outside the boundaries of your habitat envelope.

## Solution Implemented

### 1. **Smart Layout Generation** (Backend)
The backend now:
- ✅ Reads your actual envelope dimensions (radius, height, width, etc.)
- ✅ Calculates safe placement zones (70% of envelope size for safety margin)
- ✅ Places modules within these safe zones
- ✅ Generates multiple layout options with varied module positions

### 2. **Validation System** (Frontend)
Added comprehensive validation:
- ✅ Checks if modules fit within envelope boundaries
- ✅ Validates all 8 corners of each module's bounding box
- ✅ Shows warnings if modules are too close to edges
- ✅ Displays helpful error messages with specific dimensions

### 3. **Visual Feedback** (UI)
The interface now shows:
- ✅ **Envelope Dimensions Panel**: Shows your current envelope size
- ✅ **Safe Placement Zone**: Displays recommended placement boundaries
- ✅ **Validation Warnings**: Alerts you if modules extend outside
- ✅ **Real-time Feedback**: Immediate validation when layouts are generated

## How to Use

### Step 1: Check Your Envelope Size
Before generating layouts, note your envelope dimensions in the **Volume Builder** tab:
- **Cylinder**: Radius and Height
- **Box**: Width, Depth, and Height
- **Torus**: Major Radius and Minor Radius

### Step 2: Generate Layouts
1. Go to the **Layout Generation** tab
2. You'll see a blue info panel showing:
   - Your envelope dimensions
   - Safe placement zone recommendations
3. Click **Generate Layouts**

### Step 3: Review Results
- If modules fit properly: ✅ Layouts will display normally
- If modules extend outside: ⚠️ You'll see a warning message
- The system will still show the layouts but highlight the issue

## Troubleshooting

### If you still see "Module extends outside envelope":

#### Option 1: Increase Envelope Size
1. Go back to **Volume Builder** tab
2. Increase the dimensions:
   - **Cylinder**: Increase radius or height
   - **Box**: Increase width, depth, or height
   - **Torus**: Increase minor radius
3. Regenerate layouts

#### Option 2: Regenerate Layouts
- Click **Generate Layouts** again
- The system uses randomization, so new layouts may fit better

#### Option 3: Reduce Number of Modules
- In the future, you'll be able to specify fewer modules
- Fewer modules = easier to fit within envelope

## Technical Details

### Safe Placement Zones
The system uses these safety margins:
- **Cylinder**: 70% of radius, 70% of height
- **Box**: 70% of smallest dimension
- **Torus**: 60% of minor radius

### Module Sizes (Default)
- Sleep Quarter: 2m × 2m × 2.5m
- Galley: 2.5m × 2.5m × 2.5m
- Laboratory: 3m × 3m × 2.5m
- Airlock: 2m × 2m × 2m

### Validation Logic
For each module, the system checks:
1. All 8 corners of the module's bounding box
2. Whether each corner is inside the envelope geometry
3. Distance from envelope boundaries
4. Clearance for safe operation

## Examples

### Good Configuration (No Errors)
```
Envelope: Cylinder
- Radius: 8m
- Height: 15m

Result: ✅ All modules fit comfortably
Safe Zone: 5.6m radius, 10.5m height
```

### Problematic Configuration (Errors)
```
Envelope: Cylinder
- Radius: 3m
- Height: 5m

Result: ⚠️ Modules extend outside
Safe Zone: 2.1m radius, 3.5m height
(Too small for standard modules)
```

### Fixed Configuration
```
Envelope: Cylinder
- Radius: 6m (increased from 3m)
- Height: 10m (increased from 5m)

Result: ✅ All modules fit properly
Safe Zone: 4.2m radius, 7m height
```

## Recommended Envelope Sizes

### For Small Habitats (2-4 modules):
- **Cylinder**: Radius ≥ 5m, Height ≥ 8m
- **Box**: 10m × 10m × 8m
- **Torus**: Major Radius ≥ 8m, Minor Radius ≥ 3m

### For Medium Habitats (5-8 modules):
- **Cylinder**: Radius ≥ 7m, Height ≥ 12m
- **Box**: 15m × 15m × 10m
- **Torus**: Major Radius ≥ 12m, Minor Radius ≥ 4m

### For Large Habitats (9+ modules):
- **Cylinder**: Radius ≥ 10m, Height ≥ 15m
- **Box**: 20m × 20m × 12m
- **Torus**: Major Radius ≥ 15m, Minor Radius ≥ 5m

## Future Enhancements

Coming soon:
- 🔄 Auto-resize envelope to fit modules
- 📏 Custom module sizes
- 🎯 Manual module placement with drag-and-drop
- 🔍 Visual boundary indicators in 3D view
- ⚙️ Configurable safety margins

## Need Help?

If you continue to see placement errors:
1. Check the blue info panel for your current envelope size
2. Compare with recommended sizes above
3. Increase envelope dimensions in Volume Builder
4. Regenerate layouts

The system is now much smarter about placing modules within your envelope boundaries!
