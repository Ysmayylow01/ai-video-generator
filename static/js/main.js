// static/js/main.js - DOLY WERSIÝA DIL GOLDAWY BILEN

let currentTaskId = null;
let currentVideoUrl = null;
let checkInterval = null;
let failedAttempts = 0;
const MAX_FAILED_ATTEMPTS = 3;

// =========================
// LANGUAGE FUNCTIONS
// =========================

// Update all translatable elements on the page
function updatePageLanguage() {
    const currentLang = getCurrentLanguage();
    
    console.log('Updating language to:', currentLang);
    
    // Update HTML lang attribute
    document.getElementById('html-root').setAttribute('lang', currentLang);
    
    // Update all elements with data-i18n attribute (text content)
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        const translation = t(key);
        if (translation && translation !== key) {
            element.textContent = translation;
        }
    });
    
    // Update all placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        const translation = t(key);
        if (translation && translation !== key) {
            element.placeholder = translation;
        }
    });
    
    // Update select options
    document.querySelectorAll('select option[data-i18n]').forEach(option => {
        const key = option.getAttribute('data-i18n');
        const translation = t(key);
        if (translation && translation !== key) {
            option.textContent = translation;
        }
    });
    
    // Update language buttons
    updateLanguageButtons(currentLang);
    
    console.log('Language updated successfully');
}

// Update language button states
function updateLanguageButtons(lang) {
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeBtn = document.getElementById(`lang-${lang}`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
}

// Switch language
function switchLanguage(lang) {
    console.log('Switching language to:', lang);
    
    if (lang !== 'tk' && lang !== 'en') {
        console.error('Invalid language:', lang);
        return;
    }
    
    setLanguage(lang);
    updatePageLanguage();
    
    // Show notification
    const message = lang === 'tk' ? 'Dil üýtgedildi: Türkmen' : 'Language changed: English';
    showNotification(message, 'success');
}

// =========================
// INITIALIZATION
// =========================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Page loaded, initializing...');
    
    // Initialize language first
    updatePageLanguage();
    
    // Then initialize other components
    initializeForm();
    loadHistory();
    smoothScroll();
});

// =========================
// SMOOTH SCROLL
// =========================

function smoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

function scrollToGenerator() {
    document.getElementById('generator').scrollIntoView({ behavior: 'smooth' });
}

// =========================
// FORM HANDLING
// =========================

function initializeForm() {
    const form = document.getElementById('videoForm');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        await generateVideo();
    });
}

async function generateVideo() {
    console.log('=== GENERATE VIDEO START ===');
    
    const prompt = document.getElementById('prompt').value;
    const imageUrl = document.getElementById('imageUrl').value || null;
    const duration = parseInt(document.getElementById('duration').value);
    const resolution = document.getElementById('resolution').value;
    const aspectRatio = document.getElementById('aspectRatio').value;
    const seed = document.getElementById('seed').value || null;
    
    console.log('Form values:', {
        prompt,
        imageUrl,
        duration,
        resolution,
        aspectRatio,
        seed
    });
    
    if (!prompt) {
        console.error('Prompt empty!');
        showNotification(t('prompt_required'), 'error');
        return;
    }
    
    const generateBtn = document.getElementById('generateBtn');
    const originalContent = generateBtn.innerHTML;
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Işlenýär...';
    
    try {
        const payload = {
            prompt: prompt,
            duration: duration,
            resolution: resolution,
            aspect_ratio: aspectRatio
        };
        
        if (imageUrl) {
            payload.image_url = imageUrl;
        }
        if (seed) {
            payload.seed = parseInt(seed);
        }
        
        console.log('Payload to send:', JSON.stringify(payload, null, 2));
        
        console.log('Sending POST to /generate...');
        const response = await fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        console.log('Response status:', response.status);
        console.log('Response OK:', response.ok);
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.success) {
            console.log('✅ Success! Task ID:', data.task_id);
            currentTaskId = data.task_id;
            failedAttempts = 0;
            showProgress();
            startStatusCheck();
            showNotification(t('video_creating'), 'success');
        } else {
            console.error('❌ API returned success=false');
            throw new Error(data.error || t('error'));
        }
    } catch (error) {
        console.error('❌ Error caught:', error);
        console.error('Error name:', error.name);
        console.error('Error message:', error.message);
        console.error('Error stack:', error.stack);
        showNotification(t('error') + ': ' + error.message, 'error');
        resetGenerator();
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = originalContent;
    }
    
    console.log('=== GENERATE VIDEO END ===');
}
// =========================
// PROGRESS HANDLING
// =========================

