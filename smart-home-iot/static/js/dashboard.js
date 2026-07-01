var realChart = null, predChart = null, chartMode = 'all';
document.addEventListener('DOMContentLoaded', function () {
    loadStats();
    loadAlerts();
    loadOutdoorWeather();
    initRealChart();
    initPredChart();
    // 天气每10分钟刷新一次，匹配后端缓存
    setInterval(loadOutdoorWeather, 600000);
});

// 统一时区修复：数据库时间字符串强制东八区
function getCSTDate(rawStr) {
    return new Date(rawStr + " +08:00");
}

// 室外天气加载函数（适配apiGet容错，404友好处理）
async function loadOutdoorWeather() {
    const res = await apiGet("/api/data/weather/outdoor?city=天津");
    const tempDom = document.getElementById("out-temp");
    const humDom = document.getElementById("out-humi");
    const weatherDom = document.getElementById("out-weather-text");
    if (!res.success) {
        // 接口404/异常展示占位文字，不抛控制台错误
        if(tempDom) tempDom.textContent = "--";
        if(humDom) humDom.textContent = "--";
        if(weatherDom) weatherDom.textContent = "天气服务暂不可用";
        return;
    }
    if(tempDom) tempDom.textContent = res.out_temp + " ℃";
    if(humDom) humDom.textContent = res.out_humi + " %";
    if(weatherDom) weatherDom.textContent = res.weather_text;
}

async function loadStats() {
    var d = await apiGet('/api/statistics');
    if (!d.success) return;
    var s = d.data;
    document.getElementById('stat-total-devices').textContent = s.total_devices;
    document.getElementById('stat-online-devices').textContent = s.online_devices;
    document.getElementById('stat-online-rate').textContent = s.online_rate + '%';
    document.getElementById('stat-unread-alerts').textContent = s.unread_alerts;
}

async function loadAlerts() {
    var d = await apiGet('/api/alerts?per_page=5');
    var el = document.getElementById('recent-alerts-list');
    if (!d.success || !d.data.length) {
        el.innerHTML = '<div class="text-center text-muted py-5"><i class="bi bi-check-circle text-success" style="font-size:2rem"></i><p class="mt-2 mb-0 small">暂无告警</p></div>';
        return;
    }
    el.innerHTML = d.data.map(function (a) {
        var cls = a.severity === 'critical' ? 'danger' : a.severity === 'warning' ? 'warning' : 'info';
        return '<div class="alert alert-' + cls + ' py-2 px-3 mb-2" style="font-size:.82rem;border-radius:8px"><div class="d-flex justify-content-between align-items-center"><span>' + a.message + '</span><small class="text-muted ms-2 text-nowrap">' + formatTime(a.created_at) + '</small></div></div>';
    }).join('');
}

function initRealChart() {
    realChart = initChart('dashboard-real-chart');
    if (!realChart) return;
    realChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8 },
        grid: { left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true },
        xAxis: { type: 'time', axisLabel: { fontSize: 11 } },
        // 恢复双Y轴 温度左、湿度右，移除光照轴
        yAxis: [
            {
                type: 'value',
                name: '温度 °C',
                nameTextStyle: { fontSize: 11, color: '#94a3b8' },
                position: 'left',
                splitLine: { lineStyle: { color: '#f1f5f9' } }
            },
            {
                type: 'value',
                name: '湿度 %',
                nameTextStyle: { fontSize: 11, color: '#94a3b8' },
                position: 'right',
                splitLine: { show: false }
            }
        ],
        // 仅保留温度、湿度两条曲线，删除光照series
        series: [
            { name: '温度', type: 'line', smooth: true, showSymbol: false, lineStyle: { color: '#ef4444', width: 2 }, data: [] },
            { name: '湿度', type: 'line', smooth: true, showSymbol: false, yAxisIndex: 1, lineStyle: { color: '#3b82f6', width: 2 }, data: [] }
        ]
    });
    refreshChartData();
    setInterval(refreshChartData, 10000);
}

