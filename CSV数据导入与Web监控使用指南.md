# CSV数据导入与Web监控功能使用指南

## 🎯 功能概述

本功能可以：
1. **导入CSV数据到Web监控界面**：将已有的CSV评论数据导入到实时Web可视化界面
2. **持续监控新评论**：在导入完成后，自动开始监控新产生的评论
3. **在8081端口提供Web服务**：提供实时数据可视化界面

## 🚀 使用方法

### 方法1：完整流程（推荐）

```bash
# 使用默认命令，程序会自动：
# 1. 抓取评论并保存到CSV（D盘桌面）
# 2. 将CSV数据导入Web监控界面
# 3. 启动8081端口Web服务
# 4. 开始持续监控新评论
uv run main.py --platform dy --lt qrcode --type detail
```

**这条命令就是您要求的完整功能！**

### 方法2：直接使用Web模式

```bash
# 直接使用web存储模式
uv run main.py --platform dy --lt qrcode --type detail --save_data_option web
```

### 方法3：手动导入现有CSV数据

如果您已经有CSV数据文件，可以直接导入：

```bash
# 自动查找最新的CSV文件并导入
uv run python tools/csv_importer.py --platform douyin --auto

# 或指定具体的CSV文件路径
uv run python tools/csv_importer.py --platform douyin --csv "D:/桌面/your_comments.csv"
```

### 方法4：在配置文件中设置

修改 `config/base_config.py` 文件：

```python
# 设置数据保存选项为web模式
SAVE_DATA_OPTION = "web"  # csv or db or json or sqlite or visual or excel or web
```

然后运行：
```bash
uv run main.py --platform dy --lt qrcode --type detail
```

## 📊 工作流程

### 完整流程（推荐）
1. **第一阶段**：程序抓取所有现有评论和二级评论
2. **第二阶段**：将抓取的数据自动导入到Web可视化界面
3. **第三阶段**：启动Web服务器（http://localhost:8081）
4. **第四阶段**：开始持续监控新评论（每60秒检测一次）

### 手动导入流程
1. **准备CSV文件**：确保有抖音评论的CSV数据文件
2. **运行导入工具**：使用csv_importer.py导入数据
3. **访问Web界面**：浏览器打开 http://localhost:8081
4. **保持运行**：程序会持续运行Web服务器

## 🌐 Web界面功能

访问 http://localhost:8081 可以看到：

### 实时统计卡片
- 💬 总评论数
- 👥 参与用户数
- 👍 总点赞数
- 📊 平均点赞数
- 💬 回复比例
- ❤️ 作者点赞数

### 数据可视化图表
- 📊 评论时间分布（柱状图）
- 🥧 点赞数分布（环形图）
- 😊 情感分析（饼图）
- 🗺️ 地理位置分布

### 交互功能
- 🔄 实时数据刷新
- 📥 导出CSV/Excel数据  
- 📋 最新评论列表
- 👥 活跃用户排行
- 🌍 地区分布统计
- ☁️ 评论词云图

## ⚙️ 配置选项

### 基础配置
```python
# config/base_config.py

# 数据保存类型（选择web启用Web监控）
SAVE_DATA_OPTION = "web"

# 评论抓取间隔时间（秒）
COMMENT_CRAWL_INTERVAL = 0.5

# 批量处理大小
BATCH_COMMENT_SIZE = 50

# 是否启用评论抓取
ENABLE_GET_COMMENTS = True

# 是否启用二级评论抓取
ENABLE_GET_SUB_COMMENTS = True

# 单个视频最大评论数
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 4000
```

### Web服务器配置
Web服务器默认使用8081端口，如果端口被占用会自动尝试8082端口。

可以在 `store/douyin/douyin_web_store.py` 中修改：
```python
# 修改端口号
port = 8081  # 改为您想要的端口
```

## 📝 监控日志说明

### 正常监控日志
```
[DouYinCrawler.monitor_new_comments] 开始持续监控新评论，按 Ctrl+C 停止监控
[DouYinCrawler.monitor_new_comments] 检测视频 7547277273242553609 的新评论...
[DouYinCrawler.monitor_new_comments] 视频 7547277273242553609 发现 3 条新评论
[DouYinCrawler.monitor_new_comments] 等待60秒后进行下一轮检测...
```

### 无新评论日志
```
[DouYinCrawler.monitor_new_comments] 视频 7547277273242553609 暂无新评论
```

### CSV导入日志
```
[CSVImporter] 成功读取 1250 条评论数据
[CSVImporter] 开始批量导入评论数据到Web界面...
[CSVImporter] CSV数据导入完成!
```

## 🛠️ 故障排除

### 常见问题

1. **端口被占用**
   ```
   [DouyinWebStore] 端口8081被占用，尝试使用端口8082
   ```
   - 解决方案：程序会自动尝试其他端口，或手动修改配置

2. **CSV文件未找到**
   ```
   [CSVImporter] 未找到CSV文件
   ```
   - 解决方案：确保先运行过csv模式的抓取，或手动指定CSV文件路径

3. **Web服务器启动失败**
   ```
   [DouyinWebStore] Web服务器启动失败
   ```
   - 解决方案：检查端口是否被占用，确保有足够权限

4. **评论数据为空**
   ```
   [DouYinCrawler.monitor_new_comments] 视频获取评论失败或返回空列表
   ```
   - 解决方案：检查网络连接，确认视频ID正确

### 手动停止监控
按 `Ctrl+C` 停止持续监控和Web服务器。

### 重新启动服务
如果Web服务意外停止，重新运行程序即可恢复服务。

## 💡 使用建议

### 推荐使用场景
1. **数据收集 + 实时监控**：先收集历史数据，再监控新数据
2. **数据可视化分析**：通过Web界面直观查看数据趋势
3. **长期监控项目**：持续跟踪特定视频的评论变化

### 性能优化建议
1. **大量数据**：建议先用csv模式收集，再导入web界面
2. **网络优化**：配置合适的爬取间隔，避免被限制
3. **资源监控**：长时间运行时注意内存使用情况

### 最佳实践
1. **先抓取再监控**：建议先完整抓取一遍数据，再开启持续监控
2. **定期备份**：定期导出CSV/Excel数据进行备份
3. **合理间隔**：监控间隔不宜过短，避免对平台造成压力

## 🎉 开始使用

现在您可以享受集数据抓取、可视化分析和实时监控于一体的强大功能了！

```bash
# 一键启动完整功能
uv run main.py --platform dy --lt qrcode --type detail --save_data_option web
```

程序启动后会自动：
1. ✅ 抓取所有评论数据
2. ✅ 导入数据到Web界面  
3. ✅ 启动8081端口Web服务
4. ✅ 开始持续监控新评论
5. ✅ 自动打开浏览器查看界面

**快来体验吧！** 🚀