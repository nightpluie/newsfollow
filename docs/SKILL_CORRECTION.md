# ⚠️ Skills API 使用方式修正說明

## 問題發現

原始實作**錯誤地**只是將 SKILL.md 的內容複製到 system prompt,這**不是**真正使用 Claude Skills API 的方式。

## ❌ 錯誤做法 (原始版本)

```python
# 只是讀取技能文件內容
SKILL_PATH = "/Users/nightpluie/Desktop/AI bots/report-tcy/SKILL.md"
with open(SKILL_PATH, 'r', encoding='utf-8') as f:
    TCY_SKILL = f.read()

# 錯誤地放到 system prompt
system_prompt = f"""你是專業記者...

{TCY_SKILL}  # ← 這不是真正的 Skill!只是文字

請改寫..."""

# 一般 API 呼叫
message = self.claude.messages.create(
    model="claude-sonnet-4-20250514",
    system=system_prompt,  # ← 沒有真正使用 Skills API
    messages=[...]
)
```

### 為什麼這是錯的?

1. **不是 Skills API** - 只是把技能當文字貼到 prompt
2. **沒有 Code Execution** - Skill 需要執行環境
3. **沒有 Progressive Disclosure** - 無法動態載入 skill 的不同部分
4. **沒有 Files API** - 無法處理 skill 的檔案系統

## ✅ 正確做法 (修正版本)

```python
def _upload_skill(self):
    """正確上傳 Skill"""
    # 1. 上傳 skill 檔案
    skill_files = []

    # 上傳 SKILL.md
    with open(skill_path / "SKILL.md", 'rb') as f:
        skill_files.append(
            self.claude.files.create(
                file=f,
                purpose="skill"  # ← 專門的 purpose
            )
        )

    # 上傳 references 目錄
    for ref_file in references_dir.rglob('*'):
        if ref_file.is_file():
            with open(ref_file, 'rb') as f:
                skill_files.append(
                    self.claude.files.create(file=f, purpose="skill")
                )

    # 2. 建立 Skill
    skill = self.claude.beta.skills.create(
        files=[f.id for f in skill_files],
        betas=["skills-2025-01-28"]  # ← Beta feature
    )

    self.skill_id = skill.id  # ← 取得 Skill ID

def rewrite_with_claude(self, original_title, original_url):
    """正確使用 Skill"""
    message = self.claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,

        # 3. 必要的 Beta Headers
        betas=[
            "skills-2025-01-28",           # Skills API
            "code-execution-2024-10-22"    # Code Execution Tool
        ],

        # 4. 在 container 中指定 skill
        container={
            "skills": [{"id": self.skill_id, "version": "latest"}]
        },

        # 5. 啟用 Code Execution Tool
        tools=[{"type": "code_execution"}],

        messages=[{"role": "user", "content": user_prompt}]
    )
```

## 🔍 關鍵差異對照

| 項目 | 錯誤做法 | 正確做法 |
|------|----------|----------|
| **Skill 載入** | 讀取文字檔案 | 上傳到 Files API |
| **Skill 啟用** | 貼到 system prompt | 使用 `container.skills` |
| **Beta Headers** | 無 | `skills-2025-01-28` + `code-execution` |
| **Code Execution** | 無 | `tools=[{"type": "code_execution"}]` |
| **Progressive Disclosure** | 不支援 | ✅ 支援 (只讀需要的部分) |
| **檔案系統** | 無 | ✅ 有 (skill 的 assets 等) |

## 📋 正確使用 Skills API 的必要條件

### 1. Beta Features 啟用

```python
betas=[
    "skills-2025-01-28",           # Skills API
    "code-execution-2024-10-22",   # Code Execution (必需!)
    "files-2024-10-22"             # Files API (如果需要上傳檔案)
]
```

### 2. Code Execution Tool

Skills **必須**搭配 Code Execution Tool 使用:

```python
tools=[{"type": "code_execution"}]
```