function showProgress() {
    document.getElementById('previewArea').style.display = 'none';
    document.getElementById('videoPlayer').style.display = 'none';
    document.getElementById('progressArea').style.display = 'block';
    
    const circle = document.querySelector('.progress-ring-circle');
    const radius = circle.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;
    
    circle.style.strokeDasharray = `${circumference} ${circumference}`;
    circle.style.strokeDashoffset = circumference;
}

function updateProgress(percent, statusText) {
    const circle = document.querySelector('.progress-ring-circle');
    const radius = circle.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (percent / 100 * circumference);
    
    circle.style.strokeDashoffset = offset;
    document.getElementById('progressPercent').textContent = Math.round(percent) + '%';
    document.getElementById('progressStatus').textContent = statusText;
}

// =========================
// STATUS CHECK
// =========================

function startStatusCheck() {
    let attempts = 0;
    const maxAttempts = 180;
    
    updateProgress(10, t('starting'));
    
    checkInterval = setInterval(async () => {
        attempts++;
        let simulatedProgress = 10 + (attempts / maxAttempts * 85);
        if (simulatedProgress > 95) simulatedProgress = 95;
        
        try {
            console.log(`Status check attempt ${attempts}`);
            
            const response = await fetch(`/status/${currentTaskId}`);
            
            if (!response.ok) {
                failedAttempts++;
                console.error(`Status check failed: ${response.status}`);
                
                if (failedAttempts >= MAX_FAILED_ATTEMPTS) {
                    clearInterval(checkInterval);
                    showNotification(t('status_check_failed'), 'error');
                    resetGenerator();
                    return;
                }
                updateProgress(simulatedProgress, t('processing') + '...');
                return;
            }
            
            const data = await response.json();
            console.log('Status data:', data);
            
            if (!data.success) {
                failedAttempts++;
                if (failedAttempts >= MAX_FAILED_ATTEMPTS) {
                    clearInterval(checkInterval);
                    showNotification(data.error || t('error'), 'error');
                    resetGenerator();
                    return;
                }
                updateProgress(simulatedProgress, t('processing') + '...');
                return;
            }
            
            failedAttempts = 0;
            
            if (data.status === 'completed') {
                console.log('✅ Task completed!');
                
                if (!data.video_url) {
                    console.error('No video URL in response!');
                    clearInterval(checkInterval);
                    showNotification(t('error'), 'error');
                    resetGenerator();
                    return;
                }
                
                clearInterval(checkInterval);
                updateProgress(100, t('video_ready'));
                currentVideoUrl = data.video_url;
                
                console.log('Video URL:', currentVideoUrl);
                
                setTimeout(() => {
                    showVideo(data.video_url, currentTaskId);
                    showNotification(t('video_ready_notif'), 'success');
                    loadHistory();
                }, 1000);
                
            } else if (data.status === 'failed') {
                console.error('Task failed');
                clearInterval(checkInterval);
                showNotification(t('video_failed'), 'error');
                resetGenerator();
                
            } else if (data.status === 'processing' || data.status === 'pending' || data.status === 'queued') {
                console.log(`Task ${data.status}...`);
                updateProgress(simulatedProgress, t('processing') + '...');
                
            } else {
                console.log(`Unknown status: ${data.status}`);
                updateProgress(simulatedProgress, t('processing'));
            }
            
            if (attempts >= maxAttempts) {
                clearInterval(checkInterval);
                showNotification(t('timeout'), 'error');
                resetGenerator();
            }
            
        } catch (error) {
            failedAttempts++;
            console.error('Status check error:', error);
            
            if (failedAttempts >= MAX_FAILED_ATTEMPTS) {
                clearInterval(checkInterval);
                showNotification(t('network_error'), 'error');
                resetGenerator();
            }
        }
    }, 5000);
}

