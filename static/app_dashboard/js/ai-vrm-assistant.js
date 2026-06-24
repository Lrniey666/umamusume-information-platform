// 透過 base.html 的 import map 解析，確保 three 與 three-vrm 共用「同一個」THREE 實例，
// 避免雙實例造成 MToon 材質無法被 renderer 正確繪製。
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import {
  VRMLoaderPlugin,
  VRMUtils,
  VRMExpressionPresetName,
} from "@pixiv/three-vrm";

const root = document.getElementById("ai-vrm-assistant-root");

if (!root || !window.WebGLRenderingContext) {
  // 若頁面沒有掛載容器或環境不支援 WebGL，直接略過初始化。
  if (root) {
    root.style.display = "none";
  }
} else {
  init_assistant(root).catch((error) => {
    console.error("[AI VRM Assistant] 初始化失敗:", error);
    const speech_box = root.querySelector(".ai-vrm-assistant-speech");
    if (speech_box) {
      speech_box.textContent = "3D 模型載入失敗，請重新整理頁面。";
      speech_box.classList.add("is-visible");
    }
  });
}

async function init_assistant(assistant_root) {
  const model_url = assistant_root.dataset.vrmUrl || "";
  const chat_url = assistant_root.dataset.chatUrl || "/agent/chat/";

  const canvas_wrap = assistant_root.querySelector(".ai-vrm-assistant-canvas-wrap");
  const speech_box = assistant_root.querySelector(".ai-vrm-assistant-speech");
  const input_element = assistant_root.querySelector(".ai-vrm-assistant-chat input");
  const send_button = assistant_root.querySelector(".ai-vrm-assistant-chat button");
  const preset_buttons = assistant_root.querySelectorAll(".ai-vrm-assistant-presets button");
  const toggle_btn = assistant_root.querySelector(".ai-vrm-assistant-toggle-btn");

  if (!canvas_wrap || !speech_box || !input_element || !send_button || !model_url) {
    throw new Error("缺少必要 DOM 或 VRM URL");
  }

  // 不需打 API 的固定回覆（key 為觸發訊息，value 為顯示文字）。
  const FIXED_REPLIES = {
    "能帶我瀏覽本平台嗎?": "你沒有手嗎?平台就這麼大，自己去滑一滑",
  };

  // canvas-wrap 已直接放大（350×450），渲染器填滿容器即可，不需出血偏移。
  const view_width = canvas_wrap.clientWidth || 350;
  const view_height = canvas_wrap.clientHeight || 450;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, view_width / view_height, 0.1, 100);

  const renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: true,
    powerPreference: "high-performance",
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(view_width, view_height);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setClearColor(0x000000, 0);
  canvas_wrap.appendChild(renderer.domElement);

  // 三點打光 + 柔和環境光，營造接近 Live2D 的二次元立體感（避免死黑陰影）。
  const ambient_light = new THREE.AmbientLight(0xffffff, 0.75);
  scene.add(ambient_light);

  // 半球光提供天空/地面色調的柔和補色，讓 MToon 材質更通透。
  const hemi_light = new THREE.HemisphereLight(0xffffff, 0xe7ddff, 0.45);
  scene.add(hemi_light);

  // 主光（斜前上方，製造主要明暗面）。強度拉高、位置往右偏，輪廓更明顯。
  const key_light = new THREE.DirectionalLight(0xffffff, 2.2);
  key_light.position.set(2.0, 2.0, 2.0);
  scene.add(key_light);

  // 補光（另一側較弱冷光，柔化陰影死角）。
  const fill_light = new THREE.DirectionalLight(0xd7e4ff, 0.55);
  fill_light.position.set(-1.6, 1.2, 1.6);
  scene.add(fill_light);

  // 輪廓光（後上方，勾勒髮絲與肩線邊緣，增加立體分離感）。
  const rim_light = new THREE.DirectionalLight(0xfff2cc, 0.7);
  rim_light.position.set(-0.6, 1.8, -2.2);
  scene.add(rim_light);

  // resting 微笑壓低一點，避免 joy 表情把眼睛笑瞇起來而看不出視線跟隨。
  const RESTING_HAPPY = 0.18;

  // 互動參數
  const LOOK_RADIUS = 400; // 有效追視半徑（px，相對於客服容器中心）
  const IDLE_PHASE_A = Math.random() * Math.PI * 2; // 待機微動隨機相位
  const IDLE_PHASE_B = Math.random() * Math.PI * 2;

  // 待機站姿基準（依模型 humanoid 位移修正後的「真實」對應：
  // lowerArm 槽=真大臂、hand 槽=真前臂、upperArm 槽=肩膀不動）。
  const REST_POSE = {
    lUpperZ: -Math.PI / 2.6,
    rUpperZ: Math.PI / 2.6,
    lUpperX: 0,
    rUpperX: 0,
    lForeX: Math.PI / 9,
    rForeX: Math.PI / 9,
  };
  const POSE_KEYS = Object.keys(REST_POSE);
  const EXPR_KEYS = ["happy", "relaxed", "surprised", "aa", "ih"];

  let vrm_model = null;
  let model_scale_ref = 1; // 以模型實際身高推得的尺度

  // 狀態機：idle | welcoming | listening | talking
  let agent_state = "idle";
  let state_timer = 0; // welcoming / talking 倒數秒數

  // 骨骼參照（依位移修正）
  let bone_l_upper = null; // leftLowerArm 槽 = 真實左大臂
  let bone_r_upper = null; // rightLowerArm 槽 = 真實右大臂
  let bone_l_fore = null; // leftHand 槽 = 真實左前臂
  let bone_r_fore = null; // rightHand 槽 = 真實右前臂
  let chest_bone = null; // spine 槽 = 真實 Chest（呼吸）
  let chest_base_x = 0;
  let neck_node = null; // 真實 Neck node（待機微動）
  let neck_base = null;
  // ⚠ humanoid 'head' 槽被轉檔誤綁到緞帶彈簧骨，故視線直接操作真實 Head node。
  let head_node = null;
  let head_base_quat = null;

  // 姿勢通道：current 平滑趨近 target（皆在 tick 內以 lerp 過渡）
  const pose_current = { ...REST_POSE };
  const pose_target = { ...REST_POSE };

  // 表情通道：current 平滑趨近 target
  const expr_current = { happy: RESTING_HAPPY, relaxed: 0, surprised: 0, aa: 0, ih: 0 };
  const expr_target = { happy: RESTING_HAPPY, relaxed: 0, surprised: 0, aa: 0, ih: 0 };

  // 局部座標追視（normalized -1~1；超出半徑時 target 設 0，自然回正）
  let look_nx = 0;
  let look_ny = 0;
  let look_target_nx = 0;
  let look_target_ny = 0;

  let is_sending = false;
  let loading_timer = null;
  let hide_timer = null;

  const loader = new GLTFLoader();
  loader.crossOrigin = "anonymous";
  loader.register((parser) => new VRMLoaderPlugin(parser));
  const gltf = await loader.loadAsync(model_url);
  vrm_model = gltf.userData.vrm;

  if (!vrm_model) {
    throw new Error("VRM 載入失敗");
  }

  // 確保 VRM0 模型面向鏡頭（+Z），避免只看到背面或側面。
  if (VRMUtils.rotateVRM0) {
    VRMUtils.rotateVRM0(vrm_model);
  }
  VRMUtils.removeUnnecessaryVertices(gltf.scene);
  VRMUtils.removeUnnecessaryJoints(gltf.scene);

  // 關閉視錐裁切：VRM/SkinnedMesh 經旋轉縮放後 bounding sphere 不會自動更新，
  // 否則 renderer 可能誤判模型在畫面外而整個剔除，導致「畫面全透明看不到人」。
  vrm_model.scene.traverse((object) => {
    object.frustumCulled = false;
  });

  scene.add(vrm_model.scene);

  // 取真實頭部骨骼（humanoid 的 'head' 槽被轉檔誤綁到緞帶骨，不可用）。
  head_node = vrm_model.scene.getObjectByName("Head");

  // 消除預設 T-Pose，套用自然待機站姿。
  apply_rest_pose();

  // 套用 resting 微笑表情（客服親和感），並先 update 讓靜態時即生效。
  if (vrm_model.expressionManager) {
    vrm_model.expressionManager.setValue(VRMExpressionPresetName.Happy, RESTING_HAPPY);
    vrm_model.expressionManager.update();
  }

  // 先讓骨骼姿勢與世界矩陣套用一次，再依頭部骨骼座標精準框半身。
  vrm_model.update(0);
  vrm_model.scene.updateWorldMatrix(true, true);
  frame_upper_body();

  // 記錄頭部待機基準旋轉，作為視線跟隨的疊加基準。
  if (head_node) {
    head_base_quat = head_node.quaternion.clone();
  }

  window.addEventListener("mousemove", on_mouse_move);
  window.addEventListener("resize", on_resize);

  input_element.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit_message();
    }
  });
  send_button.addEventListener("click", submit_message);

  // 輸入框 focus / 輸入 → 進入「專注傾聽」；失焦且為空 → 回 idle。
  input_element.addEventListener("focus", () => enter_listening());
  input_element.addEventListener("input", () => enter_listening());
  input_element.addEventListener("blur", () => {
    if (agent_state === "listening" && !input_element.value.trim()) {
      set_state("idle");
    }
  });

  // 預設問題：點擊後填入輸入框並立即提問。
  preset_buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (is_sending) {
        return;
      }
      input_element.value = btn.dataset.q || btn.textContent.trim();
      submit_message();
    });
  });

  // 收起/展開切換：讀取 localStorage 初始狀態，點擊切換並持久化。
  if (toggle_btn) {
    if (localStorage.getItem("vrm-assistant-collapsed") === "true") {
      assistant_root.classList.add("is-collapsed");
    }
    toggle_btn.addEventListener("click", () => {
      const is_collapsed = assistant_root.classList.toggle("is-collapsed");
      localStorage.setItem("vrm-assistant-collapsed", String(is_collapsed));
    });
  }

  // 進場：迎賓模式。
  set_state("welcoming");

  const clock = new THREE.Clock();

  // 視線跟隨用的可重用暫存物件（避免每幀配置造成 GC）。
  const HEAD_MAX_YAW = 0.5; // 左右最大轉頭角（弧度）
  const HEAD_MAX_PITCH = 0.3; // 上下最大轉頭角（弧度）
  const WORLD_UP = new THREE.Vector3(0, 1, 0);
  const WORLD_RIGHT = new THREE.Vector3(1, 0, 0);
  const WORLD_FORWARD = new THREE.Vector3(0, 0, 1);
  const _q_yaw = new THREE.Quaternion();
  const _q_pitch = new THREE.Quaternion();
  const _q_roll = new THREE.Quaternion();
  const _q_world = new THREE.Quaternion();
  const _parent_q = new THREE.Quaternion();
  const _parent_q_inv = new THREE.Quaternion();
  const _head_base_world = new THREE.Quaternion();
  const _desired_local = new THREE.Quaternion();

  requestAnimationFrame(tick);

  function apply_rest_pose() {
    const humanoid = vrm_model.humanoid;
    if (!humanoid) {
      return;
    }

    // ⚠ 此模型由 PMX→VRM 自動轉檔，humanoid 對應「整體位移一節」（已由導出資料確認）：
    //   VRM leftUpperArm 槽 = 真實「肩膀」(Shoulder_L)  → 不動，避免塌陷
    //   VRM leftLowerArm 槽 = 真實「大臂」(Arm_L)        → 用來放下大臂
    //   VRM leftHand    槽 = 真實「前臂/手肘」(Elbow_L)  → 用來彎手肘
    bone_l_upper = humanoid.getNormalizedBoneNode("leftLowerArm");
    bone_r_upper = humanoid.getNormalizedBoneNode("rightLowerArm");
    bone_l_fore = humanoid.getNormalizedBoneNode("leftHand");
    bone_r_fore = humanoid.getNormalizedBoneNode("rightHand");

    // 待機呼吸骨骼：spine 槽對應真實 Chest。
    chest_bone = humanoid.getNormalizedBoneNode("spine");
    if (chest_bone) {
      chest_base_x = chest_bone.rotation.x;
    }

    // 真實 Neck node（humanoid 無 neck 對應），供待機微動。
    neck_node = vrm_model.scene.getObjectByName("Neck");
    if (neck_node) {
      neck_base = neck_node.rotation.clone();
    }

    // 立即套用一次待機姿勢（讓框景前手臂即為下垂狀態）。
    apply_pose_to_bones(0, 0);
  }

  // 將 pose_current 通道值套用到實際骨骼；breath_offset 為呼吸週期偏移。
  // 揮手動畫（bone_r_fore Z/Y）改由 tick() 直接疊加，不再走此通道。
  function apply_pose_to_bones(breath_offset) {
    if (bone_l_upper) {
      bone_l_upper.rotation.z = pose_current.lUpperZ;
      bone_l_upper.rotation.x = pose_current.lUpperX;
    }
    if (bone_r_upper) {
      bone_r_upper.rotation.z = pose_current.rUpperZ;
      bone_r_upper.rotation.x = pose_current.rUpperX;
    }
    if (bone_l_fore) {
      bone_l_fore.rotation.x = pose_current.lForeX;
    }
    if (bone_r_fore) {
      bone_r_fore.rotation.x = pose_current.rForeX;
    }
    if (chest_bone) {
      chest_bone.rotation.x = chest_base_x + breath_offset;
    }
  }

  // 狀態切換：設定該狀態的姿勢/表情「目標值」，由 tick 平滑過渡。
  function set_state(next_state) {
    agent_state = next_state;

    if (next_state === "welcoming") {
      state_timer = 2.5;
      // 右臂高舉：大臂側展 + 微前傾，前臂強彎約 90°，為有機揮手留足揮動空間。
      pose_target.rUpperZ = 0.15;   // 接近水平高舉（REST 為 ~1.21 rad，0 = T-Pose 水平）
      pose_target.rUpperX = -0.7;   // 微向前傾
      pose_target.rForeX = 1.5;     // 前臂強彎
      set_left_arm_rest();
      expr_target.happy = 1.0;
      expr_target.relaxed = 0;
      expr_target.surprised = 0;
      expr_target.aa = 0;
      expr_target.ih = 0;
    } else if (next_state === "listening") {
      set_both_arms_rest();
      // 微睜 + 認真聽（relaxed 少量），頭部前傾/側傾於 head follow 處理。
      expr_target.happy = 0.18;
      expr_target.relaxed = 0.18;
      expr_target.surprised = 0.08;
      expr_target.aa = 0;
      expr_target.ih = 0;
    } else if (next_state === "talking") {
      set_both_arms_rest();
      // 右手微抬解說手勢。
      pose_target.rUpperZ = (Math.PI / 2.6) * 0.72;
      pose_target.rUpperX = -0.35;
      pose_target.rForeX = 0.85;
      expr_target.happy = 0.4;
      expr_target.relaxed = 0;
      expr_target.surprised = 0;
    } else {
      // idle
      set_both_arms_rest();
      expr_target.happy = RESTING_HAPPY;
      expr_target.relaxed = 0;
      expr_target.surprised = 0;
      expr_target.aa = 0;
      expr_target.ih = 0;
    }
  }

  function set_left_arm_rest() {
    pose_target.lUpperZ = REST_POSE.lUpperZ;
    pose_target.lUpperX = 0;
    pose_target.lForeX = REST_POSE.lForeX;
  }

  function set_both_arms_rest() {
    pose_target.lUpperZ = REST_POSE.lUpperZ;
    pose_target.rUpperZ = REST_POSE.rUpperZ;
    pose_target.lUpperX = 0;
    pose_target.rUpperX = 0;
    pose_target.lForeX = REST_POSE.lForeX;
    pose_target.rForeX = REST_POSE.rForeX;
  }

  function enter_listening() {
    if (agent_state !== "talking" && agent_state !== "listening") {
      set_state("listening");
    }
  }

  function frame_upper_body() {
    // 不可用 Box3：此模型由 MMD 轉換，第 0 幀 SpringBone 物理尚未穩定，
    // Box3 會量到極端異常的巨大邊界，導致相機被推到數萬單位外、畫面全黑。
    // 改用「絕對安全座標 + 防呆夾擠」：以頭骨高度為基準、固定安全後退距離。
    vrm_model.scene.updateMatrixWorld(true);

    let head_y = 1.4; // 絕對安全預設值（適用多數日系人形模型）
    let head_x = 0;
    let head_z = 0;

    // 用真實 Head node 的世界座標（humanoid 'head' 槽是緞帶骨，不可用）。
    if (head_node) {
      const pos = new THREE.Vector3();
      head_node.getWorldPosition(pos);
      // 防呆：僅在合理人形身高範圍內採用，否則退回預設值，避免異常座標。
      if (pos.y > 0.5 && pos.y < 2.5) {
        head_y = pos.y;
      }
      if (Math.abs(pos.x) < 1.5) {
        head_x = pos.x;
      }
      if (Math.abs(pos.z) < 1.5) {
        head_z = pos.z;
      }
    }

    model_scale_ref = head_y / 1.4; // 互動位移用的尺度基準

    // 對焦點：胸口到臉部之間（頭骨往下 0.2 單位）。
    const target_y = head_y - 0.2;
    // 固定安全距離：Z 軸退後約 2.2 單位，拍到更完整的半身（含放下的手臂）。
    const safe_distance = 2.8;
    // 鏡頭水平視角（相機與對焦點同高，不俯不仰）。
    const camera_tilt = 0;
    // 整體向上平移（負值向下移）。
    const pan_up = -0.12;

    const focus_y = target_y + pan_up;
    const camera_height = focus_y + camera_tilt;

    camera.position.set(head_x, camera_height, head_z + safe_distance);
    camera.lookAt(head_x, focus_y, head_z);
    camera.updateProjectionMatrix();
  }

  function tick() {
    requestAnimationFrame(tick);
    const delta = clock.getDelta();
    const elapsed = clock.elapsedTime;

    update_state(delta);

    // 姿勢通道平滑過渡（lerp，禁止突變）。
    const pose_k = Math.min(1, delta * 6);
    for (const key of POSE_KEYS) {
      pose_current[key] = THREE.MathUtils.lerp(pose_current[key], pose_target[key], pose_k);
    }

    // 表情通道平滑過渡。
    const expr_k = Math.min(1, delta * 8);
    for (const key of EXPR_KEYS) {
      expr_current[key] = THREE.MathUtils.lerp(expr_current[key], expr_target[key], expr_k);
    }

    // 偽唇形同步：talking 時 aa / ih 快速擺動（直接覆蓋 current，繞過慢速 lerp）。
    if (agent_state === "talking") {
      const mouth = Math.sin(elapsed * 18) * 0.5 + 0.5; // 0~1 快速開合
      const jitter = 0.7 + 0.3 * (Math.sin(elapsed * 11) * 0.5 + 0.5);
      expr_current.aa = mouth * 0.6 * jitter;
      expr_current.ih = (1 - mouth) * 0.35 * jitter;
    }

    // 套用表情。
    if (vrm_model.expressionManager) {
      for (const key of EXPR_KEYS) {
        vrm_model.expressionManager.setValue(key, expr_current[key]);
      }
    }

    // 週期性附加偏移：待機呼吸。
    const breath = Math.sin(elapsed * 1.4) * 0.022;
    apply_pose_to_bones(breath);

    // 有機揮手動畫：welcoming 時前臂（bone_r_fore）左右搖擺 + 腕部相位差跟隨；
    // 非 welcoming 時 lerp 回 0，確保切換狀態時平滑歸零，不突變。
    if (bone_r_fore) {
      const wt = elapsed * 4.8; // 揮手速度（~5 rad/s，接近 Date.now()*0.008 效果）
      const target_fore_z = agent_state === "welcoming" ? Math.sin(wt) * 0.48 : 0;
      const target_fore_y = agent_state === "welcoming" ? Math.sin(wt - 0.5) * 0.22 : 0;
      bone_r_fore.rotation.z = THREE.MathUtils.lerp(bone_r_fore.rotation.z, target_fore_z, 0.25);
      bone_r_fore.rotation.y = THREE.MathUtils.lerp(bone_r_fore.rotation.y, target_fore_y, 0.18);
    }

    // 更新 VRM（套用 humanoid 骨架/表情/物理）。Head/Neck 不在 humanoid 對應內，
    // 故 update 不會覆蓋它們，可在其後安全地疊加視線跟隨與待機微動。
    vrm_model.update(delta);
    update_head_follow(elapsed);

    renderer.render(scene, camera);
  }

  function update_state(delta) {
    if (agent_state === "welcoming" || agent_state === "talking") {
      state_timer -= delta;
      if (state_timer <= 0) {
        set_state("idle");
      }
    }
  }

  function update_head_follow(elapsed) {
    if (!head_node || !head_base_quat) {
      return;
    }

    // 局部追視：look_target 由滑鼠（半徑內）或 0（半徑外，自然回正）給定，這裡平滑趨近。
    look_nx = THREE.MathUtils.lerp(look_nx, look_target_nx, 0.08);
    look_ny = THREE.MathUtils.lerp(look_ny, look_target_ny, 0.08);

    // 待機微動：極小幅度隨機相位正弦，打破僵直。
    const idle_yaw = Math.sin(elapsed * 0.7 + IDLE_PHASE_A) * 0.03;
    const idle_pitch = Math.sin(elapsed * 0.9 + IDLE_PHASE_B) * 0.025;

    // 傾聽：頭微前傾 + 側傾。
    let state_pitch = 0;
    let state_roll = 0;
    if (agent_state === "listening") {
      state_pitch = 0.12;
      state_roll = 0.08;
    }

    const yaw = look_nx * HEAD_MAX_YAW + idle_yaw;
    const pitch = look_ny * HEAD_MAX_PITCH + idle_pitch + state_pitch;
    const roll = state_roll;

    // 世界空間建立 yaw/pitch/roll 附加旋轉，再換算回頭骨 local（不受 PMX local roll 影響）。
    _q_yaw.setFromAxisAngle(WORLD_UP, yaw);
    _q_pitch.setFromAxisAngle(WORLD_RIGHT, pitch);
    _q_roll.setFromAxisAngle(WORLD_FORWARD, roll);
    _q_world.copy(_q_yaw).multiply(_q_pitch).multiply(_q_roll);

    const parent = head_node.parent;
    if (parent) {
      parent.getWorldQuaternion(_parent_q);
      _parent_q_inv.copy(_parent_q).invert();
      _head_base_world.copy(_parent_q).multiply(head_base_quat);
      _desired_local
        .copy(_parent_q_inv)
        .multiply(_q_world)
        .multiply(_head_base_world);
    } else {
      _desired_local.copy(_q_world).multiply(head_base_quat);
    }

    head_node.quaternion.slerp(_desired_local, 0.15);

    // 頸部待機微動（極小幅度；Neck 不在 humanoid 對應內，不會被 update 覆蓋）。
    if (neck_node && neck_base) {
      neck_node.rotation.set(
        neck_base.x + Math.sin(elapsed * 0.8 + IDLE_PHASE_B) * 0.012,
        neck_base.y + Math.sin(elapsed * 0.6 + IDLE_PHASE_A) * 0.015,
        neck_base.z
      );
    }
  }

  function on_mouse_move(event) {
    // 局部座標追視：以客服容器中心為基準，半徑內追隨、半徑外回正。
    const rect = assistant_root.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = event.clientX - cx;
    const dy = event.clientY - cy;

    if (Math.hypot(dx, dy) <= LOOK_RADIUS) {
      look_target_nx = THREE.MathUtils.clamp(dx / LOOK_RADIUS, -1, 1);
      // DOM Y 向下為正；Three.js pitch 正值向前傾（看下方），故同號即正確，不需取負。
      look_target_ny = THREE.MathUtils.clamp(dy / LOOK_RADIUS, -1, 1);
    } else {
      look_target_nx = 0;
      look_target_ny = 0;
    }
  }

  function on_resize() {
    const width = canvas_wrap.clientWidth;
    const height = canvas_wrap.clientHeight;
    if (!width || !height) {
      return;
    }
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  function set_speech_text(text, visible = true) {
    speech_box.textContent = text;
    speech_box.classList.toggle("is-visible", visible);
  }

  function start_loading() {
    const loading_frames = ["思考中", "思考中.", "思考中..", "思考中..."];
    let frame_index = 0;
    set_speech_text(loading_frames[frame_index], true);
    loading_timer = window.setInterval(() => {
      frame_index = (frame_index + 1) % loading_frames.length;
      set_speech_text(loading_frames[frame_index], true);
    }, 340);
  }

  function stop_loading() {
    if (loading_timer) {
      window.clearInterval(loading_timer);
      loading_timer = null;
    }
  }

  function schedule_hide_speech(delay_ms = 12000) {
    if (hide_timer) {
      window.clearTimeout(hide_timer);
    }
    hide_timer = window.setTimeout(() => {
      speech_box.classList.remove("is-visible");
    }, delay_ms);
  }

  async function submit_message() {
    const message = input_element.value.trim();
    if (!message || is_sending) {
      return;
    }

    // 固定回覆：不送 API，直接顯示預設文字。
    if (Object.prototype.hasOwnProperty.call(FIXED_REPLIES, message)) {
      const reply = FIXED_REPLIES[message];
      input_element.value = "";
      set_speech_text(reply, true);
      schedule_hide_speech(8000);
      set_state("talking");
      state_timer = THREE.MathUtils.clamp(reply.length * 0.06, 1.5, 8);
      return;
    }

    is_sending = true;
    input_element.disabled = true;
    send_button.disabled = true;
    start_loading();

    try {
      const response = await fetch(chat_url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": get_cookie("csrftoken"),
        },
        body: JSON.stringify({ message }),
      });

      let payload = {};
      try {
        payload = await response.json();
      } catch (_) {
        payload = {};
      }

      if (!response.ok) {
        const error_message = payload.error || `HTTP ${response.status}`;
        set_speech_text(`發生錯誤：${error_message}`, true);
        schedule_hide_speech(14000);
        return;
      }

      const reply = payload.reply || payload.message || payload.response || "已收到訊息，但暫時沒有可顯示內容。";
      set_speech_text(reply, true);
      schedule_hide_speech(18000);
      input_element.value = "";
      // 進入「對話」狀態：解說手勢 + 偽唇形同步，時長依回覆長度估算。
      set_state("talking");
      state_timer = THREE.MathUtils.clamp(reply.length * 0.06, 1.5, 8);
    } catch (error) {
      console.error("[AI VRM Assistant] 發送失敗:", error);
      set_speech_text("連線失敗，請稍後再試。", true);
      schedule_hide_speech(12000);
    } finally {
      stop_loading();
      is_sending = false;
      input_element.disabled = false;
      send_button.disabled = false;
      input_element.focus();
    }
  }

}

function get_cookie(name) {
  const key = `${name}=`;
  const cookies = document.cookie ? document.cookie.split(";") : [];
  for (let i = 0; i < cookies.length; i += 1) {
    const cookie = cookies[i].trim();
    if (cookie.startsWith(key)) {
      return decodeURIComponent(cookie.slice(key.length));
    }
  }
  return "";
}
