var predictionChart = null;
document.addEventListener('DOMContentLoaded', function () {
    loadDevSel('pred-device', function () {
        loadPredictionData();
        loadMetrics();
    });
    document.getElementById('btn-run-prediction').addEventListener('click', runPrediction);
    document.getElementById('pred-device').addEventListener('change', function () {
        if (this.value) {
            loadPredictionData();
            loadMetrics();
        }
    });
    document.getElementById('pred-type').addEventListener('change', loadPredictionData);
    document.getElementById('pred-model').addEventListener('change', function () {
        loadPredictionData();
        loadMetrics();
    });
    document.getElementById('pred-hours').addEventListener('change', loadPredictionData);
    // 每分钟自动刷新
    setInterval(loadPredictionData, 60000);
});

function getModelType() {
    return document.getElementById('pred-model').value || 'linear_regression';
}

// 统一时区修复：数据库时间字符串强制东八区CST
function getCSTDate(rawStr) {
    return new Date(rawStr + " +08:00");
}

// 加载设备下拉
function loadDevSel(sid, cb) {
    apiGet('/api/devices').then(function (d) {
        var sel = document.getElementById(sid);
        if (d.success && d.data.length) {
            sel.innerHTML = d.data.map(function (x) {
                return '<option value="' + x.id + '">' + x.name + ' (' + (x.location || '-') + ')</option>';
            }).join('');
            if (cb) cb();
        }
    })
}

// 手动生成预测
async function runPrediction() {
    var btn = document.getElementById('btn-run-prediction');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>预测中...';
    try {
        var did = document.getElementById('pred-device').value;
        var mt = getModelType();
        var r = await apiPost('/api/predictions/generate', {
            device_id: did ? parseInt(did) : null,
            model_type: mt
        });
        if (r.success) {
            showToast('预测完成 (' + (mt === 'random_forest' ? '随机森林' : '线性回归') + ')', 'success');
            loadPredictionData();
            loadMetrics();
        } else {
            showToast(r.message, 'error');
        }
    } catch (e) {
        showToast('预测请求失败', 'error');
    }
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-lightning-charge me-1"></i>运行预测';
}

// 加载历史+预测曲线数据
async function loadPredictionData() {
    var did = document.getElementById('pred-device').value;
    if (!did) return;
    var ty = document.getElementById('pred-type').value;
    var h = document.getElementById('pred-hours').value;
    var mt = getModelType();
    try {
        var d = await apiGet('/api/predictions/latest?device_id=' + did + '&type=' + ty + '&history_hours=6&predict_hours=' + h + '&model_type=' + mt);
        if (!d.success) return;
        updateChart(d.data, ty);
        updateTable(d.data.predictions);
    } catch (e) { }
}

// 填充空白时间插值，消除断层
function fillHistoryGaps(data, intervalMs) {
    if (!data || data.length < 2) return data;
    var r = [data[0]];
    for (var i = 1; i < data.length; i++) {
        var g = data[i][0] - data[i - 1][0];
        if (g > intervalMs * 1.5) {
            r.push([data[i - 1][0] + intervalMs, data[i - 1][1]]);
        }
        r.push(data[i]);
    }
    return r;
}

// 渲染预测图表
function updateChart(data, ty) {
    predictionChart = initChart('prediction-chart');
    if (!predictionChart) return;

    // 历史数据格式化，5分钟间隔补间隙
    var hd = fillHistoryGaps((data.history || []).map(function (d) {
        return [parseTime(d.recorded_at), d.value]
    }), 5 * 60 * 1000);
    var pd = (data.predictions || []).map(function (d) {
        return [parseTime(d.predicted_at), d.predicted_value]
    });

    var sn = { temperature: '温度 (C)', humidity: '湿度 (%)' };
    var cl = { temperature: '#dc3545', humidity: '#0d6efd' };

    predictionChart.setOption({
        tooltip: {
            trigger: 'axis',
            confine: true,
            formatter: function (params) {
                let time = formatTime(params[0].value[0]);
                let str = time + '<br/>';
                params.forEach(item => {
                    str += item.marker + ' ' + item.seriesName + ': ' + item.value[1] + (ty === 'temperature' ? '°C' : '%') + '<br/>';
                });
                return str;
            }
        },
        legend: {
            data: ['历史数据', '预测数据']
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'time',
            scale: false // 完整展示所选区间，不自动截取局部时段
        },
        yAxis: {
            type: 'value',
            name: sn[ty] || ''
        },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', bottom: 0, height: 20 }
        ],
        series: [
            {
                name: '历史数据',
                type: 'line',
                smooth: true,
                showSymbol: false,
                connectNulls: true, // 缺失数据延续，消除断崖
                lineStyle: { color: cl[ty] || '#0d6efd', width: 2 },
                areaStyle: { color: cl[ty] || '#0d6efd', opacity: 0.1 },
                data: hd
            },
            {
                name: '预测数据',
                type: 'line',
                smooth: true,
                showSymbol: true,
                symbol: 'circle',
                symbolSize: 6,
                connectNulls: true,
                lineStyle: { color: '#198754', width: 2, type: 'dashed' },
                areaStyle: { color: '#198754', opacity: 0.08 },
                data: pd
            }
        ]
    });
    predictionChart.resize();
}

// 预测表格渲染
function updateTable(p) {
    var tb = document.getElementById('prediction-table-body');
    if (!p || !p.length) {
        tb.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">暂无预测数据</td></tr>';
        return
    }
    tb.innerHTML = p.map(function (x) {
        return '<tr><td>' + formatTime(x.predicted_at) + '</td><td><strong>' + x.predicted_value + '</strong></td><td>' + (x.confidence ? x.confidence + '%' : '--') + '</td><td>' + (x.created_at ? formatTime(x.created_at) : '--') + '</td></tr>'
    }).join('')
}

// 加载模型精度指标
async function loadMetrics() {
    var did = document.getElementById('pred-device').value;
    if (!did) return;
    var mt = getModelType();
    try {
        var d = await apiGet('/api/predictions/accuracy?device_id=' + did + '&model_type=' + mt);
        if (!d.success) return;
        var m = d.data.temperature;
        document.getElementById('metric-rmse').textContent = m ? m.rmse : '--';
        document.getElementById('metric-mae').textContent = m ? m.mae : '--';
        document.getElementById('metric-r2').textContent = m ? m.r2 : '--';
        document.getElementById('metric-model-type').textContent = mt === 'random_forest' ? '(随机森林)' : '(线性回归)';
    } catch (e) { }
}

// 窗口自适应
window.addEventListener('resize', function () {
    if (predictionChart) predictionChart.resize();
});

// ---------------------- 全局通用工具函数（修复时区） ----------------------
// 时间字符串转时间戳（强制东八区）
function parseTime(timeStr) {
    return getCSTDate(timeStr).getTime();
}

// 时间戳格式化输出页面展示文本
function formatTime(timestamp) {
    let d = new Date(timestamp);
    let y = d.getFullYear();
    let m = String(d.getMonth() + 1).padStart(2, '0');
    let day = String(d.getDate()).padStart(2, '0');
    let h = String(d.getHours()).padStart(2, '0');
    let min = String(d.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${day} ${h}:${min}`;
}

// ECharts容器初始化
function initChart(domId) {
    const dom = document.getElementById(domId);
    if (!dom) return null;
    if (predictionChart) predictionChart.dispose();
    return echarts.init(dom);
}