// =========================
// VIDEO PLAYER
// =========================

function showVideo(videoUrl, taskId) {
    console.log('showVideo called with:', videoUrl, taskId);
    
    document.getElementById('progressArea').style.display = 'none';
    document.getElementById('videoPlayer').style.display = 'block';
    
    const video = document.getElementById('resultVideo');
    video.src = videoUrl;
    
    video.addEventListener('loadeddata', function() {
        console.log('Video loaded successfully');
    });
    
    video.addEventListener('error', function(e) {
        console.error('Video load error:', e);
        showNotification(t('video_load_error'), 'error');
    });
    
    video.load();
    
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.onclick = () => downloadVideo(taskId);
    }
    
    console.log('Video player updated');
}

function downloadVideo(taskId) {
    console.log('Download clicked for task:', taskId);
    
    if (!taskId) {
        showNotification(t('task_id_missing'), 'error');
        return;
    }
    
    const downloadUrl = `/download/${taskId}`;
    console.log('Downloading from:', downloadUrl);
    
    window.location.href = downloadUrl;
    showNotification(t('download_starting'), 'info');
}

function resetGenerator() {
    if (checkInterval) {
        clearInterval(checkInterval);
        checkInterval = null;
    }
    
    currentTaskId = null;
    currentVideoUrl = null;
    failedAttempts = 0;
    
    document.getElementById('progressArea').style.display = 'none';
    document.getElementById('videoPlayer').style.display = 'none';
    document.getElementById('previewArea').style.display = 'flex';
}

// =========================
// HISTORY
// =========================

async function loadHistory() {
    const historyGrid = document.getElementById('historyGrid');
    
    try {
        const response = await fetch('/history');
        const data = await response.json();
        
        if (data.success && data.videos.length > 0) {
            historyGrid.innerHTML = '';
            
            data.videos.forEach(video => {
                const card = createHistoryCard(video);
                historyGrid.appendChild(card);
            });
            
            document.getElementById('totalVideos').textContent = data.videos.length;
        } else {
            historyGrid.innerHTML = `
                <div class="loading-spinner">
                    <i class="fas fa-folder-open"></i>
                    <p>${t('no_videos')}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('History load error:', error);
        historyGrid.innerHTML = `
            <div class="loading-spinner">
                <i class="fas fa-exclamation-circle"></i>
                <p>${t('error')}</p>
            </div>
        `;
    }
}

function createHistoryCard(video) {
    const card = document.createElement('div');
    card.className = 'history-card';
    card.innerHTML = `
        <video src="${video.url}" muted loop onmouseenter="this.play()" onmouseleave="this.pause()"></video>
        <div class="history-card-info">
            <h4>${t('task')}: ${video.task_id}</h4>
            <p><i class="fas fa-clock"></i> ${video.created}</p>
            <div class="history-card-actions">
                <button class="btn btn-secondary" onclick="window.open('${video.url}', '_blank')">
                    <i class="fas fa-play"></i> ${t('view')}
                </button>
                <button class="btn btn-secondary" onclick="window.location.href='${video.download_url}'">
                    <i class="fas fa-download"></i> ${t('download')}
                </button>
            </div>
        </div>
    `;
    return card;
}

// =========================
// NOTIFICATIONS
// =========================

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#6366f1'};
        color: white;
        border-radius: 10px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        animation: slideInRight 0.3s ease-out;
        max-width: 400px;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Add notification animations if not already added
if (!document.getElementById('notification-animations')) {
    const style = document.createElement('style');
    style.id = 'notification-animations';
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}