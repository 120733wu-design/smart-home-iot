var gaugeTemp, gaugeHumi, gaugeLight, monitorLineChart = null, monitorTimer = null, currentDeviceId = null, currentSensor = 'temperature';
document.addEventListener('DOMContentLoaded', function () {
    loadDeviceSelect('monitor-device-select', function () {
        currentDeviceId = document.getElementById('monitor-device-select').value;
        initAll();
    });
    document.querySelectorAll('[data-sensor]').forEach(function (b) {
        b.addEventListener('click', function () {
            document.querySelectorAll('[data-sensor]').forEach(function (x) {
                x.classList.remove('active');
            });
            this.classList.add('active');
            currentSensor = this.dataset.sensor;
            updateLineChart();
        });
    });
    document.getElementById('monitor-device-select').addEventListener('change', function () {
        currentDeviceId = this.value;
        initAll();
    });
});

function loadDeviceSelect(sid, cb) {
    try {
        var d = apiGet('/api/devices');
        d.then(function (d) {
            var sel = document.getElementById(sid);
            if (d.success && d.data.length) {
                sel.innerHTML = d.data.map(function (x) {
                    return '<option value="' + x.id + '">' + x.name + ' (' + (x.location || '-') + ')</option>';
                }).join('');
                if (cb) cb();
            }
        })
    } catch (e) { }
}

function initAll() {
    if (!currentDeviceId) return;
    initGauges();
    initMonitorChart();
    startMonitorRefresh();
}

function initGauges() {
    var go = function (n, u, min, max, c) {
        return {
            series: [{
                type: 'gauge',
                min: min,
                max: max,
                axisLine: {
                    lineStyle: {
                        color: [[0.8, c], [1, '#dc3545']],
                        width: 8
                    }
                },
                axisLabel: { fontSize: 10 },
                detail: { formatter: '{value} ' + u, fontSize: 14 },
                data: [{ value: 0, name: n }]
            }]
        };
    };
    gaugeTemp = initChart('gauge-temp');
    gaugeHumi = initChart('gauge-humi');
    gaugeLight = initChart('gauge-light');
    if (gaugeTemp) gaugeTemp.setOption(go('温度', 'C', -10, 50, '#dc3545'));
    if (gaugeHumi) gaugeHumi.setOption(go('湿度', '%', 0, 100, '#0d6efd'));
    if (gaugeLight) gaugeLight.setOption(go('光照', 'lux', 0, 1000, '#ffc107'));
    updateGauges();
}

async function updateGauges() {
    if (!currentDeviceId) return;
    try {
        var d = await apiGet('/api/devices/' + currentDeviceId + '/data/realtime');
        if (d.success && d.data) d.data.forEach(function (r) {
            if (r.sensor_type === 'temperature' && gaugeTemp) {
                gaugeTemp.setOption({ series: [{ data: [{ value: r.value }] }] });
                document.getElementById('gauge-temp-time').textContent = formatTime(r.recorded_at)
            } else if (r.sensor_type === 'humidity' && gaugeHumi) {
                gaugeHumi.setOption({ series: [{ data: [{ value: r.value }] }] });
                document.getElementById('gauge-humi-time').textContent = formatTime(r.recorded_at)
            } else if (r.sensor_type === 'light' && gaugeLight) {
                gaugeLight.setOption({ series: [{ data: [{ value: r.value }] }] });
                document.getElementById('gauge-light-time').textContent = formatTime(r.recorded_at)
            }
        })
    } catch (e) { }
}

function initMonitorChart() {
    monitorLineChart = initChart('monitor-line-chart');
    if (!monitorLineChart) return;
    monitorLineChart.setOption({
        tooltip: {
            trigger: 'axis',
            confine: true,
            formatter: function (params) {
                var p = params[0];
                return formatTime(p.value[0]) + '<br/>' + p.marker + ' ' + p.seriesName + ': ' + p.value[1];
            }
        },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
            type: 'time',
            scale: false
        },
        yAxis: { type: 'value', name: '值' },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', bottom: 0, height: 18 }
        ],
        series: [{
            name: '',
            type: 'line',
            smooth: true,
            showSymbol: false,
            connectNulls: true,
            lineStyle: { width: 2 },
            markPoint: {
                data: [
                    { type: 'max', name: '最大值' },
                    { type: 'min', name: '最小值' }
                ]
            },
            data: []
        }]
    });
    updateLineChart();
}

async function updateLineChart() {
    if (!monitorLineChart || !currentDeviceId) return;
    try {
        var d = await apiGet('/api/devices/' + currentDeviceId + '/data/latest?type=' + currentSensor + '&hours=1');
        if (d.success) {
            var sd = d.data.map(function (x) {
                return [parseTime(x.recorded_at), x.value];
            });
            var sn = { temperature: '温度 (C)', humidity: '湿度 (%)', light: '光照 (lux)' };
            var cl = { temperature: '#dc3545', humidity: '#0d6efd', light: '#ffc107' };
            monitorLineChart.setOption({
                series: [{
                    name: sn[currentSensor] || '',
                    data: sd,
                    lineStyle: { color: cl[currentSensor] || '#0d6efd' }
                }],
                yAxis: { name: sn[currentSensor] || '' }
            })
        }
    } catch (e) { }
}

function startMonitorRefresh() {
    if (monitorTimer) clearInterval(monitorTimer);
    monitorTimer = setInterval(function () {
        var a = document.getElementById('auto-refresh');
        if (a && a.checked) {
            updateGauges();
            updateLineChart();
        }
    }, 10000)
}

// 工具：时间字符串转时间戳
function parseTime(timeStr) {
    return new Date(timeStr).getTime();
}

// 工具：时间格式化
function formatTime(timestamp) {
    let d = new Date(timestamp);
    let y = d.getFullYear();
    let m = String(d.getMonth() + 1).padStart(2, '0');
    let day = String(d.getDate()).padStart(2, '0');
    let h = String(d.getHours()).padStart(2, '0');
    let min = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day} ${h}:${min}`;
}

// 初始化ECharts容器
function initChart(domId) {
    const dom = document.getElementById(domId);
    if (!dom) return null;
    return echarts.init(dom);
}

// 窗口自适应
window.addEventListener('resize', function () {
    if (gaugeTemp) gaugeTemp.resize();
    if (gaugeHumi) gaugeHumi.resize();
    if (gaugeLight) gaugeLight.resize();
    if (monitorLineChart) monitorLineChart.resize();
});