import streamlit as st
import os
import time
import shutil
from datetime import datetime

# --- 1. 基础配置与安全 ---
st.set_page_config(page_title="文件交付互助站", layout="wide", page_icon="⚡")

# 数据存储根目录
BASE_DIR = "workstation_data"
# 文件自动销毁时间（小时）
EXPIRY_HOURS = 24

# 从 Secrets 获取管理员密码和隐藏入口
# 如果本地运行没有配置 secrets，则使用默认值
try:
    ADMIN_PWD = st.secrets["admin_password"]
    ADMIN_URL_KEY = st.secrets["admin_url_key"]
except FileNotFoundError:
    ADMIN_PWD = "admin"  
    ADMIN_URL_KEY = "secret_admin"

# 确保根目录存在
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# --- 2. 核心工具函数 ---

def get_path(code, sub_folder):
    """根据提取码构建安全的文件路径"""
    # 仅保留字母和数字，防止路径攻击
    safe_code = "".join([c for c in code if c.isalnum()])
    if not safe_code: return None
    
    full_path = os.path.join(BASE_DIR, safe_code, sub_folder)
    if not os.path.exists(full_path):
        os.makedirs(full_path)
    return full_path

def manage_message(code, role, mode="read", text=""):
    """读写留言板 (role: user 或 admin)"""
    msg_dir = get_path(code, "messages")
    if not msg_dir: return ""
    
    file_path = os.path.join(msg_dir, f"{role}.txt")
    
    if mode == "write":
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
    elif mode == "read":
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
    return ""

def cleanup_old_files():
    """清理超过 24 小时的旧工单"""
    now = time.time()
    if os.path.exists(BASE_DIR):
        for folder in os.listdir(BASE_DIR):
            folder_path = os.path.join(BASE_DIR, folder)
            if os.path.isdir(folder_path):
                # 检查文件夹修改时间
                if os.path.getmtime(folder_path) < now - (EXPIRY_HOURS * 3600):
                    try:
                        shutil.rmtree(folder_path)
                    except Exception as e:
                        print(f"Cleanup error: {e}")

# 每次运行前执行清理
cleanup_old_files()

# --- 3. 逻辑分流 ---

# 获取 URL 参数 (例如: ?view=secret_admin)
query_params = st.query_params
current_view = query_params.get("view", None)

# --- 4. 👨‍🔧 管理员后台 (隐藏模式) ---
if current_view == ADMIN_URL_KEY:
    st.markdown("## 🛠️ 互助站·驾驶舱")
    
    # 侧边栏登录
    input_pwd = st.sidebar.text_input("管理员密码", type="password")
    
    if input_pwd == ADMIN_PWD:
        st.sidebar.success("身份验证通过")
        
        # 扫描所有任务文件夹
        all_tasks = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
        
        if not all_tasks:
            st.info("🍵 暂无待处理工单，喝杯咖啡吧。")
        
        st.write(f"当前共有 **{len(all_tasks)}** 个活跃任务（24h内自动清理）")

        # 遍历展示每个任务
        for code in all_tasks:
            with st.expander(f"🎫 工单号：{code}", expanded=False):
                col1, col2 = st.columns(2)
                
                # 左侧：用户提交的内容
                with col1:
                    st.caption("📥 用户投递箱")
                    user_msg = manage_message(code, "user", "read")
                    if user_msg:
                        st.warning(f"用户留言：\n{user_msg}")
                    else:
                        st.text("用户无留言")
                    
                    inbox_path = get_path(code, "Inbox")
                    files = os.listdir(inbox_path)
                    if files:
                        for f_name in files:
                            f_path = os.path.join(inbox_path, f_name)
                            with open(f_path, "rb") as f:
                                st.download_button(
                                    f"⬇️ 下载用户文件: {f_name}",
                                    f,
                                    file_name=f"{code}_{f_name}"
                                )
                    else:
                        st.info("用户暂未上传文件")

                # 右侧：管理员处理区域
                with col2:
                    st.caption("📤 结果交付箱")
                    
                    # 回复留言
                    old_reply = manage_message(code, "admin", "read")
                    new_reply = st.text_area("回复进度/备注：", value=old_reply, key=f"txt_{code}")
                    if st.button("更新回复", key=f"btn_{code}"):
                        manage_message(code, "admin", "write", new_reply)
                        st.toast("回复已更新！")
                    
                    # 上传结果文件
                    uploaded_res = st.file_uploader("上传处理结果 (支持任意格式)", key=f"up_{code}")
                    if uploaded_res:
                        outbox_path = get_path(code, "Outbox")
                        save_path = os.path.join(outbox_path, uploaded_res.name)
                        with open(save_path, "wb") as f:
                            f.write(uploaded_res.getbuffer())
                        st.success(f"已回传：{uploaded_res.name}")
                        # 强制刷新以显示最新状态（可选）
                        time.sleep(1)
                        st.rerun()

    elif input_pwd:
        st.error("密码错误 🚫")