這提供:
- 隔離的執行環境 (sandbox/container)
- 檔案系統存取
- Bash 命令執行能力

### 3. Container 設定

```python
container={
    "skills": [
        {"id": skill_id, "version": "latest"},
        # 可以同時使用多個 skills
        {"id": "docx", "version": "latest"}  # 內建 skill
    ]
}
```

## 🎯 實際運作流程

### 正確的 Skills API 流程:

```
1. 上傳 Skill 檔案
   ↓
   client.files.create(file=..., purpose="skill")

2. 建立 Skill
   ↓
   client.beta.skills.create(files=[...])
   ↓
   取得 skill_id

3. 使用 Skill
   ↓
   client.messages.create(
       betas=["skills-2025-01-28", "code-execution-2024-10-22"],
       container={"skills": [{"id": skill_id}]},
       tools=[{"type": "code_execution"}],
       ...
   )

4. Claude 執行
   ↓
   - 在 container 中讀取 SKILL.md
   - Progressive disclosure (只讀需要的部分)
   - 執行 skill 中的 code
   - 存取 skill 的 assets/references
```

## 🔬 Progressive Disclosure

這是 Skills 的重要特性:

```python
# Claude 不會一次讀取整個 SKILL.md
# 而是根據需要逐步讀取:

# Step 1: 只讀 SKILL.md 前面的描述
"I'll help you rewrite this news article..."

# Step 2: 需要時讀取特定 section
"Let me check the template section..."
bash("cat /skill/assets/markdown_template.md")

# Step 3: 執行 skill 中的 code
bash("python /skill/scripts/format_article.py")
```

## 📊 驗證方式

檢查 API response 中的 `content` 欄位:

```python
response = client.messages.create(...)

# 正確使用 Skills 會看到:
for block in response.content:
    if block.type == "tool_use":
        print(block.name)  # 應該會看到 "code_execution"
        print(block.input)  # 應該會看到讀取 /skill/... 的指令
```

## ⚙️ 修正後的系統架構

```
news_dashboard.py
├── __init__()
│   ├── 建立 Anthropic client
│   └── _upload_skill()  ← 上傳並建立 Skill
│       ├── 上傳 SKILL.md
│       ├── 上傳 references/*
│       └── client.beta.skills.create()
│
└── rewrite_with_claude()
    └── client.messages.create()
        ├── betas=["skills-2025-01-28", "code-execution-2024-10-22"]
        ├── container={"skills": [{"id": skill_id}]}
        └── tools=[{"type": "code_execution"}]
```

## 🎁 修正後的優勢

1. ✅ **真正使用 Skills API** - 不是模擬
2. ✅ **Progressive Disclosure** - 效能更好
3. ✅ **執行環境隔離** - 安全沙箱
4. ✅ **支援完整 Skill 功能** - assets, scripts, templates
5. ✅ **與 Claude AI/Desktop 一致** - 相同的 skill 格式

## 📝 總結

| 層面 | 原始版本 | 修正版本 |
|------|----------|----------|
| **本質** | 只是文字貼上 | 真正的 Skills API |
| **功能** | 基本提示詞 | 完整 Skill 能力 |
| **效能** | 一次載入全部 | Progressive Disclosure |
| **相容性** | 不可移植 | 與 Claude AI/Desktop 相容 |
| **可維護性** | 修改困難 | Skill 獨立維護 |

## 🚀 使用修正版本

現在啟動儀表板會:

1. 自動上傳唐鎮宇寫作技能
2. 取得 Skill ID
3. 使用真正的 Skills API 改寫新聞

```bash
cd /Users/nightpluie/Desktop/newsfollow
./start_dashboard.sh
```

啟動時會看到:

```
✅ 唐鎮宇寫作技能已啟用 (ID: skill_xxx...)
```

如果看到:

```
⚠️  使用 Fallback 模式 (未啟用 skill)
```

表示 skill 上傳失敗,會退回到原本的 system prompt 模式。

---

**感謝指正!現在是真正使用 Claude Skills API 了! 🎉**
