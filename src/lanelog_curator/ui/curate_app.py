import json
import subprocess
from pathlib import Path

import lanelet2
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PACKAGE_DIR = Path("/home/subash/DiskD/RoboticsWorks/LaneLog/src/lanelog_curator")
RUN_SCRIPT = PACKAGE_DIR / "scripts" / "run_pipeline.sh"
MAP_DIR = PACKAGE_DIR / "data" / "maps"
LOG_DIR = PACKAGE_DIR / "data" / "raw_logs"
OUTPUT_DIR = PACKAGE_DIR / "outputs"
CURATED_PATH = OUTPUT_DIR / "curated_frames.csv"
REPORT_PATH = OUTPUT_DIR / "quality_report.json"

st.set_page_config(
    page_title="LaneLog Curator",
    layout="wide",
)

st.title("LaneLog Curator")
st.caption("Map-aware driving log curation using C++ and Lanelet2")

def list_files(folder: Path, suffix: str):
    if not folder.exists():
        return []
    return sorted([p for p in folder.glob(f"*{suffix}") if p.is_file()])

def relative_to_package(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


@st.cache_data
def load_lanelet_map_for_plot(map_path_str: str):
    """
    Loads a Lanelet2 map and extracts simple plottable geometry.

    The projector origin should match the one used in the C++ pipeline.
    """
    map_path = Path(map_path_str)

    projector = lanelet2.projection.UtmProjector(
        lanelet2.io.Origin(49.0, 8.4)
    )

    lanelet_map = lanelet2.io.load(str(map_path), projector)

    boundary_lines = []
    center_lines = []
    lanelet_count = 0

    for lanelet in lanelet_map.laneletLayer:
        lanelet_count += 1

        left_x = [float(p.x) for p in lanelet.leftBound]
        left_y = [float(p.y) for p in lanelet.leftBound]

        right_x = [float(p.x) for p in lanelet.rightBound]
        right_y = [float(p.y) for p in lanelet.rightBound]

        center_x = [float(p.x) for p in lanelet.centerline]
        center_y = [float(p.y) for p in lanelet.centerline]

        if len(left_x) >= 2:
            boundary_lines.append(
                {
                    "lanelet_id": int(lanelet.id),
                    "type": "left_boundary",
                    "x": left_x,
                    "y": left_y,
                }
            )

        if len(right_x) >= 2:
            boundary_lines.append(
                {
                    "lanelet_id": int(lanelet.id),
                    "type": "right_boundary",
                    "x": right_x,
                    "y": right_y,
                }
            )

        if len(center_x) >= 2:
            center_lines.append(
                {
                    "lanelet_id": int(lanelet.id),
                    "type": "centerline",
                    "x": center_x,
                    "y": center_y,
                }
            )

    return {
        "boundary_lines": boundary_lines,
        "center_lines": center_lines,
        "lanelet_count": lanelet_count,
    }


maps = list_files(MAP_DIR, ".osm")
logs = list_files(LOG_DIR, ".csv")

if not maps:
    st.error(f"No .osm maps found in {MAP_DIR}")
    st.stop()

if not logs:
    st.error(f"No .csv logs found in {LOG_DIR}")
    st.stop()


left, right = st.columns(2)

with left:
    selected_map = st.selectbox(
        "Lanelet2 map",
        maps,
        format_func=lambda p: p.name,
    )

with right:
    selected_log = st.selectbox(
        "Driving log",
        logs,
        format_func=lambda p: p.name,
    )


run_clicked = st.button("Run C++ curation pipeline", type="primary")

if run_clicked:
    map_arg = relative_to_package(selected_map)
    log_arg = relative_to_package(selected_log)

    with st.spinner("Running C++ LaneLog pipeline..."):
        result = subprocess.run(
            [str(RUN_SCRIPT), map_arg, log_arg],
            cwd=PACKAGE_DIR,
            text=True,
            capture_output=True,
        )

    if result.returncode != 0:
        st.error("Pipeline failed")
        st.subheader("stderr")
        st.code(result.stderr)

        if result.stdout:
            st.subheader("stdout")
            st.code(result.stdout)
    else:
        st.success("Pipeline completed")

        with st.expander("Pipeline console output"):
            st.code(result.stdout)


st.divider()


tab1, tab2, tab3 = st.tabs(
    [
        "Map viewer",
        "Quality report",
        "Curated data",
    ]
)


with tab1:
    st.subheader("Lanelet2 map viewer")

    try:
        map_plot_data = load_lanelet_map_for_plot(str(selected_map))

        fig = go.Figure()

        for line in map_plot_data["boundary_lines"]:
            fig.add_trace(
                go.Scattergl(
                    x=line["x"],
                    y=line["y"],
                    mode="lines",
                    line=dict(width=1),
                    name="Lane boundary",
                    hovertemplate=(
                        "Lanelet ID: %{customdata}<br>"
                        "Type: boundary<br>"
                        "x: %{x:.2f}<br>"
                        "y: %{y:.2f}"
                        "<extra></extra>"
                    ),
                    customdata=[line["lanelet_id"]] * len(line["x"]),
                    showlegend=False,
                )
            )

        for line in map_plot_data["center_lines"]:
            fig.add_trace(
                go.Scattergl(
                    x=line["x"],
                    y=line["y"],
                    mode="lines",
                    line=dict(width=1, dash="dot"),
                    name="Centerline",
                    hovertemplate=(
                        "Lanelet ID: %{customdata}<br>"
                        "Type: centerline<br>"
                        "x: %{x:.2f}<br>"
                        "y: %{y:.2f}"
                        "<extra></extra>"
                    ),
                    customdata=[line["lanelet_id"]] * len(line["x"]),
                    showlegend=False,
                )
            )

        if CURATED_PATH.exists():
            df_map = pd.read_csv(CURATED_PATH)

            required_cols = {
                "ego_x",
                "ego_y",
                "timestamp",
                "scenario_type",
                "ego_speed_mps",
                "ego_lanelet_id",
                "ego_lanelet_distance_m",
                "quality_issue",
            }

            if required_cols.issubset(df_map.columns):
                fig.add_trace(
                    go.Scattergl(
                        x=df_map["ego_x"],
                        y=df_map["ego_y"],
                        mode="markers+lines",
                        marker=dict(size=5),
                        line=dict(width=2),
                        name="Ego trajectory",
                        hovertemplate=(
                            "Timestamp: %{customdata[0]}<br>"
                            "Scenario: %{customdata[1]}<br>"
                            "Speed: %{customdata[2]:.2f} m/s<br>"
                            "Lanelet ID: %{customdata[3]}<br>"
                            "Lanelet distance: %{customdata[4]:.2f} m"
                            "<extra></extra>"
                        ),
                        customdata=df_map[
                            [
                                "timestamp",
                                "scenario_type",
                                "ego_speed_mps",
                                "ego_lanelet_id",
                                "ego_lanelet_distance_m",
                            ]
                        ].to_numpy(),
                    )
                )

                issue_df = df_map[df_map["quality_issue"].astype(bool)]

                if len(issue_df) > 0:
                    fig.add_trace(
                        go.Scattergl(
                            x=issue_df["ego_x"],
                            y=issue_df["ego_y"],
                            mode="markers",
                            marker=dict(size=10, symbol="x"),
                            name="Quality issue",
                            hovertemplate=(
                                "Timestamp: %{customdata[0]}<br>"
                                "Issue: %{customdata[1]}<br>"
                                "Speed: %{customdata[2]:.2f} m/s<br>"
                                "Distance to lanelet: %{customdata[3]:.2f} m"
                                "<extra></extra>"
                            ),
                            customdata=issue_df[
                                [
                                    "timestamp",
                                    "scenario_type",
                                    "ego_speed_mps",
                                    "ego_lanelet_distance_m",
                                ]
                            ].to_numpy(),
                        )
                    )

        fig.update_layout(
            title=f"Map: {selected_map.name} | Lanelets: {map_plot_data['lanelet_count']}",
            xaxis_title="Map X",
            yaxis_title="Map Y",
            height=700,
            dragmode="pan",
        )

        fig.update_yaxes(scaleanchor="x", scaleratio=1)

        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Solid lines show lane boundaries. Dotted lines show lanelet centerlines. "
            "The ego trajectory appears after the C++ pipeline generates curated_frames.csv."
        )

    except Exception as e:
        st.error("Could not load or render the Lanelet2 map.")
        st.exception(e)


