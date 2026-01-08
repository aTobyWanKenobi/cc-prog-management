"""
KML/KMZ to Terreni CSV Converter

Extracts polygons from KML or KMZ files (exported from Google Maps/Earth/geo.admin.ch)
and converts them to the terreni.csv format for the camp management system.

Usage:
    python kml_to_terreni.py <input.kml|input.kmz> [--output terreni.csv]

The script will:
1. Extract polygon geometries from the KML/KMZ
2. Calculate center coordinates for each polygon
3. Convert KML coordinates (lon,lat,alt) to our format [[lat, lon], ...]
4. Output in the terreni.csv format with empty tags for you to fill
"""

import argparse
import csv
import json
import os
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass


@dataclass
class Polygon:
    """Represents an extracted polygon."""

    name: str
    description: str
    center_lat: float
    center_lon: float
    coordinates: list[list[float]]  # [[lat, lon], ...]


def parse_kml_coordinates(coords_raw: str) -> list[list[float]]:
    """
    Parse KML coordinate string to list of [lat, lon] pairs.

    KML format: lon,lat,altitude lon,lat,altitude ...
    Our format: [[lat, lon], [lat, lon], ...]
    """
    coords_raw = coords_raw.strip().replace("\n", " ").replace("\t", " ")
    points = []

    for coord_set in coords_raw.split():
        if not coord_set.strip():
            continue
        parts = coord_set.split(",")
        if len(parts) >= 2:
            lon = float(parts[0])
            lat = float(parts[1])
            points.append([lat, lon])

    return points


def calculate_center(coordinates: list[list[float]]) -> tuple[float, float]:
    """Calculate the centroid of a polygon."""
    if not coordinates:
        return 0.0, 0.0

    lat_sum = sum(c[0] for c in coordinates)
    lon_sum = sum(c[1] for c in coordinates)
    n = len(coordinates)

    return lat_sum / n, lon_sum / n


def extract_polygons_from_kml_content(kml_content: bytes | str, source_name: str = "") -> list[Polygon]:
    """Extract all polygons from KML content."""
    polygons = []

    # Parse XML
    root = ET.fromstring(kml_content) if isinstance(kml_content, bytes) else ET.fromstring(kml_content.encode("utf-8"))

    # Handle KML namespace
    prefix = ""
    if root.tag.startswith("{"):
        prefix = root.tag.split("}")[0] + "}"

    # Counter for unnamed polygons
    unnamed_counter = 1

    # Find all Placemarks
    for placemark in root.findall(f".//{prefix}Placemark"):
        # Extract name - try multiple sources
        name = None

        # Try <name> tag first
        name_tag = placemark.find(f"{prefix}name")
        if name_tag is not None and name_tag.text and name_tag.text.strip():
            name = name_tag.text.strip()

        # If no name, try <description> tag (geo.admin.ch puts names here)
        if not name:
            description_tag = placemark.find(f"{prefix}description")
            if description_tag is not None and description_tag.text:
                # Clean up CDATA wrappers and whitespace
                desc_text = description_tag.text.strip()
                if desc_text:
                    name = desc_text

        # If still no name, try the id attribute
        if not name:
            placemark_id = placemark.get("id", "")
            if placemark_id:
                # Clean up IDs like "drawing_feature_1767896348699" to something readable
                if "drawing" in placemark_id.lower() or "feature" in placemark_id.lower():
                    name = f"Terreno {unnamed_counter}"
                    unnamed_counter += 1
                else:
                    name = placemark_id

        # Fallback
        if not name:
            name = f"Terreno {unnamed_counter}"
            unnamed_counter += 1

        # Description is now separate (empty if we used it for name)
        description_tag = placemark.find(f"{prefix}description")
        description_text = description_tag.text.strip() if description_tag is not None and description_tag.text else ""
        # If description was used as name, don't duplicate it
        description = "" if description_text == name else description_text

        # Find polygon (simple or inside MultiGeometry)
        polygon_elem = placemark.find(f".//{prefix}Polygon")

        if polygon_elem is None:
            multi = placemark.find(f".//{prefix}MultiGeometry")
            if multi:
                polygon_elem = multi.find(f".//{prefix}Polygon")

        if polygon_elem is not None:
            # Extract coordinates from outer boundary
            coords_tag = polygon_elem.find(f".//{prefix}outerBoundaryIs//{prefix}coordinates")
            if coords_tag is not None and coords_tag.text:
                coords = parse_kml_coordinates(coords_tag.text)
                if coords:
                    center_lat, center_lon = calculate_center(coords)

                    polygons.append(
                        Polygon(
                            name=name,
                            description=description,
                            center_lat=center_lat,
                            center_lon=center_lon,
                            coordinates=coords,
                        )
                    )
                    print(f"  + Extracted: {name} (center: {center_lat:.6f}, {center_lon:.6f})")

    return polygons


