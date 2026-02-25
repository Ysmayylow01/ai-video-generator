// static/js/main.js - Göni URL görmek üçin

let currentTaskId = null;
let currentVideoUrl = null;
let checkInterval = null;
let selectedMotionId = null;
let failedAttempts = 0;
const MAX_FAILED_ATTEMPTS = 3;

document.addEventListener('DOMContentLoaded', function() {
    initializeMotionCards();
    initializeForm();
    loadHistory();
    smoothScroll();
});

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

function initializeMotionCards() {
    const motionCards = document.querySelectorAll('.motion-card');
    
    motionCards.forEach(card => {
        card.addEventListener('click', function() {
            motionCards.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            selectedMotionId = this.dataset.motionId === 'null' ? null : this.dataset.motionId;
        });
    });
    
    if (motionCards.length > 0) {
        motionCards[0].classList.add('active');
    }
}

function initializeForm() {
    const form = document.getElementById('videoForm');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        await generateVideo();
    });
}

// static/js/main.js - generateVideo funksiýasyny täzeläň

async function generateVideo() {
    const prompt = document.getElementById('prompt').value;
    const imageUrl = document.getElementById('imageUrl').value || null;  // optional
    const duration = parseInt(document.getElementById('duration').value);
    const resolution = document.getElementById('resolution').value;
    const aspectRatio = document.getElementById('aspectRatio').value;
    const seed = document.getElementById('seed').value || null;
    
    if (!prompt) {
        showNotification('Prompt meýdany hökmany!', 'error');
        return;
    }
    
    const generateBtn = document.getElementById('generateBtn');
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Işlenýär...';
    
    try {
        const payload = {
            prompt: prompt,
            duration: duration,
            resolution: resolution,
            aspect_ratio: aspectRatio
        };
        
        // Optional fields
        if (imageUrl) {
            payload.image_url = imageUrl;
        }
        if (seed) {
            payload.seed = parseInt(seed);
        }
        
        console.log('Sending payload:', payload);
        
        const response = await fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentTaskId = data.task_id;
            failedAttempts = 0;
            showProgress();
            startStatusCheck();
            showNotification('Wideo döredilýär!', 'success');
        } else {
            throw new Error(data.error || 'Näbelli ýalňyşlyk');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Ýalňyşlyk: ' + error.message, 'error');
        resetGenerator();
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> Wideo Döret';
    }
}


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

function updateProgress(percent, status) {
    const circle = document.querySelector('.progress-ring-circle');
    const radius = circle.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (percent / 100 * circumference);
    
    circle.style.strokeDashoffset = offset;
    document.getElementById('progressPercent').textContent = Math.round(percent) + '%';
    document.getElementById('progressStatus').textContent = status;
}
// static/js/main.js

function startStatusCheck() {
    let attempts = 0;
    const maxAttempts = 180;
    
    updateProgress(10, 'Başlanýar...');
    
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
                    showNotification('Status barlamak başartmady', 'error');
                    resetGenerator();
                    return;
                }
                updateProgress(simulatedProgress, 'Gaýtadan synanyşýar...');
                return;
            }
            
            const data = await response.json();
            console.log('Status data:', data);
            
            if (!data.success) {
                failedAttempts++;
                if (failedAttempts >= MAX_FAILED_ATTEMPTS) {
                    clearInterval(checkInterval);
                    showNotification(data.error || 'Ýalňyşlyk', 'error');
                    resetGenerator();
                    return;
                }
                updateProgress(simulatedProgress, 'Gaýtadan synanyşýar...');
                return;
            }
            
            failedAttempts = 0;
            
            // Status barlamak
            if (data.status === 'completed') {
                console.log('✅ Task completed!');
                
                // Video URL barlamak
                if (!data.video_url) {
                    console.error('No video URL in response!');
                    console.log('Full response:', data);
                    clearInterval(checkInterval);
                    showNotification('Video URL tapylmady', 'error');
                    resetGenerator();
                    return;
                }
                
                clearInterval(checkInterval);
                updateProgress(100, 'Taýýar!');
                currentVideoUrl = data.video_url;
                
                console.log('Video URL:', currentVideoUrl);
                
                setTimeout(() => {
                    showVideo(data.video_url, currentTaskId);
                    showNotification('Wideo taýýar!', 'success');
                    loadHistory();
                }, 1000);
                
            } else if (data.status === 'failed') {
                console.error('Task failed');
                clearInterval(checkInterval);
                showNotification('Wideo döredilmedi', 'error');
                resetGenerator();
                
            } else if (data.status === 'processing' || data.status === 'pending' || data.status === 'queued') {
                console.log(`Task ${data.status}...`);
                updateProgress(simulatedProgress, `Işlenýär... (${data.status})`);
                
            } else {
                console.log(`Unknown status: ${data.status}`);
                updateProgress(simulatedProgress, `Status: ${data.status}`);
            }
            
            if (attempts >= maxAttempts) {
                clearInterval(checkInterval);
                showNotification('Timeout!', 'error');
                resetGenerator();
            }
            
        } catch (error) {
            failedAttempts++;
            console.error('Status check error:', error);
            
            if (failedAttempts >= MAX_FAILED_ATTEMPTS) {
                clearInterval(checkInterval);
                showNotification('Network ýalňyşlygy', 'error');
                resetGenerator();
            }
        }
    }, 5000);
}

function showVideo(videoUrl, taskId) {
    console.log('showVideo called with:', videoUrl, taskId);
    
    document.getElementById('progressArea').style.display = 'none';
    document.getElementById('videoPlayer').style.display = 'block';
    
    const video = document.getElementById('resultVideo');
    video.src = videoUrl;
    
    // Video load event
    video.addEventListener('loadeddata', function() {
        console.log('Video loaded successfully');
    });
    
    video.addEventListener('error', function(e) {
        console.error('Video load error:', e);
        showNotification('Wideo ýüklenip bilmedi', 'error');
    });
    
    video.load();
    
    // Download button update
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.onclick = () => downloadVideo(taskId);
    }
    
    console.log('Video player updated');
}

function downloadVideo(taskId) {
    console.log('Download clicked for task:', taskId);
    
    if (!taskId) {
        showNotification('Task ID ýok!', 'error');
        return;
    }
    
    // Download URL
    const downloadUrl = `/download/${taskId}`;
    console.log('Downloading from:', downloadUrl);
    
    // Open in new tab or download
    window.location.href = downloadUrl;
    showNotification('Wideo göçürilýär...', 'info');
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
                    <p>Wideo ýok</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('History load error:', error);
    }
}

function createHistoryCard(video) {
    const card = document.createElement('div');
    card.className = 'history-card';
    card.innerHTML = `
        <video src="${video.url}" muted loop onmouseenter="this.play()" onmouseleave="this.pause()"></video>
        <div class="history-card-info">
            <h4>Task: ${video.task_id}</h4>
            <p><i class="fas fa-clock"></i> ${video.created}</p>
            <div class="history-card-actions">
                <button class="btn btn-secondary" onclick="window.open('${video.url}', '_blank')">
                    <i class="fas fa-play"></i> Görmek
                </button>
                <button class="btn btn-secondary" onclick="window.location.href='${video.download_url}'">
                    <i class="fas fa-download"></i> Göçür
                </button>
            </div>
        </div>
    `;
    return card;
}

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