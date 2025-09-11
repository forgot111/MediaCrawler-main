// 完整的JavaScript功能补充
// 用于Web界面的翻页和作者赞过评论功能

// 全局变量
let currentCommentsPage = 1;
let currentAuthorLikedPage = 1;

// 加载分页评论数据
async function loadCommentsPage(page = 1) {
    try {
        document.getElementById('status').innerHTML = '<div class="loading"></div> 正在加载评论...';
        
        const response = await fetch(`/api/comments?page=${page}`);
        const data = await response.json();
        
        currentCommentsPage = page;
        updateCommentsList(data.comments);
        updatePagination('comments-pagination', data.pagination, 'loadCommentsPage');
        
        document.getElementById('status').textContent = `显示第 ${page} 页评论，共 ${data.pagination.total} 条`;
        
    } catch (error) {
        document.getElementById('status').textContent = '评论加载失败';
        console.error('Error loading comments:', error);
    }
}

// 加载作者赞过的评论数据
async function loadAuthorLikedPage(page = 1) {
    try {
        document.getElementById('author-liked-status').innerHTML = '<div class="loading"></div> 正在加载作者赞过的评论...';
        
        const response = await fetch(`/api/author-liked?page=${page}`);
        const data = await response.json();
        
        currentAuthorLikedPage = page;
        updateAuthorLikedList(data.comments);
        updatePagination('author-liked-pagination', data.pagination, 'loadAuthorLikedPage');
        
        document.getElementById('author-liked-status').textContent = `显示第 ${page} 页，共 ${data.pagination.total} 条作者赞过的评论`;
        
    } catch (error) {
        document.getElementById('author-liked-status').textContent = '作者赞过的评论加载失败';
        console.error('Error loading author liked comments:', error);
    }
}

// 更新分页控件
function updatePagination(containerId, pagination, callbackFunction) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    if (pagination.total === 0) {
        container.innerHTML = '<div class="pagination-info">暂无数据</div>';
        return;
    }
    
    // 上一页按钮
    const prevBtn = document.createElement('button');
    prevBtn.className = 'pagination-btn';
    prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
    prevBtn.disabled = !pagination.has_prev;
    prevBtn.onclick = () => {
        if (pagination.has_prev) {
            window[callbackFunction](pagination.page - 1);
        }
    };
    container.appendChild(prevBtn);
    
    // 页码按钮
    const startPage = Math.max(1, pagination.page - 2);
    const endPage = Math.min(pagination.total_pages, pagination.page + 2);
    
    // 第一页
    if (startPage > 1) {
        const firstBtn = document.createElement('button');
        firstBtn.className = 'pagination-btn';
        firstBtn.textContent = '1';
        firstBtn.onclick = () => window[callbackFunction](1);
        container.appendChild(firstBtn);
        
        if (startPage > 2) {
            const ellipsis = document.createElement('span');
            ellipsis.className = 'pagination-info';
            ellipsis.textContent = '...';
            container.appendChild(ellipsis);
        }
    }
    
    // 当前页面附近的页码
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = `pagination-btn ${i === pagination.page ? 'active' : ''}`;
        pageBtn.textContent = i;
        pageBtn.onclick = () => window[callbackFunction](i);
        container.appendChild(pageBtn);
    }
    
    // 最后一页
    if (endPage < pagination.total_pages) {
        if (endPage < pagination.total_pages - 1) {
            const ellipsis = document.createElement('span');
            ellipsis.className = 'pagination-info';
            ellipsis.textContent = '...';
            container.appendChild(ellipsis);
        }
        
        const lastBtn = document.createElement('button');
        lastBtn.className = 'pagination-btn';
        lastBtn.textContent = pagination.total_pages;
        lastBtn.onclick = () => window[callbackFunction](pagination.total_pages);
        container.appendChild(lastBtn);
    }
    
    // 下一页按钮
    const nextBtn = document.createElement('button');
    nextBtn.className = 'pagination-btn';
    nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
    nextBtn.disabled = !pagination.has_next;
    nextBtn.onclick = () => {
        if (pagination.has_next) {
            window[callbackFunction](pagination.page + 1);
        }
    };
    container.appendChild(nextBtn);
    
    // 页面信息
    const pageInfo = document.createElement('div');
    pageInfo.className = 'pagination-info';
    pageInfo.textContent = `第 ${pagination.page}/${pagination.total_pages} 页，共 ${pagination.total} 条`;
    container.appendChild(pageInfo);
}

