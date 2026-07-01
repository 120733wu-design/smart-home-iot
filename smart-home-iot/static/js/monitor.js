var gaugeTemp, gaugeHumi, gaugeLight, gaugeOutTemp, gaugeOutHumi, monitorLineChart = null, monitorTimer = null, currentDeviceId = null, currentSensor = 'temperature';
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

// 统一时区修复函数（全局复用，消除8小时时差）
function getCSTDate(rawStr) {
    return new Date(rawStr + " +08:00");
}

function loadDeviceSelect(sid, cb) {
    try {
        var d = apiGet('/api/devices');
        d.then(function (d) {
            var sel = document.getElementById(sid);
            if (d.success && d.data.length) {
                sel.innerHTML = d.data.map(function (x) {
                    return '<option value="' + x.id + '">' + x.name + ' (' + (x.location || '-') + ')</option>';
                }).join('');
                // 自动选中 sensor 设备（优先 device_key='sensor'）
                var sensorDev = d.data.find(function(x) { return x.device_key === 'sensor'; });
                if (!sensorDev) sensorDev = d.data.find(function(x) { return x.type === 'sensor'; });
                if (sensorDev) sel.value = sensorDev.id;
                else if (_sensorDeviceId) sel.value = _sensorDeviceId;
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
    // 首次加载室外天气
    updateOutdoorWeather();
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
    // 室内仪表
    gaugeTemp = initChart('gauge-temp');
    gaugeHumi = initChart('gauge-humi');
    gaugeLight = initChart('gauge-light');
    // 室外仪表
    gaugeOutTemp = initChart('gauge-out-temp');
    gaugeOutHumi = initChart('gauge-out-humi');

    if (gaugeTemp) gaugeTemp.setOption(go('温度', 'C', -10, 50, '#dc3545'));
    if (gaugeHumi) gaugeHumi.setOption(go('湿度', '%', 0, 100, '#0d6efd'));
    if (gaugeLight) gaugeLight.setOption(go('光照', 'lux', 0, 1000, '#ffc107'));
    if (gaugeOutTemp) gaugeOutTemp.setOption(go('室外温度', 'C', -10, 50, '#22c55e'));
    if (gaugeOutHumi) gaugeOutHumi.setOption(go('室外湿度', '%', 0, 100, '#f97316'));
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

// 新增：加载室外天气接口，更新室外仪表盘
async function updateOutdoorWeather() {
    try {
        var res = await apiGet('/api/weather/outdoor?city=' + encodeURIComponent('天津'));
        if (!res.success) {
            document.getElementById('out-weather-desc').innerText = '获取天气失败：' + res.msg;
            return;
        }
        // 更新室外仪表盘数值
        if (gaugeOutTemp) gaugeOutTemp.setOption({ series: [{ data: [{ value: res.out_temp }] }] });
        if (gaugeOutHumi) gaugeOutHumi.setOption({ series: [{ data: [{ value: res.out_humi }] }] });
        // 更新文字信息
        document.getElementById('out-temp-val').innerText = res.out_temp;
        document.getElementById('out-humi-val').innerText = res.out_humi;
        document.getElementById('out-weather-desc').innerText = res.weather_text;
        document.getElementById('out-weather-time').innerText = res.update_time;
    } catch (err) {
        console.error('室外天气加载失败', err);
    }
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
            updateOutdoorWeather(); // 自动刷新同步更新室外天气
        }
    }, 10000)
}

// 工具：时间字符串转时间戳（修复时区）
function parseTime(timeStr) {
    return getCSTDate(timeStr).getTime();
}

// 工具：时间格式化（修复时区）
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

// 窗口自适应（新增室外图表resize）
window.addEventListener('resize', function () {
    if (gaugeTemp) gaugeTemp.resize();
    if (gaugeHumi) gaugeHumi.resize();
    if (gaugeLight) gaugeLight.resize();
    if (gaugeOutTemp) gaugeOutTemp.resize();
    if (gaugeOutHumi) gaugeOutHumi.resize();
    if (monitorLineChart) monitorLineChart.resize();
});