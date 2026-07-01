var realChart = null, predChart = null, chartMode = 'all';
document.addEventListener('DOMContentLoaded', function () {
    loadStats();
    loadAlerts();
    initRealChart();
    initPredChart();
});

async function loadStats() {
    try {
        var d = await apiGet('/api/statistics');
        if (!d.success) return;
        var s = d.data;
        document.getElementById('stat-total-devices').textContent = s.total_devices;
        document.getElementById('stat-online-devices').textContent = s.online_devices;
        document.getElementById('stat-online-rate').textContent = s.online_rate + '%';
        document.getElementById('stat-unread-alerts').textContent = s.unread_alerts;
    } catch (e) {}
}

async function loadAlerts() {
    try {
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
    } catch (e) {}
}

function initRealChart() {
    realChart = initChart('dashboard-real-chart');
    if (!realChart) return;
    realChart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8 },
        grid: { left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true },
        xAxis: { type: 'time', axisLabel: { fontSize: 11 } },
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
        series: [
            { name: '温度', type: 'line', smooth: true, showSymbol: false, lineStyle: { color: '#ef4444', width: 2 }, data: [] },
            { name: '湿度', type: 'line', smooth: true, showSymbol: false, yAxisIndex: 1, lineStyle: { color: '#3b82f6', width: 2 }, data: [] },
            { name: '光照', type: 'line', smooth: true, showSymbol: false, lineStyle: { color: '#f59e0b', width: 2 }, data: [] }
        ]
    });
    refreshChartData();
    setInterval(refreshChartData, 10000);
}

async function refreshChartData() {
    if (!realChart) return;
    try {
        var ds = await apiGet('/api/devices');
        if (!ds.success || !ds.data.length) return;
        var did = ds.data[0].id;
        var d = await apiGet('/api/devices/' + did + '/data/all-recent?hours=2');
        if (!d.success) return;
        var td = (d.data.temperature || []).map(function (x) { return [parseTime(x.recorded_at), x.value]; });
        var hd = (d.data.humidity || []).map(function (x) { return [parseTime(x.recorded_at), x.value]; });
        var ld = (d.data.light || []).map(function (x) { return [parseTime(x.recorded_at), x.value]; });
        updateChartSeries(td, hd, ld);
    } catch (e) {}
}

function updateChartSeries(t, h, l) {
    if (!realChart) return;
    t = t || [];
    h = h || [];
    l = l || [];
    if (chartMode === 'all')
        realChart.setOption({ series: [{ data: t }, { data: h }, { data: l }] });
    else if (chartMode === 'temp')
        realChart.setOption({ series: [{ data: t }, { data: [] }, { data: [] }] });
    else if (chartMode === 'humi')
        realChart.setOption({ series: [{ data: [] }, { data: h }, { data: [] }] });
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
        // 核心修复：乱码�?替换为正常中文「数值」
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
    try {
        var t = await apiGet('/api/predictions/latest?type=temperature&predict_hours=6');
        var h = await apiGet('/api/predictions/latest?type=humidity&predict_hours=6');
        var th = (t.data.history || []).map(function (x) { return [parseTime(x.recorded_at), x.value]; });
        var tp = (t.data.predictions || []).map(function (x) { return [parseTime(x.predicted_at), x.predicted_value]; });
        var hh = (h.data.history || []).map(function (x) { return [parseTime(x.recorded_at), x.value]; });
        var hp = (h.data.predictions || []).map(function (x) { return [parseTime(x.predicted_at), x.predicted_value]; });
        predChart.setOption({ series: [{ data: th }, { data: tp }, { data: hh }, { data: hp }] });
    } catch (e) {}
}