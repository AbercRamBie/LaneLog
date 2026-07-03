FROM ros:jazzy

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=jazzy

SHELL ["/bin/bash", "-c"]

# System + ROS dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    python3-full \
    python3-colcon-common-extensions \
    python3-rosdep \
    git \
    build-essential \
    cmake \
    ros-jazzy-lanelet2 \
    && rm -rf /var/lib/apt/lists/*

# Create workspace
WORKDIR /lanelog_ws

# Copy project into container
COPY . /lanelog_ws

# Create Python venv for UI.
# --system-site-packages allows the venv to see ROS-installed Python packages like lanelet2.
RUN python3 -m venv --system-site-packages /opt/lanelog_venv && \
    source /opt/lanelog_venv/bin/activate && \
    pip install --upgrade pip && \
    pip install streamlit pandas plotly

# Build ROS 2 workspace
RUN source /opt/ros/jazzy/setup.bash && \
    colcon build --packages-select lanelog_curator

# Default working directory: package folder
WORKDIR /lanelog_ws/src/lanelog_curator

# Expose Streamlit
EXPOSE 8501

# Default command launches UI
CMD source /opt/ros/jazzy/setup.bash && \
    source /lanelog_ws/install/setup.bash && \
    source /opt/lanelog_venv/bin/activate && \
    streamlit run ui/curate_app.py \
      --server.address=0.0.0.0 \
      --server.port=8501
