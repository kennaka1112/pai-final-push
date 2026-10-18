# Physical AI 最終課題「ブロック押し」の実行環境
#   ROS 2 Humble + Gazebo + CRANE+ V2 + LeRobot(ACT) を1つのコンテナにまとめたもの
#   ベース: 講義で使用した airobotbook/ros2-desktop-ai-robot-book-humble
FROM airobotbook/ros2-desktop-ai-robot-book-humble:latest

SHELL ["/bin/bash", "-c"]

# 講義リポジトリのcommitを固定（再現性のため。更新するときはここを書き換える）
ARG PAI_TRAINING_REF=b4d6b5459066a80433475a83567504988875248a
ARG PHYSICALAI_TELEOP_REF=0ef2a00fd6d7bb39377969d10f3d26268e447fd9
ARG PIXI_VERSION=v0.81.0

# pixi（第4回で紹介されたパッケージマネージャ）をシステムに入れる
RUN curl -fsSL https://pixi.sh/install.sh \
      | PIXI_VERSION=${PIXI_VERSION} PIXI_HOME=/usr/local PIXI_NO_PATH_UPDATE=1 bash && \
    pixi --version

USER ubuntu
WORKDIR /home/ubuntu

# --- 1. テレオペ用ROSパッケージ（第5回：physicalai_teleop） ---
RUN mkdir -p ~/pai_ws/src && cd ~/pai_ws/src && \
    git clone https://github.com/matsuolab/physicalai_teleop.git && \
    git -C physicalai_teleop checkout ${PHYSICALAI_TELEOP_REF} && \
    cd ~/pai_ws && source /opt/ros/humble/setup.bash && \
    colcon build --symlink-install --packages-select physicalai_teleop

# --- 2. 模倣学習（第5回：pai_training + LeRobot） ---
RUN git clone https://github.com/matsuolab/pai_training.git ~/pai_training && \
    cd ~/pai_training && git checkout ${PAI_TRAINING_REF} && \
    git submodule update --init --recursive
# 依存パッケージ（torch等、数GB）はビルド時に入れておく
RUN cd ~/pai_training && pixi install && (pixi clean cache --yes || true)
# GPU(CUDA)で学習するように設定（それ以外のハイパーパラメータは講義のまま）
RUN sed -i 's/^device: .*/device: "cuda"/' ~/pai_training/configs/train_config.yaml

# --- 3. データ・チェックポイントの置き場所（docker volumeでホスト側に永続化） ---
RUN mkdir -p ~/dataset/rosbags ~/dataset/lerobot_dataset ~/checkpoints

# --- 4. 便利コマンド（pai-*） ---
COPY --chown=ubuntu:ubuntu tools/ /home/ubuntu/pai_tools/
RUN sed -i 's/\r$//' ~/pai_tools/* && chmod +x ~/pai_tools/* && \
    { echo ''; \
      echo '# ---- physical-ai-sim ----'; \
      echo 'source ~/pai_ws/install/setup.bash'; \
      echo 'export PATH="$HOME/pai_tools:$PATH"'; \
      echo 'eval "$(pixi completion --shell bash)"'; \
      echo '# ---- pai-final-push (本課題のコマンド) ----'; \
      echo 'export PATH="/workspace/pai_push/scripts:$PATH"'; \
    } >> ~/.bashrc

# 起動処理（VNC/noVNC）はベースイメージのentrypointがrootで行う
USER root
WORKDIR /
