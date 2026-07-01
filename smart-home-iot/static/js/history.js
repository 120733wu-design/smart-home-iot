var historyChart = null, currentDeviceId = null;
document.addEventListener('DOMContentLoaded', function () {
    loadDevSel('hist-device', function () {
        currentDeviceId = document.getElementById('hist-device').value;
        setQuickTime(24);
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
    // 移除传感器类型下拉切换查询逻辑，双曲线不再使用
    document.getElementById('hist-type').removeEventListener('change', queryHistory);
});

// 快捷时间赋值
function setQuickTime(h) {
    var n = new Date();
    var s = new Date(n.getTime() - h * 3600000);
    document.getElementById('hist-start').value = fdt(s);
    document.getElementById('hist-end').value = fdt(n);
    if (currentDeviceId) queryHistory();
}

// 格式化datetime-local时间
function fdt(d) {
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    var h = String(d.getHours()).padStart(2, '0');
    var min = String(d.getMinutes()).padStart(2, '0');
    return y + '-' + m + '-' + day + 'T' + h + ':' + min;
}

// 统一查询：同时获取温度、湿度两套数据
async function queryHistory() {
    if (!currentDeviceId) return;
    var st = document.getElementById('hist-start').value;
    var en = document.getElementById('hist-end').value;
    document.getElementById('history-chart-title').textContent = '温湿度历史曲线';
    try {
        // 并行请求温度、湿度数据
        const [tempRes, humiRes] = await Promise.all([
            apiGet('/api/devices/' + currentDeviceId + '/data?type=temperature&start=' + st + '&end=' + en + '&per_page=1000'),
            apiGet('/api/devices/' + currentDeviceId + '/data?type=humidity&start=' + st + '&end=' + en + '&per_page=1000')
        ]);
        const tempData = tempRes.success ? tempRes.data : [];
        const humiData = humiRes.success ? humiRes.data : [];
        const totalCount = tempRes.total + humiRes.total;
        document.getElementById('history-data-count').textContent = '共 ' + totalCount + ' 条数据';
        updateChart(tempData, humiData);
    } catch (e) {
        console.error('查询历史失败', e);
    }
}

// 渲染双轴图表 + 计算最值填充统计栏
function updateChart(tempRaw, humiRaw) {
    historyChart = initChart('history-chart');
    if (!historyChart) return;

    // 排序并格式化 [时间戳, 数值]
    const tempSorted = (tempRaw || []).sort((a, b) => parseTime(a.recorded_at) - parseTime(b.recorded_at));
    const humiSorted = (humiRaw || []).sort((a, b) => parseTime(a.recorded_at) - parseTime(b.recorded_at));
    const tempSeries = tempSorted.map(d => [parseTime(d.recorded_at), d.value]);
    const humiSeries = humiSorted.map(d => [parseTime(d.recorded_at), d.value]);

    // 计算温湿度最大最小值
    let tempArr = tempSeries.map(i => i[1]);
    let humiArr = humiSeries.map(i => i[1]);
    let tempMax = tempArr.length ? Math.max(...tempArr).toFixed(1) : '--';
    let tempMin = tempArr.length ? Math.min(...tempArr).toFixed(1) : '--';
    let humiMax = humiArr.length ? Math.max(...humiArr).toFixed(1) : '--';
    let humiMin = humiArr.length ? Math.min(...humiArr).toFixed(1) : '--';
    // 填充顶部统计卡片
    document.getElementById('stat-temp-max').textContent = tempMax + '°C';
    document.getElementById('stat-temp-min').textContent = tempMin + '°C';
    document.getElementById('stat-humi-max').textContent = humiMax + '%';
    document.getElementById('stat-humi-min').textContent = humiMin + '%';

    const option = {
        tooltip: {
            trigger: 'axis',
            confine: true,
            formatter: function (params) {
                let time = formatTime(params[0].value[0]);
                let str = time + '<br/>';
                params.forEach(item => {
                    str += item.marker + ' ' + item.seriesName + ': ' + item.value[1] + (item.seriesName === '温度 (°C)' ? '°C' : '%') + '<br/>';
                });
                return str;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '8%',
            containLabel: true
        },
        xAxis: {
            type: 'time',
            scale: false // 完整展示所选区间，不自动截取局部
        },
        yAxis: [
            {
                type: 'value',
                name: '温度 (°C)',
                position: 'left',
                axisLine: { lineStyle: { color: '#dc3545' } }
            },
            {
                type: 'value',
                name: '湿度 (%)',
                position: 'right',
                axisLine: { lineStyle: { color: '#0d6efd' } }
            }
        ],
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', bottom: 0, height: 20 }
        ],
        series: [
            {
                name: '温度 (°C)',
                type: 'line',
                yAxisIndex: 0,
                smooth: true,
                showSymbol: false,
                connectNulls: true, // 缺失数据延续，消除断崖
                lineStyle: { color: '#dc3545', width: 2 },
                areaStyle: { color: '#dc3545', opacity: 0.1 },
                data: tempSeries,
                markPoint: {
                    data: [
                        { type: 'max', name: '最高温' },
                        { type: 'min', name: '最低温' }
                    ]
                }
            },
            {
                name: '湿度 (%)',
                type: 'line',
                yAxisIndex: 1,
                smooth: true,
                showSymbol: false,
                connectNulls: true,
                lineStyle: { color: '#0d6efd', width: 2 },
                areaStyle: { color: '#0d6efd', opacity: 0.1 },
                data: humiSeries,
                markPoint: {
                    data: [
                        { type: 'max', name: '最高湿' },
                        { type: 'min', name: '最低湿' }
                    ]
                }
            }
        ]
    };
    historyChart.setOption(option);
    historyChart.resize();
}

// 加载设备下拉选项
function loadDevSel(sid, cb) {
    apiGet('/api/devices').then(function (d) {
        var sel = document.getElementById(sid);
        if (d.success && d.data.length) {
            sel.innerHTML = d.data.map(function (x) {
                return '<option value="' + x.id + '">' + x.name + ' (' + (x.location || '-') + ')</option>';
            }).join('');
            if (cb) cb();
        }
    });
}

// 窗口自适应缩放
window.addEventListener('resize', function () {
    if (historyChart) historyChart.resize();
});

// 工具：时间字符串转时间戳
function parseTime(timeStr) {
    return new Date(timeStr).getTime();
}

// 工具：时间戳格式化tooltip显示
function formatTime(timestamp) {
    let d = new Date(timestamp);
    let y = d.getFullYear();
    let m = String(d.getMonth() + 1).padStart(2, '0');
    let day = String(d.getDate()).padStart(2, '0');
    let h = String(d.getHours()).padStart(2, '0');
    let min = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day} ${h}:${min}`;
}

// 初始化echarts图表容器
function initChart(domId) {
    const dom = document.getElementById(domId);
    if (!dom) return null;
    if (historyChart) historyChart.dispose();
    return echarts.init(dom);
}