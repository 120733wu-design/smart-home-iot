var realChart = null, predChart = null;
var currentDeviceId = null;

document.addEventListener('DOMContentLoaded', function () {

    loadStats();
    loadAlerts();
    loadOutdoorWeather();

    // 设备选择（必须）
    loadDeviceSelect('dashboard-device-select', function () {
        currentDeviceId = document.getElementById('dashboard-device-select').value;
        initRealChart();
        initPredChart();
    });

    document.getElementById('dashboard-device-select')?.addEventListener('change', function () {
        currentDeviceId = this.value;
        refreshChartData();
        refreshPredData();
    });

    setInterval(loadOutdoorWeather, 600000);
});


// =========================
// 设备选择（本地实现，避免依赖报错）
// =========================
async function loadDeviceSelect(id, cb) {
    try {
        var d = await apiGet('/api/devices');
        var sel = document.getElementById(id);

        if (d.success && d.data.length) {
            sel.innerHTML = d.data.map(x =>
                `<option value="${x.id}">${x.name}</option>`
            ).join('');
            cb && cb();
        }
    } catch (e) {
        console.error(e);
    }
}


// =========================
// 外部天气
// =========================
async function loadOutdoorWeather() {
    const res = await apiGet("/api/weather/outdoor?city=天津");

    const tempDom = document.getElementById("out-temp");
    const humDom = document.getElementById("out-humi");
    const weatherDom = document.getElementById("out-weather-text");

    if (!res.success) {
        if (tempDom) tempDom.textContent = "--";
        if (humDom) humDom.textContent = "--";
        if (weatherDom) weatherDom.textContent = "天气不可用";
        return;
    }

    if (tempDom) tempDom.textContent = res.out_temp + " ℃";
    if (humDom) humDom.textContent = res.out_humi + " %";
    if (weatherDom) weatherDom.textContent = res.weather_text;
}


// =========================
// 统计
// =========================
async function loadStats() {
    var d = await apiGet('/api/statistics');
    if (!d.success) return;

    var s = d.data;
    document.getElementById('stat-total-devices').textContent = s.total_devices;
    document.getElementById('stat-online-devices').textContent = s.online_devices;
    document.getElementById('stat-online-rate').textContent = s.online_rate + '%';
    document.getElementById('stat-unread-alerts').textContent = s.unread_alerts;
}


// =========================
// 告警
// =========================
async function loadAlerts() {
    var d = await apiGet('/api/alerts?per_page=5');
    var el = document.getElementById('recent-alerts-list');

    if (!d.success || !d.data.length) {
        el.innerHTML = '<div class="text-center text-muted py-4">暂无告警</div>';
        return;
    }

    el.innerHTML = d.data.map(a =>
        `<div class="alert alert-secondary py-1 px-2 mb-1">
            <div class="d-flex justify-content-between">
                <span>${a.message}</span>
                <small>${formatTime(a.created_at)}</small>
            </div>
        </div>`
    ).join('');
}


// =========================
// 主图表（温度 + 湿度）
// =========================
function initRealChart() {
    realChart = initChart('dashboard-real-chart');
    if (!realChart) return;

    realChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { bottom: 0 },

        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            top: '5%',
            containLabel: true
        },

        xAxis: { type: 'time' },

        yAxis: [
            {
                type: 'value',
                name: '温度 °C'
            },
            {
                type: 'value',
                name: '湿度 %'
            }
        ],

        series: [
            {
                name: '温度',
                type: 'line',
                data: [],
                smooth: true,
                showSymbol: false,
                lineStyle: { color: '#ef4444', width: 2 }
            },
            {
                name: '湿度',
                type: 'line',
                data: [],
                smooth: true,
                showSymbol: false,
                yAxisIndex: 1,
                lineStyle: { color: '#3b82f6', width: 2 }
            }
        ]
    });

    refreshChartData();
    setInterval(refreshChartData, 10000);
}


// =========================
// ⭐核心：数据刷新（对齐monitor）
// =========================
async function refreshChartData() {
    if (!realChart || !currentDeviceId) return;

    try {
        const t = await apiGet(`/api/devices/${currentDeviceId}/data/latest?type=temperature&hours=1`);
        const h = await apiGet(`/api/devices/${currentDeviceId}/data/latest?type=humidity&hours=1`);

        if (!t.success || !h.success) return;

        const tempData = (t.data || []).map(x => [
            parseTime(x.recorded_at),
            x.value
        ]);

        const humiData = (h.data || []).map(x => [
            parseTime(x.recorded_at),
            x.value
        ]);

        realChart.setOption({
            series: [
                { data: tempData },
                { data: humiData }
            ]
        });

    } catch (e) {
        console.error("dashboard refresh error", e);
    }
}


// =========================
// 预测图（保持原功能）
// =========================
function initPredChart() {
    predChart = initChart('dashboard-prediction-chart');
    if (!predChart) return;

    predChart.setOption({
        xAxis: { type: 'time' },
        yAxis: { type: 'value' },

        series: [
            { name: '温度历史', type: 'line', data: [] },
            { name: '温度预测', type: 'line', data: [] },
            { name: '湿度历史', type: 'line', data: [] },
            { name: '湿度预测', type: 'line', data: [] }
        ]
    });

    refreshPredData();
    setInterval(refreshPredData, 60000);
}

async function refreshPredData() {
    if (!predChart || !currentDeviceId) return;

    const t = await apiGet(`/api/predictions/latest?device_id=${currentDeviceId}&type=temperature&predict_hours=6`);
    const h = await apiGet(`/api/predictions/latest?device_id=${currentDeviceId}&type=humidity&predict_hours=6`);

    if (!t.success || !h.success) return;

    const th = (t.data.history || []).map(x => [parseTime(x.recorded_at), x.value]);
    const tp = (t.data.predictions || []).map(x => [parseTime(x.predicted_at), x.predicted_value]);

    const hh = (h.data.history || []).map(x => [parseTime(x.recorded_at), x.value]);
    const hp = (h.data.predictions || []).map(x => [parseTime(x.predicted_at), x.predicted_value]);

    predChart.setOption({
        series: [
            { data: th },
            { data: tp },
            { data: hh },
            { data: hp }
        ]
    });
}


// =========================
// 工具函数
// =========================
function getCSTDate(str) {
    return new Date(str + " +08:00");
}

function parseTime(str) {
    return getCSTDate(str).getTime();
}

function formatTime(str) {
    const d = getCSTDate(str);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}


// =========================
// echarts init
// =========================
function initChart(id) {
    const dom = document.getElementById(id);
    if (!dom) return null;
    return echarts.init(dom);
}