// 更新作者赞过的评论列表
function updateAuthorLikedList(comments) {
    const authorLikedList = document.getElementById('author-liked-list');
    authorLikedList.innerHTML = '';
    
    if (!comments || comments.length === 0) {
        authorLikedList.innerHTML = '<div class="status">暂无作者赞过的评论</div>';
        return;
    }
    
    comments.forEach(comment => {
        const commentDiv = document.createElement('div');
        commentDiv.className = 'comment-item';
        
        const userDiv = document.createElement('div');
        userDiv.className = 'comment-user';
        userDiv.innerHTML = `<i class="fas fa-user"></i> ${comment['用户昵称'] || '匿名用户'}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'comment-content';
        contentDiv.textContent = comment['评论内容'] || '';
        
        const metaDiv = document.createElement('div');
        metaDiv.className = 'comment-meta';
        
        const timeItem = document.createElement('div');
        timeItem.className = 'meta-item';
        timeItem.innerHTML = `<i class="fas fa-clock"></i> ${comment['评论时间'] || ''}`;
        
        const likesItem = document.createElement('div');
        likesItem.className = 'meta-item';
        likesItem.innerHTML = `<i class="fas fa-heart"></i> ${comment['点赞数'] || 0}`;
        
        const authorLikedItem = document.createElement('div');
        authorLikedItem.className = 'meta-item';
        authorLikedItem.innerHTML = `<i class="fas fa-star" style="color: #ffc107;"></i> 作者已赞`;
        
        const locationItem = document.createElement('div');
        locationItem.className = 'meta-item';
        if (comment['ip归属']) {
            locationItem.innerHTML = `<i class="fas fa-map-marker-alt"></i> ${comment['ip归属']}`;
        }
        
        metaDiv.appendChild(timeItem);
        metaDiv.appendChild(likesItem);
        metaDiv.appendChild(authorLikedItem);
        if (comment['ip归属']) {
            metaDiv.appendChild(locationItem);
        }
        
        // 如果是回复评论，显示被回复人
        if (comment['被回复人昵称']) {
            const replyItem = document.createElement('div');
            replyItem.className = 'meta-item';
            replyItem.innerHTML = `<i class="fas fa-reply"></i> 回复 @${comment['被回复人昵称']}`;
            metaDiv.appendChild(replyItem);
        }
        
        commentDiv.appendChild(userDiv);
        commentDiv.appendChild(contentDiv);
        commentDiv.appendChild(metaDiv);
        
        authorLikedList.appendChild(commentDiv);
    });
}

// 标签页切换功能（更新版本）
function switchTab(tabName) {
    // 隐藏所有标签内容
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // 移除所有标签的激活状态
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // 激活选中的标签
    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // 根据标签类型加载相应数据
    if (tabName === 'comments') {
        loadCommentsPage(currentCommentsPage);
    } else if (tabName === 'author-liked') {
        loadAuthorLikedPage(currentAuthorLikedPage);
    } else if (tabName === 'users') {
        if (currentData) {
            updateUsersList(currentData.analytics.top_users || []);
        }
    } else if (tabName === 'locations') {
        if (currentData) {
            updateLocationsList(currentData.analytics.location_distribution || {});
        }
    }
}

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    loadData();
    
    // 设置定时刷新
    setInterval(loadData, 30000); // 每30秒刷新一次数据
});

// 导出功能
function exportData(type) {
    const link = document.createElement('a');
    link.href = `/export/${type}`;
    link.download = `douyin_comments.${type}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

console.log('Web功能增强脚本已加载：翻页功能和作者赞过的评论功能');