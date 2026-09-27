# Public data acquired for SAGAR-SAKSHI

These files were downloaded from public sources on 2026-09-26. This folder contains reference/training material, not substitutes for the two India incident scenes.

## Downloaded files

- `DARTIS_2019/DARTIS_2019.tab` - PANGAEA tabular metadata/annotations for Sentinel-1 oil slick and look-alike patches. The patch imagery itself is linked through PANGAEA; bulk image download returned HTTP 401/503 from this environment and is not included. Dataset DOI: <https://doi.org/10.1594/PANGAEA.980773>.
- `DARTIS_2019/Metadata.txt` and `DARTIS_2019/README.pdf` - dataset metadata and instructions. DARTIS labels are from the Eastern Mediterranean, so they are auxiliary training material and do not validate Indian-coast performance.
- `Kerala_MSC_ELSA3_2025/SDMA_SITREP_3_2025-05-25.pdf` - Kerala State Disaster Management Authority situation report, useful as event context/label provenance; it is not a machine-readable SAR mask.

## Sentinel-1 scenes found in the official Copernicus catalogue

See `sentinel_scene_catalog.json` for the catalogue metadata and product IDs.

- Ennore event-date candidate: `S1A_IW_GRDH_1SDV_20170129T003132_20170129T003157_015039_01892E_8B05_COG.SAFE` (29 Jan 2017, VV/VH IW GRD).
- Kerala candidate: `S1A_IW_GRDH_1SDV_20250528T004112_20250528T004137_059387_075F14_7F15_COG.SAFE` (28 May 2025, VV/VH IW GRD). This is temporally relevant to the 25 May sinking and replaces the July 2025 scene as the incident replay candidate.

Copernicus Data Space metadata is public, but product download requires an authenticated Data Space account/session. No credentials were present in this environment, so the large SAFE products could not be downloaded. Search the exact product names in <https://dataspace.copernicus.eu/browser/> after signing in. The catalogue footprints cover the configured approximate AOIs; verify the downloaded SAFE products and georeferencing before processing.

## Still needed for defensible incident attribution

1. The two original SAFE/COG products above and 2-4 before/after/control scenes per AOI.
2. Historical AIS for all vessels in the scene windows, plus receiver/coverage quality metadata. The public official sources found here do not provide a bulk machine-readable AIS archive.
3. Wind/current files (ERA5 and Copernicus Marine reanalysis) for each scene timestamp and drift window.
4. Expert-reviewed GeoJSON slick and look-alike polygons tied to SAR timestamps and independent official/field evidence.

Synthetic AIS or constant environmental values must remain clearly marked as prototype placeholders.

## SHA-256 checksums

bf88895370b69aef624dad6bb49d166274663a9842df87541cdc2297a96a6da8  data/external/DARTIS_2019/DARTIS_2019.tab  2411266 bytes
9722073ee4aeeb976a001624d7879dac8898d205ed3e75bbcaa76bcdd6c356b3  data/external/DARTIS_2019/Metadata.txt  3198 bytes
01ddf7b4a2a25519caebc8512ad59b9676dadbd061bdea08c1986067694c2f55  data/external/DARTIS_2019/README.pdf  101331 bytes
a34aa82500507a48e18ac42b99bed15df5ad465156c4a486c45f0fdd28a4b070  data/external/Kerala_MSC_ELSA3_2025/SDMA_SITREP_3_2025-05-25.pdf  857206 bytes
796686c69e0af51269985eb00f3449395fa6f129b44e9afbfa408e43c97bfcd2  data/external/sentinel_scene_catalog.json  4305 bytes


### ALOS-2 local file checksums

534dab2749268cbc4ac3980878b50182c6ce322fbd9c4002de411e84500ac524  data/external/ALOS2_Kerala_2025_browse_previews/IMG-HH-ALOS2594703420-250528-FBDR2.1GUD_sml.jpg  494882 bytes
40b1d02a6097378d08bf0c12faf00ab1fb2b89ae8a72767aa4583718e4074012  data/external/ALOS2_Kerala_2025_browse_previews/IMG-HH-ALOS2594703430-250528-FBDR2.1GUD_sml.jpg  504778 bytes
3ec2cb9110b00407a12083101084f7a40e9b57df309db77816129e4f4be3468a  data/external/ALOS2_Kerala_2025_browse_previews/IMG-HH-ALOS2594703440-250528-FBDR2.1GUD_sml.jpg  386017 bytes
f32665eff87947d3695c6f5f3b94ccf74a1e6a351a635a82b61dae104bf8103b  data/external/ALOS2_Kerala_2025_browse_previews/IMG-HH-ALOS2594703450-250528-FBDR2.1GUD_sml.jpg  152104 bytes
8a7aec8f31e06a9d7ef0f8d3d1e400b7241ae6ac68261f242478f04ba8e74ad9  data/external/ALOS2_Kerala_2025_browse_previews/IMG-HH-ALOS2594703460-250528-FBDR2.1GUD_sml.jpg  634733 bytes
a15e6e5269cbbf8db205dca1be1da152c071f2b63c15c18149b49953065d2c99  data/external/ALOS2_Kerala_2025_browse_previews/manifest.json  1721 bytes
fe1dfd6a4df8ee6d0647dc3d5a71cbba2ee32e4a0c06b787b8b4ce294d8e2998  data/external/ALOS2_Kerala_2025_browse_previews/README.txt  621 bytes
d4a5a317b49e08b3192e5ea7bcadb678fbbe36bbdeb90eb2faec3e66b455a352  data/external/ALOS2_Ennore_2017/README.txt  661 bytes

## ALOS-2 / PALSAR-2 follow-up

Five Kerala event browse JPEGs were downloaded to `ALOS2_Kerala_2025_browse_previews/`. They correspond to the Sentinel Asia 2025-05-28 frame list (3420 through 3460) and are small HH browse previews, not usable calibrated raster inputs. The event page identifies these as PALSAR-2 Level 2.1 FBD right-looking products. FBD is dual-polarization (HH+HV), not quad-polarization. No Ennore event-specific full product was available from public links inspected in this pass; see `ALOS2_Ennore_2017/README.txt`.

A true quad-pol acquisition contains HH, HV, VH, and VV from one acquisition. Combining dual-pol PALSAR-2 with dual-pol Sentinel-1 does not create quad-pol data: the wavelengths, acquisition times, geometry, and polarizations differ. JAXA's free PALSAR-2 ScanSAR L2.2 archive offers 25 m HH/HV backscatter for some acquisitions, but is heterogeneous and needs per-scene polarization filtering. Use JAXA G-Portal/AUIG2 to search event-date scenes and check the actual mode/polarizations.
