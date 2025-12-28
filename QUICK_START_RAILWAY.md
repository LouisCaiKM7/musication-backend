# Railway 快速部署指南（5分钟）

## 🚀 快速部署步骤

### 1. 准备 GitHub 仓库（如果还没有）

```bash
cd e:\0_comps\00_conrad_2526\musication-backend
git init  # 如果还没初始化
git add .
git commit -m "Prepare for Railway deployment"
git branch -M main
git remote add origin https://github.com/你的用户名/musication-backend.git
git push -u origin main
```

### 2. 登录 Railway

1. 访问 https://railway.app/
2. 点击 "Login" → "Login with GitHub"
3. 授权 Railway 访问你的 GitHub

### 3. 创建项目（Web UI 方式）

**步骤 A: 新建项目**
1. 点击 "New Project"
2. 选择 "Deploy from GitHub repo"
3. 选择 `musication-backend` 仓库
4. Railway 会自动开始构建

**步骤 B: 添加数据库**
1. 在项目面板中，点击 "+ New"
2. 选择 "Database" → "PostgreSQL"
3. 等待数据库创建完成（约30秒）

**步骤 C: 配置环境变量**
1. 点击你的后端服务
2. 进入 "Variables" 标签
3. 点击 "+ New Variable" 添加以下变量：

```
FLASK_ENV=production
FRONTEND_URL=https://musicationapp.netlify.app
ENABLE_MELODY_ANALYSIS=false
```

**注意：** `DATABASE_URL` 和 `PORT` 由 Railway 自动提供，无需手动设置

**步骤 D: 获取后端 URL**
1. 部署完成后，进入 "Settings" → "Networking"
2. 点击 "Generate Domain"
3. 复制生成的 URL（如：`https://musication-backend-production.up.railway.app`）

**步骤 E: 更新 BASE_URL**
1. 回到 "Variables" 标签
2. 添加新变量：
```
BASE_URL=https://你刚才复制的URL.up.railway.app
```

### 4. 更新前端配置

**如果前端在 Netlify：**
1. 进入 Netlify Dashboard → Site settings → Environment variables
2. 编辑 `NEXT_PUBLIC_API_URL`
3. 改为：`https://你的Railway后端URL.up.railway.app`
4. 进入 Deploys → Trigger deploy → Deploy site

**如果想迁移前端到 Vercel：**
```bash
cd e:\0_comps\00_conrad_2526\musication-frontend
npm install -g vercel
vercel
# 按提示操作，设置环境变量：
# NEXT_PUBLIC_API_URL=https://你的Railway后端URL.up.railway.app
```

### 5. 测试部署

```bash
# 测试健康检查
curl https://你的Railway后端URL.up.railway.app/health
# 应该返回: {"status":"ok"}

# 测试 API
curl https://你的Railway后端URL.up.railway.app/api/library/stats
# 应该返回统计信息
```

---

## 🔧 使用 Railway CLI 部署（进阶）

### 安装 CLI

**Windows (PowerShell):**
```powershell
iwr https://railway.app/install.ps1 | iex
```

**Mac/Linux:**
```bash
sh <(curl -fsSL https://railway.app/install.sh)
```

### 通过 CLI 部署

```bash
cd e:\0_comps\00_conrad_2526\musication-backend

# 登录
railway login

# 初始化项目
railway init

# 链接到现有项目（或创建新项目）
railway link

# 添加 PostgreSQL
railway add --database postgresql

# 设置环境变量
railway variables set FLASK_ENV=production
railway variables set ENABLE_MELODY_ANALYSIS=false

# 部署
railway up

# 查看日志
railway logs

# 获取部署 URL
railway domain
```

---

## 📊 部署后验证

### 检查清单

- [ ] 后端服务状态为 "Active"
- [ ] PostgreSQL 数据库运行正常
- [ ] `/health` 端点返回 200 OK
- [ ] 前端能连接到后端 API
- [ ] 文件上传功能正常
- [ ] 音乐识别功能正常

### 常见问题

**Q: 构建失败，提示找不到 chromaprint？**
A: 检查 Dockerfile 是否包含 chromaprint 安装（已在第 5-9 行配置）

**Q: 内存不足错误？**
A: 
1. 确保设置了 `ENABLE_MELODY_ANALYSIS=false`
2. 考虑升级到 Railway Pro（$5/月）获得更多资源

**Q: 数据库连接失败？**
A: 检查 Railway 的 PostgreSQL 服务是否在同一项目中，Railway 会自动连接

**Q: CORS 错误？**
A: 确保 `FRONTEND_URL` 环境变量与实际前端 URL 匹配

---

## 💰 费用说明

**Railway 免费额度：**
- ✅ $5 免费额度/月（约 500 小时运行时间）
- ✅ 8GB 内存限制（远超你的需求）
- ✅ 100GB 网络流量/月

**预计使用：**
- 轻度使用：完全免费
- 中度使用：约 $5-10/月
- 重度使用：约 $15-20/月

**节省费用技巧：**
1. 设置 `ENABLE_MELODY_ANALYSIS=false` 减少内存使用
2. 使用 Railway Sleep（闲置时自动休眠）
3. 监控 Metrics 标签中的资源使用

---

## 🔄 持续部署

**自动部署：**
- 推送到 `main` 分支会自动触发 Railway 部署
- 无需手动操作

**手动部署：**
```bash
railway up
```

**回滚：**
1. 进入 "Deployments" 标签
2. 找到之前的成功部署
3. 点击 "Redeploy"

---

## 📞 获取帮助

遇到问题？
1. 查看 Railway 日志：Dashboard → 服务 → Deployments → 点击部署查看日志
2. Railway 文档：https://docs.railway.app/
3. Railway Discord：https://discord.gg/railway
