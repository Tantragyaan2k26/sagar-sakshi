---
name: Ocean Witness Tactical Console
colors:
  surface: '#0c1419'
  surface-dim: '#0c1419'
  surface-bright: '#323a40'
  surface-container-lowest: '#070f14'
  surface-container-low: '#141d22'
  surface-container: '#182126'
  surface-container-high: '#232b31'
  surface-container-highest: '#2e363c'
  on-surface: '#dbe4eb'
  on-surface-variant: '#bec8cd'
  inverse-surface: '#dbe4eb'
  inverse-on-surface: '#293137'
  outline: '#889297'
  outline-variant: '#3f484c'
  surface-tint: '#7fd1f0'
  primary: '#80d2f1'
  on-primary: '#003544'
  primary-container: '#63b6d4'
  on-primary-container: '#004658'
  inverse-primary: '#006780'
  secondary: '#edb1ff'
  on-secondary: '#4a1a5d'
  secondary-container: '#663478'
  on-secondary-container: '#dea3f0'
  tertiary: '#81d8b4'
  on-tertiary: '#003827'
  tertiary-container: '#65bc99'
  on-tertiary-container: '#004a35'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#b8eaff'
  primary-fixed-dim: '#7fd1f0'
  on-primary-fixed: '#001f28'
  on-primary-fixed-variant: '#004d61'
  secondary-fixed: '#f9d8ff'
  secondary-fixed-dim: '#edb1ff'
  on-secondary-fixed: '#320046'
  on-secondary-fixed-variant: '#633276'
  tertiary-fixed: '#9cf4cf'
  tertiary-fixed-dim: '#80d7b3'
  on-tertiary-fixed: '#002116'
  on-tertiary-fixed-variant: '#00513b'
  background: '#0c1419'
  on-background: '#dbe4eb'
  surface-variant: '#2e363c'
typography:
  display-lg:
    fontFamily: Space Grotesk
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 22px
    fontWeight: '500'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 22px
    letterSpacing: 0em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.01em
  mono-lg:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.02em
  mono-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.03em
  mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '400'
    lineHeight: 14px
    letterSpacing: 0.04em
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 9px
    fontWeight: '600'
    lineHeight: 12px
    letterSpacing: 0.08em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.75rem
  margin: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 1.75rem
---

## Brand & Style
The design system establishes a high-stakes, maritime mission-critical environment tailored for defense command, regulatory surveillance, and oceanographic research. Operating within maritime operations centers under low-lux lighting conditions, the interface projects composure, rigorous scientific precision, and rapid situational clarity.

The aesthetic fuses modern high-density defense consoles with precision cartography. Interfaces prioritize information hierarchy over decoration: typography is calibrated for dense telemetry, borders act as structural framing, and color is deployed strictly as semantic instrumentation (slick signatures, dark targets, verification telemetry). Ambient lighting cues and restrained teal-violet glows ground the user in a deep-sea surveillance context without inducing cognitive exhaustion during protracted watches.

## Colors
The palette is rooted in an abyssal chromatic scale, moving upward through stratified ocean layers to render physical depth and focal priority.

### Surface System
- **Abyss (`#070F14`)**: Root application backdrop; the infinite oceanic canvas.
- **Deck (`#0E1E25`)**: Primary frame, peripheral utility rails, and outer view shell.
- **Panel (`#102229`)**: Core tactical cards, telemetry readouts, and map HUDs.
- **Raised (`#16303A`)**: Elevated flyouts, hovered operational nodes, popovers, and contextual action menus.
- **Hairline Border (`#24414B`)**: Crisp 1px boundary layer standard across all panels, tables, and compartmental divisions.

### Semantic Instrumentation & Symbology
- **Primary / Sea Action (`#63B6D4`)**: Active focus states, SAR track selections, primary CTA buttons. Accentuated by a faint atmospheric glow (`rgba(143, 227, 245, 0.25)`).
- **Slick / Hydrocarbon Anomaly (`#C68DD8`)**: SAR imagery polygon delineations, slick drift trajectories, thickness gradients.
- **Alert / Dark Target (`#F0786F`)**: Non-transponding AIS vessels, correlated collision vectors, rapid spill escalations.
- **Verified / Compliant (`#6CC3A0`)**: Authorized transponders, clean bilge inspection records, confirmed port clearances.
- **Caution / Unverified (`#E3B15A`)**: Intermittent AIS signals, draft-change anomalies, pending satellite validation.

### Typographic Contrast Scale
- **Primary (`#E4EEEF`)**: Critical metrics, active coordinates, high-priority status strings.
- **Secondary (`#9BB3B9`)**: Metadata keys, column identifiers, auxiliary telemetry.
- **Muted (`#6A8790`)**: Grid markers, inactive parameters, disabled status indicators.

## Typography
Typographic execution is divided into three distinct functional lanes:

1. **Strategic Telemetry (`Space Grotesk`)**: Reserved for screen headers, critical aggregate KPI metrics, confidence scoring indicators, and map overlay titles. It provides a sharp, calculated technical character.
2. **Operational Text (`Inter`)**: Drives descriptions, incident narratives, alert dialogues, system alerts, and baseline navigational UI. Provides maximum neutral legibility across dense data clusters.
3. **Sensor Raw & Telematics (`JetBrains Mono`)**: Strict allocation for spatial coordinates (Lat/Long), MMSI/IMO registration numbers, cryptographic verification hashes, timestamp streams (UTC / IST), and bathymetric readouts. Numbers are tabular lining by default to prevent jitter during real-time data streaming.

