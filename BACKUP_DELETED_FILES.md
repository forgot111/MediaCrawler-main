# 项目精简 - 删除文件备份记录

**删除时间**: 2025-10-04
**精简目标**: 保留抖音数据抓取 + CSV生成 + Web界面展示功能

## 删除的目录和文件清单

### 1. 文档和开发相关
```
docs/.vitepress/               # VitePress文档配置
docs/static/                   # 静态资源
docs/CDP模式使用指南.md
docs/index.md
docs/mediacrawlerpro订阅.md
docs/代理使用.md
docs/作者介绍.md
docs/原生环境管理文档.md
docs/常见问题.md
docs/开发者咨询.md
docs/微信交流群.md
docs/快代理使用文档.md
docs/手机号登录说明.md
docs/捐赠名单.md
docs/知识付费介绍.md
docs/知识星球介绍.md
docs/词云图使用配置.md
docs/豌豆HTTP使用文档.md
docs/项目代码结构.md
node_modules/                  # 前端依赖（VitePress）
.github/                       # GitHub Actions等配置
.idea/                         # PyCharm IDE配置
test/                          # 测试文件
DELETED_FILES_BACKUP_RESTORE.md
```

### 2. 代理功能（未启用）
```
proxy/                         # 整个代理目录
  ├── __init__.py
  ├── base_proxy.py
  ├── proxy_ip_pool.py
  ├── types.py
  └── providers/               # 代理提供商实现
```

### 3. 数据库支持（只用CSV和Web）
```
async_db.py                    # MySQL异步数据库
db.py                          # 数据库初始化
schema/tables.sql              # MySQL表结构
store/douyin/douyin_store_sql.py  # SQL存储实现
```

### 4. 其他存储方式（只保留CSV和Web）
```
store/douyin/douyin_excel_store.py    # Excel存储
store/douyin/douyin_visual_store.py   # 可视化存储
async_sqlite_db.py             # SQLite数据库（如果不用）
schema/sqlite_tables.sql       # SQLite表结构（如果不用）
schema/sqlite_tables.db        # SQLite数据库文件（如果不用）
```

### 5. 词云功能（未启用）
```
tools/words.py                 # 词云生成工具
docs/hit_stopwords.txt         # 停用词文件
docs/STZHONGS.TTF              # 中文字体文件
```

### 6. 媒体下载功能（未启用）
```
store/douyin/douyin_store_media.py  # 媒体文件存储
```

### 7. Redis缓存（只用本地缓存）
```
cache/redis_cache.py           # Redis缓存实现
```

### 8. 不常用工具
```
tools/slider_util.py           # 滑块验证工具
tools/easing.py                # 缓动函数
```

### 9. 命令行参数（使用配置文件）
```
cmd_arg/                       # 命令行参数解析
  ├── __init__.py
  └── arg.py
```

### 10. 其他平台相关（只保留抖音）
```
# 当前项目已经只有douyin平台，无需删除
```

## 保留的核心文件

### 核心功能模块
- `base/` - 基础抽象类
- `config/` - 配置文件
- `media_platform/douyin/` - 抖音爬虫核心
- `store/douyin/` - 数据存储（保留 CSV 和 Web）
- `cache/` - 缓存（保留本地缓存和工厂）
- `tools/` - 核心工具类
- `libs/` - JS库（反检测）
- `constant/` - 常量定义
- `model/` - 数据模型

### 启动脚本
- `main.py` - 主入口
- `start_douyin_complete.py` - 完整自动化流程
- `start_web_auto_port.py` - Web界面启动
- `var.py` - 全局变量

### 配置文件
- `pyproject.toml` - 项目配置
- `requirements.txt` - Python依赖
- `.python-version` - Python版本
- `.gitignore` - Git忽略配置

### 数据目录
- `data/` - 数据存储目录
- `browser_data/` - 浏览器缓存

## 恢复方法

如果需要恢复删除的功能：

1. **恢复代理功能**: 从Git历史恢复 `proxy/` 目录
2. **恢复数据库**: 恢复 `async_db.py`, `db.py`, `schema/`, `store/douyin/douyin_store_sql.py`
3. **恢复词云**: 恢复 `tools/words.py` 和 `docs/` 中的字体、停用词文件
4. **恢复文档**: 恢复 `docs/` 和 `node_modules/`

## Git命令恢复示例

```bash
# 查看删除的文件
git log --diff-filter=D --summary

# 恢复特定文件
git checkout <commit_hash> -- <file_path>

# 恢复整个目录
git checkout <commit_hash> -- proxy/
```

## 配置调整

删除功能后，需要确保配置文件中对应选项已禁用：

```python
# config/base_config.py
ENABLE_IP_PROXY = False          # 代理已删除
ENABLE_GET_WORDCLOUD = False     # 词云已删除
ENABLE_GET_MEIDAS = False        # 媒体下载已删除
SAVE_DATA_OPTION = "csv"         # 或 "web"
```

## 依赖清理

删除功能后可以移除的依赖（可选）：

```
# requirements.txt 中可以考虑移除：
aiomysql==0.2.0              # MySQL支持
redis~=4.6.0                 # Redis缓存
jieba==0.42.1                # 词云分词
wordcloud==1.9.3             # 词云生成
matplotlib==3.9.0            # 词云绘图
seaborn>=0.13.2              # 数据可视化
openpyxl>=3.1.5              # Excel支持
```

**注意**: 建议先测试功能正常后再清理依赖
