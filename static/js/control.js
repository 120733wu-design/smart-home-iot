/**
 * 远程控制面板 - control.js
 * 设备选择、继电器开关控制、命令记录展示
 */
(function () {
    'use strict';

    const state = {
        devices: [],
        mqttConnected: false
    };

    // ========== 初始化 ==========
    async function init() {
        await loadMQTTStatus();
        await loadDevices();
        await loadCommandHistory();
    }

    // ========== MQTT 状态 ==========
    async function loadMQTTStatus() {
        try {
            const res = await apiGet('/api/control/mqtt-status');
            if (res.success) {
                state.mqttConnected = res.data.connected;
                const badge = document.getElementById('mqtt-indicator');
                const brokerEl = document.getElementById('mqtt-broker');
                if (res.data.connected) {
                    badge.className = 'badge bg-success';
                    badge.innerHTML = '<i class="bi bi-check-circle me-1"></i>已连接';
                } else {
                    badge.className = 'badge bg-danger';
                    badge.innerHTML = '<i class="bi bi-x-circle me-1"></i>未连接（命令无法下发）';
                }
                brokerEl.textContent = 'Broker: ' + (res.data.broker || '未知');
            }
        } catch (e) {
            document.getElementById('mqtt-indicator').className = 'badge bg-danger';
            document.getElementById('mqtt-indicator').innerHTML = '<i class="bi bi-x-circle me-1"></i>状态未知';
        }
    }

    // ========== 加载可控制设备 ==========
    async function loadDevices() {
        try {
            const res = await apiGet('/api/control/devices');
            if (!res.success || !res.data.length) {
                document.getElementById('device-cards').innerHTML = `
                    <div class="col-12 text-center py-5">
                        <i class="bi bi-device-hdd display-4 text-muted d-block mb-3"></i>
                        <p class="text-muted">暂无可用设备</p>
                        <small class="text-secondary">请先在"设备管理"中添加设备</small>
                    </div>`;
                return;
            }
            state.devices = res.data;
            renderDeviceCards(res.data);
        } catch (e) {
            console.error('加载设备列表失败:', e);
        }
    }

    // ========== 渲染设备控制卡片 ==========
    function renderDeviceCards(devices) {
        const container = document.getElementById('device-cards');
        let html = '';
        devices.forEach(function (dev) {
            const isOnline = dev.status === 'online';
            const statusClass = isOnline ? 'success' : 'secondary';
            const statusText = isOnline ? '在线' : '离线';
            const statusIcon = isOnline ? 'wifi' : 'wifi-off';

            html += `
            <div class="col-lg-6 mb-4">
                <div class="card border-0 shadow-sm h-100">
                    <div class="card-header bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
                        <div>
                            <i class="bi bi-cpu-fill text-primary me-2"></i>
                            <span class="fw-bold">${escapeHtml(dev.name)}</span>
                            <small class="text-muted ms-2">${escapeHtml(dev.location || '')}</small>
                        </div>
                        <span class="badge bg-${statusClass}">
                            <i class="bi bi-${statusIcon} me-1"></i>${statusText}
                        </span>
                    </div>
                    <div class="card-body">
                        <div class="row g-3">`;

            // 按分组渲染控制按钮
            const groups = {};
            dev.controls.forEach(function (ctrl) {
                if (!groups[ctrl.group]) groups[ctrl.group] = [];
                groups[ctrl.group].push(ctrl);
            });

            Object.keys(groups).forEach(function (groupName) {
                const ctrls = groups[groupName];
                const label = groupName === 'relay1' ? '继电器 1 (灯/风扇)' : '继电器 2 (备用)';
                html += `
                            <div class="col-6">
                                <div class="border rounded p-3 text-center">
                                    <label class="form-label fw-bold text-secondary small mb-2">${label}</label>
                                    <div class="btn-group w-100" role="group">`;
                ctrls.forEach(function (ctrl) {
                    const btnClass = ctrl.id.includes('_on') ? 'btn-success' : 'btn-outline-danger';
                    const icon = ctrl.id.includes('_on') ? 'toggle-on' : 'toggle-off';
                    html += `
                                        <button class="btn btn-sm ${btnClass} ctrl-btn"
                                                data-device-key="${escapeHtml(dev.device_key)}"
                                                data-command="${ctrl.id}"
                                                data-device-name="${escapeHtml(dev.name)}"
                                                ${!state.mqttConnected ? 'disabled' : ''}>
                                            <i class="bi bi-${icon} me-1"></i>${ctrl.label.replace('继电器1 ', '').replace('继电器2 ', '')}
                                        </button>`;
                });
                html += `
                                    </div>
                                </div>
                            </div>`;
            });

            html += `
                        </div>
                        <div class="mt-2">
                            <small class="text-muted">设备Key: <code>${escapeHtml(dev.device_key)}</code></small>
                        </div>
                    </div>
                </div>
            </div>`;
        });
        container.innerHTML = html;

        // 绑定按钮事件
        document.querySelectorAll('.ctrl-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const deviceKey = this.dataset.deviceKey;
                const command = this.dataset.command;
                const deviceName = this.dataset.deviceName;
                sendControlCommand(deviceKey, command, deviceName, this);
            });
        });
    }

    // ========== 发送控制命令 ==========
    async function sendControlCommand(deviceKey, command, deviceName, btnEl) {
        // 按钮禁用 + loading
        const originalHTML = btnEl.innerHTML;
        btnEl.disabled = true;
        btnEl.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>发送中...';

        try {
            const res = await apiPost('/api/control/send', {
                device_key: deviceKey,
                command: command
            });
            if (res.success) {
                showToast(res.message || '命令已发送', 'success');
                // 刷新命令历史
                setTimeout(loadCommandHistory, 600);
            } else {
                showToast(res.message || '发送失败', 'danger');
            }
        } catch (e) {
            showToast('网络错误，命令发送失败', 'danger');
        } finally {
            btnEl.disabled = false;
            btnEl.innerHTML = originalHTML;
        }
    }

    // ========== 加载命令历史 ==========
    async function loadCommandHistory() {
        try {
            const res = await apiGet('/api/control/history?per_page=50');
            document.getElementById('cmd-total').textContent = res.data ? res.data.length : 0;
            if (!res.success || !res.data || res.data.length === 0) {
                document.getElementById('cmd-history-body').innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center text-muted py-4">
                            <i class="bi bi-inbox display-6 d-block mb-2"></i>暂无命令记录
                        </td>
                    </tr>`;
                return;
            }
            renderCommandHistory(res.data);
        } catch (e) {
            console.error('加载命令历史失败:', e);
        }
    }

    function renderCommandHistory(commands) {
        const tbody = document.getElementById('cmd-history-body');
        const statusMap = {
            'pending': { cls: 'warning', text: '已发送', icon: 'hourglass-split' },
            'acknowledged': { cls: 'success', text: '已确认', icon: 'check-circle' },
            'failed': { cls: 'danger', text: '失败', icon: 'x-circle' },
            'sent': { cls: 'info', text: '已发送', icon: 'send-check' }
        };
        let html = '';
        commands.forEach(function (cmd) {
            const s = statusMap[cmd.status] || { cls: 'secondary', text: cmd.status || '未知', icon: 'question-circle' };
            html += `
                <tr>
                    <td class="small">${cmd.created_at_str || '-'}</td>
                    <td><span class="fw-bold">${escapeHtml(cmd.device_name || '-')}</span></td>
                    <td><code>${escapeHtml(cmd.command || '-')}</code></td>
                    <td><span class="badge bg-${s.cls}"><i class="bi bi-${s.icon} me-1"></i>${s.text}</span></td>
                </tr>`;
        });
        tbody.innerHTML = html;
    }

    // ========== 事件 ==========
    document.getElementById('btn-refresh-history').addEventListener('click', loadCommandHistory);

    // 页面可见时自动刷新
    let autoRefreshTimer = null;
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) {
            loadMQTTStatus();
            loadCommandHistory();
            autoRefreshTimer = setInterval(function () {
                loadMQTTStatus();
                loadCommandHistory();
            }, 15000);
        } else {
            clearInterval(autoRefreshTimer);
        }
    });
    if (!document.hidden) {
        autoRefreshTimer = setInterval(function () {
            loadMQTTStatus();
            loadCommandHistory();
        }, 15000);
    }

    init();
})();