## Layout & Spacing
The layout employs an ultra-dense, multi-pane mission console framework configured for maximum situational awareness without horizontal pagination.

### Screen Partitioning & Viewport Architecture
- **Desktop (Mission Command / 1440px+)**: A continuous fluid view consisting of a 4-tier cockpit: a compressed 48px top status rail, collapsible 320px left asset navigator, central full-bleed vector/SAR viewport, and a 380px right-hand incident attribution panel.
- **Tactical Field Display / Laptop (1024px - 1439px)**: Split-screen orientation. Right attribution panel docks into an expandable bottom drawer spanning the lower 40% of the screen.
- **Mobile Watchkeeper (<1024px)**: Single primary viewport displaying map tracking with stacked bottom-sheet drilldowns and segmented tab toggles for switching between vessel manifests and slick tracking.

### Grid & Density Rhythms
A base unit of `4px` governs tactical placement. Data rows use a compact `28px` to `32px` vertical height to ensure operators view extensive log histories without excessive scrolling. Outer margins remain tightly controlled at `1rem` (`16px`) to ensure spatial real estate belongs entirely to high-resolution geospatial imagery and tracking feeds.

## Elevation & Depth
Elevation is expressed through tonal gradation, frosted glass refraction, and targeted photonic luminance rather than diffused drop shadows.

### Atmospheric Glassmorphism & Tonal Depths
- **Ground / Map Bed (`Elevation 0`)**: `#070F14` base or raw satellite imagery viewport.
- **HUD Panels & Overlays (`Elevation 1`)**: `#102229` at `78%` opacity with `backdrop-filter: blur(12px)`. Enclosed by a crisp 1px stroke of `#24414B`.
- **Floating Controls & Modals (`Elevation 2`)**: `#16303A` solid or semi-opaque (`88%`). Outlined by `#24414B` with an inset highlight (`inset 0 1px 0 rgba(228, 238, 239, 0.08)`).

### Photonic Focus Glow
Active components, critical alerts, and selected vessels project faint radial glow rings:
- Target Selection: `box-shadow: 0 0 16px rgba(99, 182, 212, 0.25)`
- Dark Target Threat: `box-shadow: 0 0 16px rgba(240, 120, 111, 0.3)`
- Anomaly Slick Detection: `box-shadow: 0 0 16px rgba(198, 141, 216, 0.25)`

## Shapes
Geometry is restrained and architectural, maintaining discipline suited for military and maritime infrastructure.

- **Panels, Windows, HUD Frames**: Fixed radius of `10px`. Delivers structural containment without rounded aesthetic softness.
- **Interactive Controls (Inputs, Buttons, Segment Pickers)**: Standardized radius of `6px`.
- **Status Tags, Coordinate Pills, Confidence Badges**: Compact radius of `4px` or full pill (`999px`) strictly when demarcating vessel state or threat categorization.
- **Linework**: Strictly `1px` continuous or subtle broken `1px` dashes for predicted drifting polygons and AIS broadcast lapses.

## Components

### Buttons & Interactive Triggers
- **Primary / Intercept Action**: Background `#63B6D4`, text `#070F14`, font `Space Grotesk` medium. Hover state shifts to `#8FE3F5` with a `0 0 12px rgba(143, 227, 245, 0.35)` glow.
- **Secondary / Panel Toggle**: Background `#102229`, border `1px solid #24414B`, text `#E4EEEF`. Hover advances surface to `#16303A` and border to `#63B6D4`.
- **Critical / Interdiction Alert**: Background `rgba(240, 120, 111, 0.15)`, border `1px solid #F0786F`, text `#F0786F`. Pulsing glow under active threat escalation.

### Telemetry Badges & Chips
- Designed with `JetBrains Mono` at `9px` or `10px` all-caps.
- Background tint matches semantic state at `12%` opacity with a solid `1px` hairline boundary (e.g., Verified: border `#6CC3A0`, bg `rgba(108, 195, 160, 0.12)`).

### Input Fields & Filter HUDs
- Height fixed at `32px` for dense data filtering.
- Background `#0E1E25`, border `1px solid #24414B`, text `#E4EEEF`, placeholder `#6A8790`.
- Focus shifts border to `#63B6D4` with an inner border glow. Clear indicator icons use ultra-thin `1.5px` stroke vectors.

### Checkboxes & Segmented Selectors
- Checkboxes: `14px x 14px` square with `3px` corner radius. `#0E1E25` background, `#24414B` border. Active state fills with `#63B6D4` displaying an abyssal `#070F14` checkmark.
- Segmented Radios: Enclosed within a `#0E1E25` cradle; selected segment is elevated to `#16303A` with `#24414B` outline and `#E4EEEF` typography.

### Data Tables & Log Stream
- Alternating zero-contrast surfaces with a `1px solid #24414B` bottom dividing hairline.
- Header row pinned with `#102229` background, `JetBrains Mono` label caps, and muted secondary text `#9BB3B9`.
- Row hover triggers instant transition to `#16303A`. Selected anomaly rows feature a `2px` vertical marker along the left edge colored in semantic status (e.g., `#F0786F` for dark targets).

### SAR & Anomaly Cards
- Backed by `#102229` with `rgba(16, 34, 41, 0.78)` frosted backdrop blur (`12px`).
- Features a dual-header displaying target vessel thumbnail / radar cross-section, confidence match percentage (`Space Grotesk`), and cryptographic attribution timestamp (`JetBrains Mono`).