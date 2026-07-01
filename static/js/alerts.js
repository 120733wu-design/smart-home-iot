var alertsData=[];
document.addEventListener('DOMContentLoaded',function(){
    loadAlerts();
    loadDevFilter();
    document.getElementById('btn-refresh-alerts').addEventListener('click',loadAlerts);
    document.getElementById('btn-mark-all-read').addEventListener('click',markAllRead);
    document.getElementById('filter-severity').addEventListener('change',filterAndRender);
    document.getElementById('filter-device').addEventListener('change',filterAndRender);
    document.getElementById('filter-read').addEventListener('change',filterAndRender)
});

async function loadAlerts(){
    try{
        var d=await apiGet('/api/alerts?per_page=100');
        if(d.success){
            alertsData=d.data;
            filterAndRender()
        }
    }catch(e){}
}

async function loadDevFilter(){
    try{
        var d=await apiGet('/api/devices');
        var sel=document.getElementById('filter-device');
        if(d.success)
            sel.innerHTML='<option value="">全部设备</option>'+d.data.map(function(x){
                return'<option value="'+x.id+'">'+escapeHtml(x.name)+'</option>'
            }).join('')
    }catch(e){}
}

function filterAndRender(){
    var sv=document.getElementById('filter-severity').value;
    var did=document.getElementById('filter-device').value;
    var ir=document.getElementById('filter-read').value;
    var f=alertsData;
    if(sv)f=f.filter(function(a){return a.severity===sv});
    if(did)f=f.filter(function(a){return String(a.device_id)===did});
    if(ir!=='')f=f.filter(function(a){return String(a.is_read)===ir});
    renderAlerts(f);
    document.getElementById('alert-count-badge').textContent='共 '+f.length+' 条'
}

// 重写时间格式化函数，强制东八区，消除8小时时差
function formatTime(rawStr) {
    // 拼接时区标识，告诉JS这是东八区时间
    const dt = new Date(rawStr + " +08:00");
    const year = dt.getFullYear();
    const month = String(dt.getMonth() + 1).padStart(2, '0');
    const day = String(dt.getDate()).padStart(2, '0');
    const hour = String(dt.getHours()).padStart(2, '0');
    const minute = String(dt.getMinutes()).padStart(2, '0');
    const second = String(dt.getSeconds()).padStart(2, '0');
    return `${year}/${month}/${day} ${hour}:${minute}:${second}`;
}

function renderAlerts(alerts){
    var tb=document.getElementById('alerts-table-body');
    if(!alerts.length){
        tb.innerHTML='<tr><td colspan="7" class="text-center text-muted py-4">暂无告警</td></tr>';
        return
    }
    tb.innerHTML=alerts.map(function(a, idx){
        var sl={
            critical:'<span class="badge badge-severity critical">严重</span>',
            warning:'<span class="badge badge-severity warning">警告</span>',
            info:'<span class="badge badge-severity info">信息</span>'
        };
        var tl={
            threshold:'阈值告警',
            disconnection:'设备断连',
            anomaly:'数据异常'
        };
        // 最新告警序号最大（从总数递减）
        var rowNum = alerts.length - idx;
        return'<tr class="'+(a.is_read?'':'fw-bold')+'"><td>'+rowNum+'</td><td>'+(sl[a.severity]||a.severity)+'</td><td>'+(escapeHtml(a.device_name)||'--')+'</td><td>'+(tl[a.alert_type]||a.alert_type)+'</td><td>'+escapeHtml(a.message)+'</td><td>'+formatTime(a.created_at)+'</td><td>'+(a.is_read?'<span class="text-muted small">已读</span>':'<button class="btn btn-sm btn-outline-success" onclick="markRead('+a.id+')">标记已读</button>')+'<button class="btn btn-sm btn-outline-danger ms-1" title="删除告警" aria-label="删除告警" onclick="deleteAlert('+a.id+')"><i class="bi bi-trash"></i></button></td></tr>'
    }).join('')
}

async function markRead(id){
    await apiPut('/api/alerts/'+id+'/read');
    loadAlerts();
    loadAlertBadge()
}

async function markAllRead(){
    var r=await apiPut('/api/alerts/read-all');
    if(r.success){
        showToast(r.message,'success');
        loadAlerts();
        loadAlertBadge()
    }
}

async function deleteAlert(id){
    if(!confirm('确定要删除这条告警吗？'))return;
    await apiDelete('/api/alerts/'+id);
    loadAlerts();
    loadAlertBadge()
}