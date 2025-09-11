# 🎯 修复CSV文件检测逻辑

## ✅ 问题描述

用户反馈程序检测到的是 `douyin_comments.csv` 文件，但实际应该检测 `7548310409170783498_comments.csv` 文件（按视频ID命名的文件）。

## 🔧 问题分析

**之前的检测逻辑：**
- ❌ 只查找包含 "douyin" 或 "抖音" 关键词的CSV文件
- ❌ 忽略了按视频ID命名的CSV文件格式
- ❌ 导致检测到错误的CSV文件

**实际文件命名规则：**
- ✅ 按视频ID命名：`{视频ID}_comments.csv`
- ✅ 例如：`7548310409170783498_comments.csv`

## 📝 修复详情

### 优化后的 `_find_latest_csv_in_desktop` 方法：

```python
def _find_latest_csv_in_desktop(self) -> str:
    """在桌面查找最新的CSV文件"""
    try:
        import glob
        
        # 在D盘桌面查找CSV文件
        desktop_paths = ["D:/桌面", "D:/Desktop", os.path.expanduser("~/Desktop")]
        
        for desktop_path in desktop_paths:
            if os.path.exists(desktop_path):
                # 查找所有CSV文件
                csv_files = glob.glob(os.path.join(desktop_path, "*.csv"))
                
                # 【新增】优先查找按视频ID命名的CSV文件
                video_id_csv_files = []
                for csv_file in csv_files:
                    filename = os.path.basename(csv_file)
                    # 检查是否以数字开头并以_comments.csv结尾（视频ID格式）
                    if filename[0].isdigit() and filename.endswith('_comments.csv'):
                        video_id_csv_files.append(csv_file)
                
                if video_id_csv_files:
                    # 返回最新的视频ID CSV文件
                    latest_csv = max(video_id_csv_files, key=lambda f: os.path.getmtime(f))
                    utils.logger.info(f"找到最新视频ID CSV文件: {latest_csv}")
                    return latest_csv
                
                # 如果没找到视频ID格式的，再查找抖音相关的CSV文件
                douyin_csv_files = [f for f in csv_files if '抖音' in os.path.basename(f) or 'douyin' in os.path.basename(f).lower()]
                
                if douyin_csv_files:
                    latest_csv = max(douyin_csv_files, key=lambda f: os.path.getmtime(f))
                    utils.logger.info(f"找到最新抖音CSV文件: {latest_csv}")
                    return latest_csv
                elif csv_files:
                    # 最后返回最新的任意CSV文件
                    latest_csv = max(csv_files, key=lambda f: os.path.getmtime(f))
                    utils.logger.info(f"找到最新CSV文件: {latest_csv}")
                    return latest_csv
```

### 🚀 检测优先级

现在的检测逻辑按以下优先级进行：

1. **🎯 最高优先级**：按视频ID命名的文件
   - 格式：`数字开头_comments.csv`
   - 例如：`7548310409170783498_comments.csv`

2. **🔍 中等优先级**：包含抖音关键词的文件
   - 格式：包含 "抖音" 或 "douyin" 的文件
   - 例如：`douyin_comments.csv`

3. **📋 最低优先级**：任意CSV文件
   - 格式：任何 `.csv` 文件

### 💡 关键改进

1. **🎯 精确识别视频ID格式**
   - 检查文件名是否以数字开头
   - 检查文件名是否以 `_comments.csv` 结尾

2. **📊 按修改时间排序**
   - 在同类文件中选择最新的文件
   - 确保获取最近生成的CSV

3. **🔄 多层级fallback机制**
   - 优先视频ID格式 → 抖音关键词 → 任意CSV
   - 确保总能找到合适的文件

### 🎉 预期效果

现在程序会：
- ✅ **正确识别 `7548310409170783498_comments.csv` 文件**
- ✅ **优先选择按视频ID命名的CSV文件**
- ✅ **准确导入正确的评论数据到Web界面**
- ✅ **避免导入错误的CSV文件**

## 🎯 总结

修复后，程序会优先检测按视频ID命名的CSV文件（如 `7548310409170783498_comments.csv`），而不是通用的 `douyin_comments.csv` 文件，确保导入正确的评论数据！🎊