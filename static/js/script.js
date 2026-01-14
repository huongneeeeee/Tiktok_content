document.addEventListener("DOMContentLoaded", function() {
    // Tự động chọn tab dựa trên dữ liệu server trả về
    const mainContainer = document.getElementById('main-container');
    const targetTab = mainContainer.dataset.initialTab || 'process';
    switchTab(targetTab);
});

function switchTab(tabName) {
    const processTab = document.getElementById('tab-process');
    const searchTab = document.getElementById('tab-search');
    const btnProcess = document.getElementById('btn-process');
    const btnSearch = document.getElementById('btn-search');

    if (tabName === 'search') {
        processTab.classList.add('hidden');
        searchTab.classList.remove('hidden');
        
        btnSearch.className = "px-6 py-2.5 rounded-lg text-sm font-semibold transition-all flex items-center bg-indigo-600 text-white shadow-md";
        btnProcess.className = "px-6 py-2.5 rounded-lg text-sm font-semibold transition-all flex items-center text-slate-400 hover:text-white";
    } else {
        processTab.classList.remove('hidden');
        searchTab.classList.add('hidden');
        
        btnProcess.className = "px-6 py-2.5 rounded-lg text-sm font-semibold transition-all flex items-center bg-indigo-600 text-white shadow-md";
        btnSearch.className = "px-6 py-2.5 rounded-lg text-sm font-semibold transition-all flex items-center text-slate-400 hover:text-white";
    }
}

function showLoading() {
    document.getElementById('loadingOverlay').classList.remove('hidden');
}

async function confirmReset() {
    if (confirm("⚠️ CẢNH BÁO: Hành động này sẽ xóa toàn bộ dữ liệu database. Bạn có chắc không?")) {
        const btn = document.getElementById('btn-reset');
        if(btn) {
             btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Đang xóa...';
             btn.disabled = true;
        }
        
        try {
            await fetch('/api/reset-system', { method: 'POST' });
            window.location.href = "/";
        } catch (e) {
            alert("Lỗi: " + e);
            if(btn) {
                btn.innerHTML = 'RESET SYSTEM';
                btn.disabled = false;
            }
        }
    }
}

function copyToNotion() {
    // Lấy dữ liệu an toàn hơn bằng ID
    const titleEl = document.getElementById('video-title');
    const summaryEl = document.getElementById('ai-summary-box');
    
    if (!titleEl || !summaryEl) {
        alert("Không tìm thấy nội dung để copy!");
        return;
    }

    const title = titleEl.innerText;
    const summary = summaryEl.innerText; // Lấy cả tiêu đề "Tóm tắt" bên trong
    const link = window.location.href;
    
    // Format Markdown Notion
    const notionText = `
# ${title}
> ${summary.replace(/\n/g, ' ')}

**Nguồn:** [Link TikVault](${link})

---
## Nội dung chi tiết
(Paste nội dung transcript hoặc các bước vào đây)
    `;

    navigator.clipboard.writeText(notionText).then(() => {
        alert("✅ Đã copy! Hãy mở Notion và bấm Ctrl+V.");
    }).catch(err => {
        alert("Lỗi copy: " + err);
    });
}