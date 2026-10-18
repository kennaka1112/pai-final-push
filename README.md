# ブロック押しタスクの模倣学習（Physical AI 応用1 最終課題）

ロボットアーム **CRANE+ V2** が、机の上の赤いブロックを目標エリアまで押すタスクを、
**ACT（Action Chunking with Transformers）による模倣学習**で獲得します。
シミュレータは ROS 2 Humble + Gazebo（Ignition Fortress）です。

```
自動デモ生成 → rosbag2 記録 → LeRobotDataset 変換 → ACT 学習(GPU) → Gazeboで実行
```

## タスク

| 項目 | 内容 |
|---|---|
| ロボット | CRANE+ V2（4自由度アーム＋グリッパ） |
| 対象物 | 4cm角のブロック（質量80g、摩擦係数0.45） |
| 開始位置 | ロボット基部から半径0.14m・方位 −20° |
| 目標エリア | 同 半径0.14m・方位 +23°（緑のマーカー、8.5cm角） |
| 成功判定 | ブロック中心が目標エリア中心から4cm以内 |
| AIの役割 | 20エピソードのデモから ACT 方策を学習し、関節状態のみを入力に押し動作を生成 |

アームは関節空間で動きます。平面2リンクの逆運動学で手先（joint4の軸）を
「半径・高さ」で指定し、joint4 でグリッパを常に真下へ向け、joint1（旋回）で
ブロックを円弧状に押します。

## 動かす

必要なもの: Docker（WSL 2 backend 可）、NVIDIA GPU とドライバ、空きディスク 40GB 程度。

```bash
docker compose up -d --build
```

初回ビルドはベースイメージと PyTorch のダウンロードで数十分かかります。
起動後、ブラウザで <http://localhost:6080> を開きます（VNCパスワード: `ubuntu`）。
デスクトップの **Terminator** を開き、`Ctrl+Shift+E` / `Ctrl+Shift+O` で分割して使います。

### 1. シミュレータを起動

```bash
ros2 launch /workspace/pai_push/launch/push_task.launch.py
```

机・ブロック・目標エリアを配置した専用ワールドで CRANE+ V2 が立ち上がります。
MoveIt と RViz は使わないので、講義の `crane_plus_with_table.launch.py` より軽量です。

### 2. デモデータを自動収集（別ターミナル）

```bash
push-collect -n 20
```

スクリプトが押し動作を生成し、`/joint_states` と関節指令トピックを rosbag2 に記録します。
エピソードごとに押し始めの角度・押す速さ・手先の高さを乱数で少し変え、
毎回ブロックを開始位置へ戻します。終了時に各エピソードの成否が表示されます。

### 3. LeRobotDataset へ変換

```bash
push-convert
```

### 4. ACT を学習（GPU）

```bash
push-train
```

設定は [`pai_push/configs/push_train.yaml`](pai_push/configs/push_train.yaml)。
RTX 3060 で 6000 step がおよそ 10 分です。

### 5. 学習した方策で実行

```bash
push-infer
```

`/joint_states` を観測として受け取り、20Hz で関節指令を出します。
成否を自動判定しながら決まった回数だけ試行するには `push-trial 15 10`
（1試行あたり15秒制御、10試行）。アームの直立復帰とブロックのリセットも自動で行います。
データセット上でのオフライン評価は `push-eval 0`。

### 6. 動画を録る

```bash
record_screen.sh /workspace/video/raw/policy.mp4 60   # Gazeboの3Dビューを60秒録画
make_video.sh                                          # 字幕とタイトルを付けて結合
```

## ファイル構成

```text
.
├── Dockerfile / compose.yaml          # 実行環境（講義のベースイメージ＋本課題のPATH設定）
├── pai_push/
│   ├── worlds/push_task.sdf           # 机・ブロック・目標エリアのワールド
│   ├── launch/push_task.launch.py     # Gazebo + CRANE+ V2（MoveIt/RVizなし）
│   ├── gui/push_gui.config            # 撮影用のGazebo GUI設定（3Dビューのみ）
│   ├── scripts/
│   │   ├── push_motion.py             # 逆運動学と押し軌道の生成
│   │   ├── auto_demo_push.py          # デモの自動生成と rosbag 記録
│   │   ├── run_push.py                # 押し動作を1回だけ実行（動作確認用）
│   │   ├── reset_block.sh             # ブロックを開始位置へ戻す
│   │   ├── block_pose.sh              # ブロックの現在位置を表示
│   │   ├── goto_upright.py            # アームを直立へ戻す（試行条件をそろえる）
│   │   ├── push-collect / -convert / -train / -infer / -eval / -trial
│   │   ├── plot_loss.py               # 学習ログから損失曲線を描く
│   │   ├── prepare_display.sh         # 録画前にスクリーンセーバーを止める
│   │   ├── record_screen.sh / record_clips.sh  # 画面録画
│   │   └── make_video.sh              # 提出用動画の組み立て
│   └── configs/                       # 特徴量定義・変換設定・学習設定
├── tools/                             # 講義の pai-* コマンド（環境構築時から流用）
└── report/                            # レポート（PDF）の原稿
```

## 講義教材からの変更点

この環境は講義（第4・5回）の「CRANE+ V2 でお辞儀を模倣学習する」演習を土台にしています。
本課題で新しく作った部分は次のとおりです。

- **タスクの変更**: 姿勢を再生するだけのお辞儀から、物体に接触して位置を変える「押し」へ
- **ワールドの自作**: ブロックと目標エリアを置いた `push_task.sdf`、Fuel 依存を減らした自前のブロックモデル
- **逆運動学による軌道設計**: URDF から読んだリンク長で平面2リンク IK を実装し、
  手先の高さ・半径・向きを指定して軌道を作れるようにした（お辞儀デモは関節角の直打ち）
- **データ収集の自動化**: ブロックの自動リセット、パラメータのランダム化、
  目標エリアへの到達判定による成否の自動記録
- **学習設定の調整**: 講義デフォルト（200 step / batch 2 / chunk 16）では
  11秒の長い軌道を再現できなかったため、6000 step / batch 16 / chunk 32 へ変更

## ライセンス

- ベースイメージおよび CRANE+ V2 のパッケージは [RT Corporation](https://github.com/rt-net/crane_plus) 他の
  Apache License 2.0 に従います。
- 学習コード（`pai_training`）は講義で配布された [matsuolab/pai_training](https://github.com/matsuolab/pai_training) を
  そのまま利用しています（このリポジトリには含まれず、Dockerビルド時に取得します）。
- 本リポジトリで新規に作成したファイルは MIT License とします。
