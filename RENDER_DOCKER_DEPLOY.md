# 🐳 Render Docker 部署指南（支持音乐识别）

因为音乐识别功能需要 `chromaprint` 系统库，所以必须使用 Docker 部署。

## 📋 前提条件

1. GitHub 账号
2. Render 账号（https://render.com）
3. 代码已推送到 GitHub

---

## 步骤 1: 创建 PostgreSQL 数据库

1. 登录 Render Dashboard
2. 点击 **New +** → **PostgreSQL**
3. 配置：
   - **Name**: `musication-db`
   - **Database**: `musication`
   - **Region**: 选择离你最近的
   - **Plan**: **Free**
4. 点击 **Create Database**
5. 等待 1-2 分钟直到状态变为 Available
6. **重要**: 复制 **Internal Database URL**（格式：`postgresql://...`）

---

## 步骤 2: 部署后端（Docker）

1. 进入 Render Dashboard
2. 点击 **New +** → **Web Service**
3. 连接你的 GitHub 仓库
4. 配置如下：

### 基本设置
- **Name**: `musication-backend`（或自定义）
- **Region**: 与数据库相同
- **Branch**: `main`
- **Root Directory**: `musication-backend`（如果后端在子文件夹）
- **Environment**: **Docker**
- **Plan**: **Free**

### 不需要填写 Build/Start Command
Docker 会自动使用 Dockerfile 中的命令

### 环境变量（Environment Variables）

点击 **Advanced**，添加以下环境变量：

| Key | Value | 说明 |
|-----|-------|------|
| `FLASK_ENV` | `production` | Flask 环境 |
| `DATABASE_URL` | `<粘贴步骤1的URL>` | 数据库连接 |
| `BASE_URL` | `https://你的服务名.onrender.com` | 后端URL（第一次可留空） |
| `FRONTEND_URL` | `https://你的前端.netlify.app` | 前端URL（稍后更新） |
| `UPLOAD_DIR` | `uploads` | 上传目录 |
| `FPCALC` | `/usr/bin/fpcalc` | fpcalc 路径（Docker已设置） |

**注意**：
- `BASE_URL` 第一次部署前可能不知道完整URL，可以先留空，部署后再更新
- `FRONTEND_URL` 等前端部署好后再填写

5. 点击 **Create Web Service**
6. 等待 5-10 分钟（Docker 构建需要更长时间）
7. 部署成功后，记录你的服务URL（例如：`https://musication-backend.onrender.com`）

### 更新 BASE_URL

1. 部署成功后，进入服务的 **Environment** 标签
2. 更新 `BASE_URL` 为实际的 Render URL
3. 保存后会自动重新部署

---

## 步骤 3: 测试后端

访问健康检查端点：
```
https://你的后端.onrender.com/health
```

应该返回：
```json
{
  "status": "ok"
}
```

测试音乐识别（上传音乐后点击 ✨ 按钮）

---

## 步骤 4: 部署前端到 Netlify

### 4.1 推送代码到 GitHub

确保前端代码已推送到 GitHub

### 4.2 连接 Netlify

1. 登录 Netlify
2. 点击 **Add new site** → **Import an existing project**
3. 选择 GitHub，授权并选择你的仓库
4. 配置：
   - **Base directory**: 留空（如果前端在根目录）
   - **Build command**: `npm run build`
   - **Publish directory**: `.next`
5. 添加环境变量：
   - **Key**: `NEXT_PUBLIC_API_URL`
   - **Value**: `https://你的后端.onrender.com`

### 4.3 部署

点击 **Deploy site**，等待 2-3 分钟

### 4.4 更新后端 CORS

1. 回到 Render → 后端服务 → Environment
2. 更新 `FRONTEND_URL` 为你的 Netlify URL
3. 保存（会自动重新部署）

---

## ✅ 验证部署

1. **后端健康检查**：访问 `/health` 端点
2. **上传音乐**：在前端上传 MP3 文件
3. **识别音乐**：点击 ✨ 按钮测试音乐识别
4. **查看结果**：应该能看到匹配结果或"No matches found"

---

## ⚠️ 重要注意事项

### 文件存储限制
- Render 免费版使用**临时文件系统**
- 服务重启时上传的音乐会丢失（~15天或重新部署时）
- **解决方案**：
  - 测试用：接受文件丢失
  - 生产用：集成 S3/Cloudflare R2/Supabase Storage

### 数据库持久化
- ✅ PostgreSQL 数据永久保存（即使在免费版）

### Cold Start（冷启动）
- 免费版闲置 15 分钟后会休眠
- 首次访问需要 30-60 秒唤醒
- 升级到 $7/月可获得 24/7 在线

### Docker 构建时间
- 首次部署需要 5-10 分钟
- 后续部署会使用缓存，更快

---

## 🔧 故障排查

### "Build failed" 错误
- 检查 Dockerfile 语法
- 确认 `requirements.txt` 存在
- 查看 Render 构建日志

### 数据库连接错误
- 确认 `DATABASE_URL` 格式正确
- 使用 **Internal Database URL**，不是 External
- 检查数据库状态为 Available

### CORS 错误
- 确认 `FRONTEND_URL` 与 Netlify URL 完全匹配
- 检查没有多余的斜杠
- 查看浏览器控制台和后端日志

### 音乐识别失败
- 检查日志中是否有 fpcalc 相关错误
- 确认 Docker 镜像包含 chromaprint
- 验证环境变量 `FPCALC=/usr/bin/fpcalc` 已设置

---

## 📊 生产环境清单

- [ ] 后端部署成功（Docker）
- [ ] PostgreSQL 创建并连接
- [ ] 所有环境变量已设置
- [ ] `/health` 返回 200
- [ ] 前端部署到 Netlify
- [ ] 前端可以连接后端（无 CORS 错误）
- [ ] 上传功能正常
- [ ] 音乐识别功能正常（✨ 按钮）
- [ ] 删除功能正常

---

## 🚀 可选优化

1. **自定义域名**（Netlify + Render 都支持）
2. **集成云存储**（S3/R2）存储音频文件
3. **设置 Alembic 迁移**管理数据库结构变更
4. **添加监控**（Sentry、LogRocket）
5. **升级付费版**获得更好性能（$7/月起）

---

## 需要帮助？

- Render 文档：https://render.com/docs
- Netlify 文档：https://docs.netlify.com
- 检查日志：Render Dashboard → 你的服务 → Logs
