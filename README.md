# 斗鱼主播等级排行榜 Top 100

实时展示斗鱼（www.douyu.com）全站主播等级排名前100名，每15分钟自动更新。

## 📸 预览

深色主题，支持桌面端和移动端。前三名金银铜徽章，100级+主播高亮标记。

## 🚀 一键部署（GitHub Pages）

### 1. Push 到 GitHub

```bash
cd douyurank
git init
git add .
git commit -m "Initial commit: Douyu streamer rank"
git branch -M main
git remote add origin git@github.com:YOUR_USERNAME/douyurank.git
git push -u origin main
```

### 2. 开启 GitHub Pages

- 进入仓库 → Settings → Pages
- Source: **Deploy from a branch**
- Branch: `main` → `/ (root)` → Save
- 等待 1-2 分钟后访问 `https://YOUR_USERNAME.github.io/douyurank/`

### 3. 验证自动更新

GitHub Actions 会每 15 分钟自动运行爬虫并更新 `data.json`。进入 Actions 标签页查看运行状态。

## 🏗️ 项目结构

```
douyurank/
├── .github/workflows/update-rank.yml  # GitHub Actions 定时任务
├── scraper.py                         # 异步爬虫 (支持 --ci 模式)
├── index.html                         # 前端排行榜页面
├── data.json                          # 排行榜数据 (自动更新)
├── test_project.py                    # 自动化测试套件
├── requirements.txt                   # Python 依赖
├── .gitignore
└── README.md
```

## 🔧 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
python test_project.py

# 手动运行爬虫
python scraper.py

# 查看排行榜
start index.html
```

## ⚠️ 注意事项

- **数据来源**: 斗鱼公开 API，仅供学习研究使用
- **GitHub Actions IP**: 如果斗鱼屏蔽了 GitHub Actions 的美国 IP，爬虫可能失败。此时 data.json 会保留上一次成功的数据
- **更新频率**: 每 15 分钟。斗鱼 API 数据本身有分钟级延迟，更频繁拉取无意义
- **数据过时**: 如果超过 2 小时未更新，页面会显示黄色警告；超过 6 小时显示红色警告
