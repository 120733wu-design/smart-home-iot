// 通用GET请求（增加异常捕获+状态码校验）
async function apiGet(u) {
    try {
        const r = await fetch(u);
        // 非2xx状态码统一返回失败对象，不解析JSON
        if (!r.ok) {
            return { success: false, msg: "服务器请求异常" };
        }
        return await r.json();
    } catch (err) {
        return { success: false, msg: "网络请求失败" };
    }
}

// ========== 全局设备缓存：device_key → device_id 自动映射 ==========
var _deviceCache = null;
var _sensorDeviceId = null;

/**
 * 自动从 /api/devices 获取设备列表，按 type='sensor' 精准匹配
 * 所有页面统一调用此函数，不再写死 device_id 或取 ds.data[0].id
 * @returns {number|null} 传感器设备的 ID，找不到返回 null
 */
async function getSensorDeviceId() {
    if (_sensorDeviceId !== null) return _sensorDeviceId;
    try {
        const resp = await apiGet('/api/devices');
        if (resp.success && resp.data.length) {
            _deviceCache = resp.data;
            // 精确匹配 type === 'sensor' 且有在线状态或最新数据的设备
            // 优先匹配 device_key 包含 'sensor' 的设备（真实 ESP8266）
            var sensorDev = resp.data.find(function(d) {
                return d.device_key && d.device_key.toLowerCase() === 'sensor';
            });
            // 其次匹配 device_key 包含 'esp' 且 type === 'sensor' 的设备
            if (!sensorDev) {
                sensorDev = resp.data.find(function(d) {
                    return d.device_key && d.device_key.toLowerCase().indexOf('esp') >= 0 && d.type === 'sensor';
                });
            }
            // 最后 fallback: 第一个 type === 'sensor' 的设备
            if (!sensorDev) {
                sensorDev = resp.data.find(function(d) { return d.type === 'sensor'; });
            }
            if (sensorDev) {
                _sensorDeviceId = sensorDev.id;
                console.log('[Device] Auto-selected sensor device: id=' + sensorDev.id + ' key=' + sensorDev.device_key + ' name=' + sensorDev.name);
            } else {
                console.warn('[Device] No sensor-type device found, falling back to first device id=' + resp.data[0].id);
                _sensorDeviceId = resp.data[0].id;
            }
        }
    } catch(e) {
        console.error('[Device] Failed to load device list:', e);
    }
    return _sensorDeviceId;
}

/**
 * 强制刷新设备缓存（设备增删后调用）
 */
async function refreshDeviceCache() {
    _deviceCache = null;
    _sensorDeviceId = null;
    return getSensorDeviceId();
}

// 通用POST请求
async function apiPost(u, d) {
    try {
        const r = await fetch(u, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(d)
        });
        if (!r.ok) {
            return { success: false, msg: "服务器请求异常" };
        }
        return await r.json();
    } catch (err) {
        return { success: false, msg: "网络请求失败" };
    }
}

// 通用PUT请求
async function apiPut(u, d) {
    try {
        const r = await fetch(u, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(d)
        });
        if (!r.ok) {
            return { success: false, msg: "服务器请求异常" };
        }
        return await r.json();
    } catch (err) {
        return { success: false, msg: "网络请求失败" };
    }
}

// 通用DELETE请求
async function apiDelete(u) {
    try {
        const r = await fetch(u, { method: 'DELETE' });
        if (!r.ok) {
            return { success: false, msg: "服务器请求异常" };
        }
        return await r.json();
    } catch (err) {
        return { success: false, msg: "网络请求失败" };
    }
}

// 时间格式化（中文本地时间）
function formatTime(dt) {
    if (!dt) return '';
    return new Date(dt).toLocaleString('zh-CN', { hour12: false });
}

// 时间转时间戳
function parseTime(dt) {
    if (!dt) return 0;
    return new Date(dt).getTime();
}

// 初始化ECharts实例：修复echarts未定义报错
function initChart(id) {
    const dom = document.getElementById(id);
    // 先判断echarts全局对象是否存在，不存在直接返回null不报错
    if (!dom || typeof echarts === 'undefined') {
        return null;
    }
    return echarts.init(dom);
}

// 全局Toast弹窗提示
function showToast(msg, type) {
    type = type || 'success';
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999';
        document.body.appendChild(container);
    }
    const bgClass = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-warning';
    const iconClass = type === 'success' ? 'bi-check-circle' : type === 'error' ? 'bi-x-circle' : 'bi-exclamation-circle';

    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center text-white ' + bgClass + ' border-0 show';
    toastEl.role = 'alert';
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi ${iconClass} me-2"></i>${msg}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    container.appendChild(toastEl);
    // 4秒后自动销毁
    setTimeout(() => toastEl.remove(), 4000);
}

// HTML转义防XSS
function escapeHtml(s) {
    const tempDiv = document.createElement('div');
    tempDiv.textContent = s || '';
    return tempDiv.innerHTML;
}

// 页面DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function () {
    // 侧边栏折叠按钮
    const toggleBtn = document.getElementById('menu-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function () {
            document.getElementById('sidebar-wrapper').classList.toggle('toggled');
        });
    }

    // 登出按钮
    const logoutBtn = document.getElementById('btn-logout');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async function () {
            await apiPost('/logout');
            window.location.href = '/login';
        });
    }

    // 未读告警角标定时刷新（30秒一次）
    const alertBadge = document.getElementById('alert-badge');
    if (alertBadge) {
        setInterval(async function () {
            const res = await apiGet('/api/alerts/stats');
            if (res.success) {
                // 后端返回字段 unread，不是 unread_count
                const count = res.unread || 0;
                alertBadge.textContent = count;
                alertBadge.style.display = count > 0 ? 'inline-block' : 'none';
            }
        }, 30000);
    }
});