# 已删除文件备份记录 - 恢复版

**删除时间**: 2025-09-30  
**删除原因**: 精简项目，只保留抖音核心功能  
**核心功能**: `start_douyin_complete.py` 和 `start_web_auto_port.py`

## 🗑️ 需要删除的文件和目录

### 1. 其他平台目录
- `media_platform/bilibili/` - B站平台
- `media_platform/kuaishou/` - 快手平台  
- `media_platform/xhs/` - 小红书平台
- `media_platform/weibo/` - 微博平台
- `media_platform/zhihu/` - 知乎平台
- `media_platform/tieba/` - 贴吧平台

### 2. 其他平台存储
- `store/bilibili/` - B站存储
- `store/kuaishou/` - 快手存储
- `store/xhs/` - 小红书存储
- `store/weibo/` - 微博存储
- `store/zhihu/` - 知乎存储
- `store/tieba/` - 贴吧存储

### 3. 其他平台配置
- `config/bilibili_config.py` - B站配置
- `config/ks_config.py` - 快手配置
- `config/xhs_config.py` - 小红书配置
- `config/weibo_config.py` - 微博配置
- `config/zhihu_config.py` - 知乎配置
- `config/tieba_config.py` - 贴吧配置

### 4. 其他平台数据模型
- `model/m_kuaishou.py` - 快手模型
- `model/m_xiaohongshu.py` - 小红书模型
- `model/m_weibo.py` - 微博模型
- `model/m_zhihu.py` - 知乎模型
- `model/m_baidu_tieba.py` - 贴吧模型
- `model/m_douyin.py` - 抖音模型（不需要）

### 5. 常量定义
- `constant/baidu_tieba.py` - 贴吧常量
- `constant/zhihu.py` - 知乎常量

### 6. JS库文件
- `libs/zhihu.js` - 知乎JS库

### 7. 不必要的测试和工具文件
- `manual_start_web.py` - 手动启动Web（已有自动版本）
- `test_*.py` (除了基础测试) - 各种测试文件
- `recv_sms.py` - 短信接收
- `start_image_web.py` - 图片Web启动
- `start_web_monitor.py` - Web监控启动
- `update_stats.py` - 统计更新
- `fix_stats.py` - 修复统计
- `test_author_liked.py` - 作者点赞测试
- `test_comment_images.py` - 评论图片测试
- `test_data_import.py` - 数据导入测试
- `test_reply_logic.py` - 回复逻辑测试
- `test_8083.py` - 端口测试
- `test_api.py` - API测试

### 8. 说明文档（非核心）
- `CSV数据导入与Web监控使用指南.md`
- `Web三列布局优化说明.md`
- `Web界面增强功能说明.md`
- `Web界面新增功能说明.md`
- `Web评论排序优化说明.md`
- `二级评论逻辑修正说明.md`
- `作者已赞功能说明.md`
- `修复CSV文件检测逻辑说明.md`
- `常见问题解答.md`
- `持续监控说明.md`
- `数据可视化使用指南.md`
- `简化评论抓取流程说明.md`
- `评论图片功能实现总结.md`
- `评论图片显示功能说明.md`
- `评论抓取流程改进说明.md`
- `README_en.md`
- `README_es.md`

### 9. 辅助脚本
- `start_web.bat`
- `start_web.ps1`
- `启动助手.bat`

### 10. 其他配置和环境文件
- `package.json`
- `package-lock.json`
- `web_enhancement.js`

## 🔄 恢复方法

如果需要恢复这些文件，请执行：
```bash
git checkout HEAD -- [文件路径]
```

## ⚠️ 注意事项

删除这些文件后，只能运行抖音相关功能：
- ✅ `start_douyin_complete.py` - 抖音完整抓取
- ✅ `start_web_auto_port.py` - Web监控界面