def extract_polygons_from_file(file_path: str) -> list[Polygon]:
    """Extract all polygons from a KML or KMZ file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".kmz":
        print(f"[KMZ] Processing archive: {file_path}")
        with zipfile.ZipFile(file_path, "r") as kmz:
            # Find KML file inside the archive
            kml_files = [f for f in kmz.namelist() if f.endswith(".kml")]
            if not kml_files:
                raise ValueError("No KML file found inside the KMZ archive")

            print(f"      Found internal KML: {kml_files[0]}")
            kml_content = kmz.read(kml_files[0])
            return extract_polygons_from_kml_content(kml_content, file_path)

    elif ext == ".kml":
        print(f"[KML] Processing file: {file_path}")
        with open(file_path, "rb") as f:
            kml_content = f.read()
        return extract_polygons_from_kml_content(kml_content, file_path)

    else:
        raise ValueError(f"Unsupported file format: {ext}. Use .kml or .kmz files.")


def write_terreni_csv(polygons: list[Polygon], output_path: str) -> None:
    """Write polygons to terreni.csv format."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Tags", "CenterLat", "CenterLon", "Polygon", "Description", "ImageUrls"])

        for poly in polygons:
            writer.writerow(
                [
                    poly.name,
                    "",  # Tags - to be filled manually (SPORT, CERIMONIA, NOTTURNO, BIVACCO)
                    f"{poly.center_lat:.6f}",
                    f"{poly.center_lon:.6f}",
                    json.dumps(poly.coordinates),
                    poly.description,
                    "[]",  # ImageUrls - empty by default
                ]
            )

    print(f"\n[OK] Written {len(polygons)} terrains to: {output_path}")
    print("\n[!] Remember to fill in the 'Tags' column with valid values:")
    print("   SPORT, CERIMONIA, NOTTURNO, BIVACCO")


def main():
    parser = argparse.ArgumentParser(
        description="Convert KML/KMZ polygons to terreni.csv format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python kml_to_terreni.py geo/map.kml
    python kml_to_terreni.py geo/map.kmz --output terreni.csv
    python kml_to_terreni.py geo/map.kml --append

Valid tags for terreni: SPORT, CERIMONIA, NOTTURNO, BIVACCO
        """,
    )
    parser.add_argument("input", help="Path to the KML or KMZ file")
    parser.add_argument("--output", "-o", default="terreni.csv", help="Output CSV file (default: terreni.csv)")
    parser.add_argument("--append", "-a", action="store_true", help="Append to existing CSV instead of overwriting")

    args = parser.parse_args()

    print("=== KML/KMZ to Terreni Converter ===")
    print(f"{'=' * 40}")
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    print()

    try:
        polygons = extract_polygons_from_file(args.input)

        if not polygons:
            print("\n[X] No polygons found in the file.")
            return 1

        if args.append and os.path.exists(args.output):
            # Read existing data
            existing = []
            with open(args.output, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                existing = list(reader)

            # Append new polygons
            with open(args.output, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for poly in polygons:
                    writer.writerow(
                        [
                            poly.name,
                            "",
                            f"{poly.center_lat:.6f}",
                            f"{poly.center_lon:.6f}",
                            json.dumps(poly.coordinates),
                            poly.description,
                            "[]",
                        ]
                    )
            print(f"\n[OK] Appended {len(polygons)} terrains to: {args.output}")
            print(f"   (Total terrains in file: {len(existing) + len(polygons)})")
        else:
            write_terreni_csv(polygons, args.output)

        return 0

    except FileNotFoundError as e:
        print(f"\n[X] Error: {e}")
        return 1
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        raise


if __name__ == "__main__":
    exit(main())
