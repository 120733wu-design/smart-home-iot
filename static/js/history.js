var tempChart = null;
var humiChart = null;
var lightChart = null;
var currentDeviceId = null;

document.addEventListener('DOMContentLoaded', function () {

    loadDevSel('hist-device', function () {
        currentDeviceId = document.getElementById('hist-device').value;
        setQuickTime(1);
    });

    document.getElementById('btn-query-history').addEventListener('click', queryHistory);

    document.querySelectorAll('.hist-quick').forEach(function (b) {
        b.addEventListener('click', function () {
            document.querySelectorAll('.hist-quick').forEach(x => x.classList.remove('active'));
            this.classList.add('active');
            setQuickTime(parseInt(this.dataset.hours));
        });
    });

    document.getElementById('hist-device').addEventListener('change', function () {
        currentDeviceId = this.value;
        if (currentDeviceId) queryHistory();
    });
});

// ===== 时区 =====
function getCSTDate(rawStr) {
    return new Date(rawStr + " +08:00");
}

function parseTime(str) {
    return getCSTDate(str).getTime();
}

// ===== 快捷时间 =====
function setQuickTime(h) {
    const now = new Date();
    const start = new Date(now.getTime() - h * 3600 * 1000);

    document.getElementById('hist-start').value = fmt(start);
    document.getElementById('hist-end').value = fmt(now);

    if (currentDeviceId) queryHistory();
}

function fmt(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day}T${h}:${min}`;
}

// ===== 主查询 =====
async function queryHistory() {
    if (!currentDeviceId) return;

    const st = document.getElementById('hist-start').value;
    const en = document.getElementById('hist-end').value;

    const res = await apiGet(
        `/api/devices/${currentDeviceId}/data/latest-n?limit=1000&start=${st}&end=${en}`
    );

    if (!res.success) return;

    renderCharts(res.data);
}

// ===== 初始化图表 =====
function initCharts() {

    tempChart = echarts.init(document.getElementById('chart-temp'));
    humiChart = echarts.init(document.getElementById('chart-humi'));
    lightChart = echarts.init(document.getElementById('chart-light'));

    tempChart.setOption(baseOption('温度', '#dc3545'));
    humiChart.setOption(baseOption('湿度', '#0d6efd'));
    lightChart.setOption(baseOption('光照', '#f59e0b'));
}

function baseOption(name, color) {
    return {
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'time' },
        yAxis: { type: 'value', name: name },
        series: [{
            name: name,
            type: 'line',
            smooth: true,
            showSymbol: false,
            lineStyle: { width: 2, color: color },
            data: []
        }]
    };
}

// ===== 数据拆分 =====
function split(arr) {
    return (arr || []).map(x => [
        parseTime(x.recorded_at),
        x.value
    ]);
}

// ===== 渲染 =====
function renderCharts(data) {

    if (!tempChart) initCharts();

    const temp = split(data.temperature);
    const humi = split(data.humidity);
    const light = split(data.light);

    tempChart.setOption({ series: [{ data: temp }] });
    humiChart.setOption({ series: [{ data: humi }] });
    lightChart.setOption({ series: [{ data: light }] });
}

// ===== 设备列表 =====
function loadDevSel(sid, cb) {
    apiGet('/api/devices').then(d => {
        const sel = document.getElementById(sid);
        if (d.success && d.data.length) {
            sel.innerHTML = d.data.map(x =>
                `<option value="${x.id}">${x.name} (${x.location || '-'})</option>`
            ).join('');
            if (cb) cb();
        }
    });
}

// ===== resize =====
window.addEventListener('resize', function () {
    tempChart && tempChart.resize();
    humiChart && humiChart.resize();
    lightChart && lightChart.resize();
});