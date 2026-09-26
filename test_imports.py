import sys

modules = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "numpy",
    "scipy",
    "pandas",
    "sklearn",
    "shapely",
    "pyproj",
    "tifffile",
    "zarr",
    "yaml",
    "requests",
    "reportlab",
    "pytest",
    "rasterio"
]

print("Testing dependencies:")
missing = []
for m in modules:
    try:
        __import__(m)
        print(f"  [OK] {m}")
    except ImportError as e:
        print(f"  [MISSING] {m}: {e}")
        missing.append(m)

print(f"\nMissing modules count: {len(missing)} ({missing})")
