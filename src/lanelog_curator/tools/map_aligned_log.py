import csv
from pathlib import Path

import lanelet2

MAP_PATH = Path("data/maps/sample.osm")
OUT_PATH = Path("data/raw_logs/map_aligned_log.csv")

def load_map():
    projector = lanelet2.projection.UtmProjector(
        lanelet2.io.Origin(49.0, 8.4)
    )
    return lanelet2.io.load(str(MAP_PATH), projector)

def main():
    lanelet_map = load_map()

    rows = []
    timestamp = 0

    for lanelet in lanelet_map.laneletLayer:
        centerline = lanelet.centerline

        for point in centerline:
            ego_x = float(point.x)
            ego_y = float(point.y)

            rows.append({
                "timestamp": timestamp,
                "ego_x": ego_x,
                "ego_y": ego_y,
                "ego_speed_mps": 8.0 if timestamp % 60 != 0 else 55.0,
                "object_id": "obj_001",
                "object_x": ego_x + 6.0,
                "object_y": ego_y + 1.0,
                "object_class": "vehicle",
                "label_source": "map_generated",
                "label_confidence": 0.55 if timestamp % 25 == 0 else 0.95,
            })

            timestamp += 1

            if timestamp >= 200:
                break

        if timestamp >= 200:
            break

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "ego_x",
                "ego_y",
                "ego_speed_mps",
                "object_id",
                "object_x",
                "object_y",
                "object_class",
                "label_source",
                "label_confidence",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {OUT_PATH}")
    print(f"Rows: {len(rows)}")

if __name__ == "__main__":
    main()