async function refreshChartData() {
    if (!realChart) return;
    var did = await getSensorDeviceId();
    if (!did) {
        console.warn('[Dashboard] No sensor device found, chart data skipped');
        return;
    }
    var d = await apiGet('/api/devices/' + did + '/data/all-recent?hours=2');
    if (!d.success) return;
    var td = (d.data.temperature || []).map(function (x) { return [parseTime(x.recorded_at), x.value]; });
    var hd = (d.data.humidity || []).map(function (x) { return [parseTime(x.recorded_at), x.value]; });
    // 移除光照ld变量，只传温湿度
    updateChartSeries(td, hd);
}

// 只接收温湿度两个参数，删除light相关分支
function updateChartSeries(t, h) {
    if (!realChart) return;
    t = t || [];
    h = h || [];
    if (chartMode === 'all') {
        realChart.setOption({ series: [{ data: t }, { data: h }] });
    } else if (chartMode === 'temp') {
        realChart.setOption({ series: [{ data: t }, { data: [] }] });
    } else if (chartMode === 'humi') {
        realChart.setOption({ series: [{ data: [] }, { data: h }] });
    }
}

function dashboardChartSwitch(m, event) {
    chartMode = m;
    var btns = document.querySelectorAll('.btn-group .btn');
    for (var i = 0; i < btns.length; i++) btns[i].classList.remove('active');
    if (event && event.target) event.target.classList.add('active');
    refreshChartData();
}

function initPredChart() {
    predChart = initChart('dashboard-prediction-chart');
    if (!predChart) return;
    predChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8 },
        grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
        xAxis: { type: 'time', axisLabel: { fontSize: 11 } },
        yAxis: {
            type: 'value',
            name: '数值',
            nameTextStyle: { fontSize: 11, color: '#94a3b8' },
            splitLine: { lineStyle: { color: '#f1f5f9' } }
        },
        color: ['#ef4444', '#ef4444', '#3b82f6', '#3b82f6'],
        series: [
            { name: '温度历史', type: 'line', smooth: true, showSymbol: false, lineStyle: { width: 2 }, areaStyle: { opacity: .05 }, data: [] },
            { name: '温度预测', type: 'line', smooth: true, showSymbol: false, lineStyle: { type: 'dashed', width: 2 }, data: [] },
            { name: '湿度历史', type: 'line', smooth: true, showSymbol: false, lineStyle: { width: 2 }, areaStyle: { opacity: .05 }, data: [] },
            { name: '湿度预测', type: 'line', smooth: true, showSymbol: false, lineStyle: { type: 'dashed', width: 2 }, data: [] }
        ]
    });
    refreshPredData();
    setInterval(refreshPredData, 60000);
}

async function refreshPredData() {
    if (!predChart) return;
    var did = await getSensorDeviceId();
    if (!did) return;
    var t = await apiGet('/api/predictions/latest?device_id=' + did + '&type=temperature&predict_hours=6');
    var h = await apiGet('/api/predictions/latest?device_id=' + did + '&type=humidity&predict_hours=6');
    if (!t.success || !h.success) return;
    var th = (t.data.history || []).map(function (x) { return [parseTime(x.recorded_at), x.value]; });
    var tp = (t.data.predictions || []).map(function (x) { return [parseTime(x.predicted_at), x.predicted_value]; });
    var hh = (h.data.history || []).map(function (x) { return [parseTime(x.recorded_at), x.value]; });
    var hp = (h.data.predictions || []).map(function (x) { return [parseTime(x.predicted_at), x.predicted_value]; });
    predChart.setOption({ series: [{ data: th }, { data: tp }, { data: hh }, { data: hp }] });
}

// 修复：解析数据库时间字符串，强制东八区
function parseTime(str) {
    return getCSTDate(str).getTime();
}

// 修复：格式化时间展示
function formatTime(rawStr) {
    const d = getCSTDate(rawStr);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const h = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day} ${h}:${min}`;
}