# --- 5. 🚀 用户前台界面 ---
else:
    # 顶部 Hero 区域
    st.markdown("""
    <div style='text-align: center; padding: 20px;'>
        <h1>⚡ 文件交付互助站</h1>
        <p style='color: #666;'>WPS会员功能解锁 | NotebookLLM 资料整理 | 复杂格式转换</p>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        col_input, col_tips = st.columns([2, 1])
        
        with col_input:
            u_code = st.text_input("🔑 请输入/设置您的专属提取码", placeholder="例如：Alex2024", help="凭此码上传文件和取回结果，请勿泄露")
        
        with col_tips:
            st.info("💡 **服务流程**：\n1. 输入提取码进入空间\n2. 上传资料并留言\n3. 等待管理员处理回传")

    if u_code:
        # 简单校验
        if len(u_code) < 3:
            st.warning("⚠️ 提取码太短，请至少输入 3 位字符。")
        else:
            # 这里的 Tab 布局非常关键，实现了“双向”感
            tab1, tab2 = st.tabs(["📤 **提交需求**", "📥 **收取结果**"])

            # --- Tab 1: 用户提交 ---
            with tab1:
                st.write("#### 1. 您的需求")
                current_note = manage_message(u_code, "user", "read")
                note_input = st.text_area("请描述具体需求（如：PDF转PPT，提取第3页表格等）", value=current_note, height=100)
                
                if st.button("💾 保存留言"):
                    manage_message(u_code, "user", "write", note_input)
                    st.success("需求已备注，管理员可见。")

                st.write("#### 2. 上传文件")
                st.caption("支持 PDF, ZIP, DOCX, PPTX 等所有格式，最大支持 1GB")
                
                # accept_multiple_files=True 允许一次传多个
                uploaded_files = st.file_uploader("拖拽文件到此处", accept_multiple_files=True)
                
                if uploaded_files:
                    inbox = get_path(u_code, "Inbox")
                    for up_f in uploaded_files:
                        save_path = os.path.join(inbox, up_f.name)
                        with open(save_path, "wb") as f:
                            f.write(up_f.getbuffer())
                        st.toast(f"✅ {up_f.name} 上传成功！")
                    st.success("所有文件已安全投递到云端收件箱。")

            # --- Tab 2: 结果查询 ---
            with tab2:
                st.write("#### 📬 进度反馈")
                
                # 查看管理员回复
                admin_reply = manage_message(u_code, "admin", "read")
                if admin_reply:
                    st.info(f"👨‍💻 **管理员回复：**\n\n{admin_reply}")
                else:
                    st.caption("暂无回复，请稍后...")

                st.write("#### 🎁 下载结果")
                outbox = get_path(u_code, "Outbox")
                if os.path.exists(outbox):
                    results = os.listdir(outbox)
                    if results:
                        for res in results:
                            res_path = os.path.join(outbox, res)
                            with open(res_path, "rb") as f:
                                st.download_button(
                                    label=f"📥 点击下载：{res}",
                                    data=f,
                                    file_name=res,
                                    mime="application/octet-stream"
                                )
                    else:
                        st.markdown("Processing... ⏳ **正在处理中**")
                        st.caption("若等待时间过长，请私信管理员催单。")
                else:
                    st.caption("您的空间已创建，等待结果回传...")

    st.divider()
    st.caption("🛡️ 数据安全声明：所有文件仅做临时中转，系统将在 24 小时后自动永久粉碎。请勿上传涉及个人隐私（身份证/银行卡）的敏感文件。")
