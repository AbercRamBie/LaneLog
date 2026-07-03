#include <lanelet2_core/LaneletMap.h>
#include <lanelet2_core/geometry/LaneletMap.h>
#include <lanelet2_core/primitives/Lanelet.h>
#include <lanelet2_io/Io.h>
#include <lanelet2_projection/UTM.h>

#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct LogRecord {
  int timestamp{};
  double ego_x{};
  double ego_y{};
  double ego_speed_mps{};
  std::string object_id;
  double object_x{};
  double object_y{};
  std::string object_class;
  std::string label_source;
  double label_confidence{};
};

struct CuratedRecord {
  LogRecord raw;

  long ego_lanelet_id{-1};
  double ego_lanelet_distance_m{-1.0};

  bool matched_to_lanelet{false};
  bool far_from_lanelet{false};
  bool object_ahead_close{false};
  bool low_confidence_label{false};
  bool unrealistic_speed{false};
  bool quality_issue{false};

  std::string scenario_type{"normal"};
};

struct QualityReport {
  int total_frames{0};
  int matched_frames{0};
  int far_from_lanelet_frames{0};
  int object_ahead_close_frames{0};
  int low_confidence_label_frames{0};
  int unrealistic_speed_frames{0};
  int quality_issue_frames{0};
};

std::vector<std::string> splitCsvLine(const std::string& line) {
  std::vector<std::string> result;
  std::stringstream ss(line);
  std::string cell;

  while (std::getline(ss, cell, ',')) {
    result.push_back(cell);
  }

  return result;
}

double distance2d(double x1, double y1, double x2, double y2) {
  const double dx = x1 - x2;
  const double dy = y1 - y2;
  return std::sqrt(dx * dx + dy * dy);
}

std::vector<LogRecord> readSyntheticLog(const std::string& path) {
  std::ifstream file(path);
  if (!file.is_open()) {
    throw std::runtime_error("Could not open log file: " + path);
  }

  std::vector<LogRecord> records;
  std::string line;

  // Skip header.
  std::getline(file, line);

  while (std::getline(file, line)) {
    if (line.empty()) {
      continue;
    }

    auto cells = splitCsvLine(line);
    if (cells.size() != 10) {
      std::cerr << "Skipping malformed row: " << line << "\n";
      continue;
    }

    LogRecord record;
    record.timestamp = std::stoi(cells[0]);
    record.ego_x = std::stod(cells[1]);
    record.ego_y = std::stod(cells[2]);
    record.ego_speed_mps = std::stod(cells[3]);
    record.object_id = cells[4];
    record.object_x = std::stod(cells[5]);
    record.object_y = std::stod(cells[6]);
    record.object_class = cells[7];
    record.label_source = cells[8];
    record.label_confidence = std::stod(cells[9]);

    records.push_back(record);
  }

  return records;
}

lanelet::LaneletMapPtr loadMap(const std::string& map_path) {
  // This origin matches Lanelet2's tutorial/sample-map usage.
  lanelet::Origin origin({49.0, 8.4});
  lanelet::projection::UtmProjector projector(origin);

  return lanelet::load(map_path, projector);
}

std::pair<long, double> findNearestLanelet(
    lanelet::LaneletMapPtr map,
    double x,
    double y) {
  lanelet::BasicPoint2d query_point(x, y);

  // Lanelet2 examples recommend geometry::findNearest for the actually closest
  // lanelet, instead of only the nearest bounding box.
  auto nearest = lanelet::geometry::findNearest(
      map->laneletLayer,
      query_point,
      1);

  if (nearest.empty()) {
    return {-1, -1.0};
  }

  const double distance_m = nearest.front().first;
  const long lanelet_id = nearest.front().second.id();

  return {lanelet_id, distance_m};
}

CuratedRecord curateRecord(
    const LogRecord& record,
    lanelet::LaneletMapPtr map) {
  CuratedRecord curated;
  curated.raw = record;

  const auto nearest = findNearestLanelet(map, record.ego_x, record.ego_y);

  curated.ego_lanelet_id = nearest.first;
  curated.ego_lanelet_distance_m = nearest.second;

  curated.matched_to_lanelet = curated.ego_lanelet_id != -1;

  // Thresholds are intentionally simple for MVP.
  curated.far_from_lanelet =
      !curated.matched_to_lanelet ||
      curated.ego_lanelet_distance_m > 8.0;

  const double object_distance = distance2d(
      record.ego_x,
      record.ego_y,
      record.object_x,
      record.object_y);

  curated.object_ahead_close = object_distance < 12.0;
  curated.low_confidence_label = record.label_confidence < 0.70;
  curated.unrealistic_speed = record.ego_speed_mps > 45.0;

  curated.quality_issue =
      curated.far_from_lanelet ||
      curated.low_confidence_label ||
      curated.unrealistic_speed;

  if (curated.unrealistic_speed) {
    curated.scenario_type = "sensor_or_log_artifact";
  } else if (curated.far_from_lanelet) {
    curated.scenario_type = "map_match_issue";
  } else if (curated.low_confidence_label) {
    curated.scenario_type = "needs_label_review";
  } else if (curated.object_ahead_close) {
    curated.scenario_type = "object_ahead_close";
  } else {
    curated.scenario_type = "normal";
  }

  return curated;
}