with tab2:
    st.subheader("Quality report")

    if REPORT_PATH.exists():
        with REPORT_PATH.open("r") as f:
            report = json.load(f)

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("Total frames", report.get("total_frames", 0))
        c2.metric("Matched frames", report.get("matched_frames", 0))
        c3.metric("Quality issues", report.get("quality_issue_frames", 0))
        c4.metric("Low confidence", report.get("low_confidence_label_frames", 0))
        c5.metric("Unrealistic speed", report.get("unrealistic_speed_frames", 0))

        st.json(report)
    else:
        st.info("Run the pipeline to generate outputs/quality_report.json")


with tab3:
    st.subheader("Curated frames")

    if CURATED_PATH.exists():
        df = pd.read_csv(CURATED_PATH)

        if "scenario_type" in df.columns:
            scenario_filter = st.multiselect(
                "Filter by scenario type",
                sorted(df["scenario_type"].unique()),
            )

            view_df = df.copy()

            if scenario_filter:
                view_df = view_df[view_df["scenario_type"].isin(scenario_filter)]
        else:
            view_df = df

        st.dataframe(view_df, use_container_width=True, height=520)

        st.download_button(
            label="Download curated_frames.csv",
            data=CURATED_PATH.read_bytes(),
            file_name="curated_frames.csv",
            mime="text/csv",
        )
    else:
        st.info("Run the pipeline to generate outputs/curated_frames.csv")