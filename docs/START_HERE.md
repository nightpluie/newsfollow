# 🚀 新聞監控儀表板 - 使用 Skills API

## ✅ 技能已成功上傳

您的唐鎮宇寫作技能已經上傳到 Claude API：
- **Skill ID**: `skill_013Hgp6psVYYF7AjWCyPJFNd`
- **Display Title**: 唐鎮宇寫作技能
- **Version**: `latest`

## 🎯 啟動步驟

### 1. 啟動伺服器

```bash
cd /Users/nightpluie/Desktop/newsfollow
source .venv/bin/activate
python3 news_dashboard_with_real_skills.py
```

### 2. 訪問儀表板

打開瀏覽器: **http://localhost:8080**

## 📊 功能說明

1. **開始爬取並分析** - 爬取 UDN、TVBS、ETtoday 新聞
2. **查看三家媒體新聞** - 顯示所有爬取的新聞標題
3. **ETtoday 缺少的新聞** - 自動比對找出遺漏
4. **用 Claude 改寫** - 使用真正的 Skills API 與唐鎮宇寫作技能改寫

## 🔧 技術細節

### 真正的 Skills API vs System Prompt

**之前的錯誤方式 (news_dashboard.py)**:
```python
# ❌ 只是把 SKILL.md 貼到 system prompt
system_prompt = f"請遵循以下技能:\n\n{skill_content}"
message = client.messages.create(
    system=system_prompt,  # 只是文字參考
    ...
)
```

**現在的正確方式 (news_dashboard_with_real_skills.py)**:
```python
# ✅ 使用真正的 Skills API
message = client.beta.messages.create(
    betas=["code-execution-2025-08-25", "skills-2025-10-02"],
    container={
        "skills": [
            {
                "type": "custom",
                "skill_id": "skill_013Hgp6psVYYF7AjWCyPJFNd",
                "version": "latest"
            }
        ]
    },
    tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
    ...
)
```

## 📝 Skills API 優勢

1. ✅ **Progressive Disclosure** - 技能內容按需載入，不占用 context
2. ✅ **Code Execution** - 支援執行 Python 程式碼
3. ✅ **Files API** - 可上傳下載檔案
4. ✅ **版本控制** - 支援多版本管理
5. ✅ **組織共享** - Workspace 內所有成員可用

## 🆚 兩個版本比較

| 檔案 | 方式 | 備註 |
|------|------|------|
| `news_dashboard.py` | System Prompt | 舊版，只是文字參考 |
| `news_dashboard_with_real_skills.py` | Skills API | ✅ 新版，真正的技能執行 |

## 🎓 學到的重點

1. **Skills API 完全支援 Python SDK** - 通過 `client.beta.skills`
2. **需要三個 beta headers** - `code-execution`, `skills`, `files-api`
3. **技能格式要求**:
   - 必須有 SKILL.md (含 YAML frontmatter)
   - `name`: 小寫、連字號、最多 64 字元
   - `description`: 最多 1024 字元
   - 總大小 < 8MB
4. **上傳方式**:
   - `files_from_dir()` - 直接從目錄
   - Zip 檔案上傳
   - Console UI 手動上傳

## 📚 參考文件

- Skills Overview: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Skills API Guide: https://platform.claude.com/docs/en/build-with-claude/skills-guide
- API Reference: https://platform.claude.com/docs/en/api/skills/create-skill

---

**準備好了！現在啟動 `news_dashboard_with_real_skills.py` 就能使用真正的 Skills API！** 🎉
