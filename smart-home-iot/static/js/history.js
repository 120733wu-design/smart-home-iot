var historyChart = null, currentDeviceId = null;
document.addEventListener('DOMContentLoaded', function () {
    loadDevSel('hist-device', function () {
        currentDeviceId = document.getElementById('hist-device').value;
        setQuickTime(1);
    });
    document.getElementById('btn-query-history').addEventListener('click', queryHistory);
    document.querySelectorAll('.hist-quick').forEach(function (b) {
        b.addEventListener('click', function () {
            document.querySelectorAll('.hist-quick').forEach(function (x) {
                x.classList.remove('active');
            });
            this.classList.add('active');
            setQuickTime(parseInt(this.dataset.hours));
        });
    });
    document.getElementById('hist-device').addEventListener('change', function () {
        currentDeviceId = this.value;
        if (currentDeviceId) queryHistory();
    });
    document.getElementById('hist-type').addEventListener('change', queryHistory);
});

// 固定时区：数据库字符串 +08:00 强制东八区
function getCSTDate(rawStr) {
    return new Date(rawStr + " +08:00");
}

// 快速时间筛选修复，使用真实服务器东八区时间
function setQuickTime(h) {
    // 直接获取当前北京时间
    const nowCst = new Date();
    const startCst = new Date(nowCst.getTime() - h * 3600 * 1000);
    document.getElementById('hist-start').value = fdt(startCst);
    document.getElementById('hist-end').value = fdt(nowCst);
    if (currentDeviceId) queryHistory();
}

function fdt(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day}T${h}:${min}`;
}

async function queryHistory() {
    if (!currentDeviceId) return;
    const st = document.getElementById('hist-start').value;
    const en = document.getElementById('hist-end').value;
    const sensorType = document.getElementById('hist-type').value;
    const titleMap = {
        temperature: "温度历史曲线",
        humidity: "湿度历史曲线",
        light: "光照历史曲线"
    };
    document.getElementById('history-chart-title').textContent = titleMap[sensorType];
    try {
        const res = await apiGet(`/api/devices/${currentDeviceId}/data?type=${sensorType}&start=${st}&end=${en}&per_page=10000`);
        const data = res.success ? res.data : [];
        document.getElementById('history-data-count').textContent = `共 ${res.total} 条数据`;
        updateChart(data, sensorType);
    } catch (e) {
        console.error('查询失败', e);
    }
}

function updateChart(rawData, sensorType) {
    if (historyChart) historyChart.dispose();
    const dom = document.getElementById('history-chart');
    historyChart = echarts.init(dom);
    // 1. 先过滤前端 value <= 0 无效脏数据，双重兜底
    const validData = (rawData || []).filter(item => Number(item.value) > 0);
    // 按时间升序排序
    const sorted = validData.sort((a, b) => parseTime(a.recorded_at) - parseTime(b.recorded_at));
    let seriesData = sorted.map(d => [parseTime(d.recorded_at), d.value]);
    if (sensorType === 'light') {
        seriesData = sorted.map(d => [parseTime(d.recorded_at), 1023 - d.value]);
    }
    const nameMap = {
        temperature: "温度 (°C)",
        humidity: "湿度 (%)",
        light: "光照 (lux)"
    };
    const colorMap = {
        temperature: "#dc3545",
        humidity: "#0d6efd",
        light: "#ffc107"
    };
    const curName = nameMap[sensorType];
    const curColor = colorMap[sensorType];
    const option = {
        tooltip: {
            trigger: 'axis',
            confine: true,
            formatter(params) {
                const p = params[0];
                return formatTime(p.value[0]) + '<br/>' + p.marker + ' ' + p.seriesName + ': ' + p.value[1];
            }
        },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'time', scale: false },
        yAxis: { type: 'value', name: curName },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', bottom: 0, height: 18 }
        ],
        series: [{
            name: curName,
            type: 'line',
            smooth: true,
            showSymbol: false,
            connectNulls: false,
            areaStyle: { opacity: 0 },
            lineStyle: { width: 2, color: curColor },
            markPoint: { data: [{ type: 'max', name: '最大值' }, { type: 'min', name: '最小值' }] },
            data: seriesData
        }]
    };
    historyChart.setOption(option);
}

function loadDevSel(sid, cb) {
    apiGet('/api/devices').then(d => {
        const sel = document.getElementById(sid);
        if (d.success && d.data.length) {
            sel.innerHTML = d.data.map(x => `<option value="${x.id}">${x.name} (${x.location || '-'})</option>`).join('');
            if (cb) cb();
        }
    });
}
window.addEventListener('resize', () => { if (historyChart) historyChart.resize(); });

// 修复：解析数据库时间字符串为正确时间戳
function parseTime(str) {
    return getCSTDate(str).getTime();
}

// 修复：时间戳格式化，输出东八区时间
function formatTime(ts) {
    const d = new Date(ts);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day} ${h}:${min}`;
}
function initChart(domId) {
    const dom = document.getElementById(domId);
    if (!dom) return null;
    if (historyChart) historyChart.dispose();
    return echarts.init(dom);
}