void writeCuratedFrames(
    const std::string& path,
    const std::vector<CuratedRecord>& records) {
  std::ofstream out(path);
  if (!out.is_open()) {
    throw std::runtime_error("Could not write curated CSV: " + path);
  }

  out << "timestamp,"
      << "ego_x,ego_y,ego_speed_mps,"
      << "object_id,object_x,object_y,object_class,"
      << "label_source,label_confidence,"
      << "ego_lanelet_id,ego_lanelet_distance_m,"
      << "matched_to_lanelet,far_from_lanelet,object_ahead_close,"
      << "low_confidence_label,unrealistic_speed,quality_issue,"
      << "scenario_type\n";

  out << std::fixed << std::setprecision(3);

  for (const auto& r : records) {
    out << r.raw.timestamp << ","
        << r.raw.ego_x << ","
        << r.raw.ego_y << ","
        << r.raw.ego_speed_mps << ","
        << r.raw.object_id << ","
        << r.raw.object_x << ","
        << r.raw.object_y << ","
        << r.raw.object_class << ","
        << r.raw.label_source << ","
        << r.raw.label_confidence << ","
        << r.ego_lanelet_id << ","
        << r.ego_lanelet_distance_m << ","
        << r.matched_to_lanelet << ","
        << r.far_from_lanelet << ","
        << r.object_ahead_close << ","
        << r.low_confidence_label << ","
        << r.unrealistic_speed << ","
        << r.quality_issue << ","
        << r.scenario_type << "\n";
  }
}

QualityReport buildQualityReport(const std::vector<CuratedRecord>& records) {
  QualityReport report;
  report.total_frames = static_cast<int>(records.size());

  for (const auto& r : records) {
    report.matched_frames += r.matched_to_lanelet ? 1 : 0;
    report.far_from_lanelet_frames += r.far_from_lanelet ? 1 : 0;
    report.object_ahead_close_frames += r.object_ahead_close ? 1 : 0;
    report.low_confidence_label_frames += r.low_confidence_label ? 1 : 0;
    report.unrealistic_speed_frames += r.unrealistic_speed ? 1 : 0;
    report.quality_issue_frames += r.quality_issue ? 1 : 0;
  }

  return report;
}

void writeQualityReport(const std::string& path, const QualityReport& report) {
  std::ofstream out(path);
  if (!out.is_open()) {
    throw std::runtime_error("Could not write quality report: " + path);
  }

  out << "{\n";
  out << "  \"total_frames\": " << report.total_frames << ",\n";
  out << "  \"matched_frames\": " << report.matched_frames << ",\n";
  out << "  \"far_from_lanelet_frames\": " << report.far_from_lanelet_frames << ",\n";
  out << "  \"object_ahead_close_frames\": " << report.object_ahead_close_frames << ",\n";
  out << "  \"low_confidence_label_frames\": " << report.low_confidence_label_frames << ",\n";
  out << "  \"unrealistic_speed_frames\": " << report.unrealistic_speed_frames << ",\n";
  out << "  \"quality_issue_frames\": " << report.quality_issue_frames << "\n";
  out << "}\n";
}

int main(int argc, char** argv) {
  try {
    std::string map_path = "data/maps/sample.osm";
    std::string log_path = "data/raw_logs/synthetic_log.csv";
    std::string curated_path = "outputs/curated_frames.csv";
    std::string report_path = "outputs/quality_report.json";

    if (argc >= 2) {
      map_path = argv[1];
    }

    if (argc >= 3) {
      log_path = argv[2];
    }

    std::cout << "Loading map: " << map_path << "\n";
    auto map = loadMap(map_path);

    std::cout << "Loaded lanelets: " << map->laneletLayer.size() << "\n";

    std::cout << "Reading log: " << log_path << "\n";
    auto records = readSyntheticLog(log_path);

    std::vector<CuratedRecord> curated_records;
    curated_records.reserve(records.size());

    for (const auto& record : records) {
      curated_records.push_back(curateRecord(record, map));
    }

    const auto report = buildQualityReport(curated_records);

    writeCuratedFrames(curated_path, curated_records);
    writeQualityReport(report_path, report);

    std::cout << "Wrote: " << curated_path << "\n";
    std::cout << "Wrote: " << report_path << "\n";

    std::cout << "\nQuality summary\n";
    std::cout << "---------------\n";
    std::cout << "Total frames: " << report.total_frames << "\n";
    std::cout << "Matched frames: " << report.matched_frames << "\n";
    std::cout << "Quality issue frames: " << report.quality_issue_frames << "\n";
    std::cout << "Low confidence labels: " << report.low_confidence_label_frames << "\n";
    std::cout << "Unrealistic speed frames: " << report.unrealistic_speed_frames << "\n";
    std::cout << "Far from lanelet frames: " << report.far_from_lanelet_frames << "\n";

    return 0;
  } catch (const std::exception& e) {
    std::cerr << "ERROR: " << e.what() << "\n";
    return 1;
  }
}
