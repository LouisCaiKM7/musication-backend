# 🔧 修复数据库约束错误

## 问题描述
```
CheckViolation: new row for relation "analyses" violates check constraint "analyses_method_check"
method: 'similarity_comparison'
```

**原因：** 生产数据库的约束是旧版本，不包含 `similarity_comparison` 方法。

---

## ✅ 解决方案：在 Render 上更新数据库约束

### 方法 1: 通过 Render Dashboard 执行 SQL（推荐）

#### Step 1: 连接到数据库
1. 登录 Render Dashboard
2. 找到 `musication-db` 数据库
3. 点击 **Connect** 标签
4. 选择 **External Connection** 或 **Internal Connection**
5. 复制连接命令，例如：
   ```bash
   PGPASSWORD=xxxx psql -h dpg-xxxx.oregon-postgres.render.com -U musication musication
   ```

#### Step 2: 在本地终端连接数据库
```bash
# 粘贴 Render 提供的连接命令
PGPASSWORD=your_password psql -h your-host.render.com -U musication musication
```

#### Step 3: 执行更新 SQL
```sql
-- 1. 检查当前约束
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conname = 'analyses_method_check';

-- 2. 删除旧约束
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_method_check;

-- 3. 添加新约束（包含 similarity_comparison）
ALTER TABLE analyses ADD CONSTRAINT analyses_method_check 
CHECK (method IN (
    'chromaprint',
    'hpcp',
    'dtw',
    'lyrics',
    'music_identification',
    'similarity_detection',
    'melody_similarity',
    'cover_detection',
    'similarity_comparison',
    'other'
));

-- 4. 验证约束已更新
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conname = 'analyses_method_check';
```

#### Step 4: 退出并测试
```sql
\q  -- 退出 psql
```

现在重新测试前端比较功能，应该能正常工作。

---

### 方法 2: 通过 Render Shell 执行（需要付费计划）

如果有付费计划，可以使用 Render Shell：

```bash
# 在 Render Dashboard 中
render shell -s musication-backend

# 连接数据库
psql $DATABASE_URL

# 执行上面的 SQL
```

---

### 方法 3: 通过 Web Service 执行（临时解决方案）

如果无法直接连接数据库，可以创建一个临时端点：

#### 在 `app.py` 中添加：
```python
@app.post("/admin/update-constraint")
def update_constraint():
    """临时端点：更新数据库约束"""
    # 仅在开发/调试时使用！
    if settings.flask_env != "production":
        return jsonify({"error": "Not allowed"}), 403
    
    with engine.begin() as conn:
        # 删除旧约束
        conn.execute(text("""
            ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_method_check;
        """))
        
        # 添加新约束
        conn.execute(text("""
            ALTER TABLE analyses ADD CONSTRAINT analyses_method_check 
            CHECK (method IN (
                'chromaprint','hpcp','dtw','lyrics','music_identification',
                'similarity_detection','melody_similarity','cover_detection',
                'similarity_comparison','other'
            ));
        """))
    
    return jsonify({"status": "success", "message": "Constraint updated"})
```

然后访问：
```bash
curl -X POST https://musication-backend-pffy.onrender.com/admin/update-constraint
```

**⚠️ 注意：** 使用后立即删除此端点！

---

## 🔍 验证修复

### 1. 检查约束
```sql
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conname = 'analyses_method_check';
```

预期输出应包含 `similarity_comparison`：
```
analyses_method_check | CHECK (method IN ('chromaprint','hpcp',...,'similarity_comparison','other'))
```

### 2. 测试比较功能
1. 访问前端：https://your-app.netlify.app
2. 点击 **Compare Tracks**
3. 选择两首曲目
4. 点击 **Compare**
5. 应该能看到进度条并完成比较

---

## 🎯 长期解决方案：使用 Alembic 迁移

为避免将来出现类似问题，建议使用 Alembic 管理数据库 schema：

### 初始化 Alembic（在本地）
```bash
cd musication-backend

# 安装 alembic（已在 requirements.txt 中）
pip install alembic

# 初始化
alembic init alembic

# 编辑 alembic.ini，设置数据库 URL
# sqlalchemy.url = postgresql://user:pass@localhost/dbname
```

### 创建迁移
```bash
# 自动生成迁移脚本
alembic revision --autogenerate -m "Add similarity_comparison to method check"

# 应用迁移
alembic upgrade head
```

### 在 Render 上自动运行迁移
在 `render.yaml` 中添加：
```yaml
services:
  - type: web
    name: musication-backend
    buildCommand: "pip install -r requirements.txt && alembic upgrade head"
```

这样每次部署时都会自动更新数据库 schema。

---

## 📋 完成检查表

- [ ] 连接到 Render 数据库
- [ ] 执行约束更新 SQL
- [ ] 验证约束包含 `similarity_comparison`
- [ ] 测试前端比较功能
- [ ] （可选）设置 Alembic 迁移

修复完成后，应该能正常使用音乐比较功能！
