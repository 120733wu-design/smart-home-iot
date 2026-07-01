var devicesData=[];
document.addEventListener('DOMContentLoaded',function(){
    loadDevices();
    document.getElementById('search-device').addEventListener('input',filterDevices);
    document.getElementById('filter-status').addEventListener('change',filterDevices);
    document.getElementById('filter-type').addEventListener('change',filterDevices);
    document.getElementById('btn-refresh-devices').addEventListener('click',loadDevices);
    document.getElementById('btn-save-device').addEventListener('click',saveDevice);
    document.getElementById('deviceModal').addEventListener('show.bs.modal',function(){
        document.getElementById('deviceModalLabel').textContent='新增设备';
        document.getElementById('edit-device-id').value='';
        document.getElementById('edit-name').value='';
        document.getElementById('edit-key').value='';
        document.getElementById('edit-type').value='sensor';
        document.getElementById('edit-location').value=''
    })
});

async function loadDevices(){
    try{
        var d=await apiGet('/api/devices');
        if(d.success){
            devicesData=d.data;
            renderDevices(devicesData)
        }
    }catch(e){
        document.getElementById('devices-table-body').innerHTML='<tr><td colspan="8" class="text-center text-danger">加载失败</td></tr>'
    }
}

function renderDevices(devs){
    var tb=document.getElementById('devices-table-body');
    if(!devs.length){
        tb.innerHTML='<tr><td colspan="8" class="text-center text-muted py-4">暂无设备</td></tr>';
        return
    }
    tb.innerHTML=devs.map(function(d){
        var sd='<span class="status-dot '+d.status+'"></span>';
        var tl={
            sensor:'传感器',
            actuator:'执行器',
            hybrid:'混合设备'
        };
        return'<tr><td>'+d.id+'</td><td><strong>'+escapeHtml(d.name)+'</strong></td><td><code>'+escapeHtml(d.device_key)+'</code></td><td>'+(tl[d.type]||d.type)+'</td><td>'+(d.location||'-')+'</td><td>'+sd+d.status+'</td><td>'+formatTime(d.created_at)+'</td><td><button class="btn btn-sm btn-outline-primary me-1" title="编辑设备" aria-label="编辑设备" onclick="editDevice('+d.id+')"><i class="bi bi-pencil"></i></button><button class="btn btn-sm btn-outline-danger" title="删除设备" aria-label="删除设备" onclick="deleteDevice('+d.id+')"><i class="bi bi-trash"></i></button></td></tr>'
    }).join('')
}

function filterDevices(){
    var s=document.getElementById('search-device').value.toLowerCase();
    var st=document.getElementById('filter-status').value;
    var ty=document.getElementById('filter-type').value;
    renderDevices(devicesData.filter(function(d){
        return(!s||d.name.toLowerCase().includes(s)||d.device_key.toLowerCase().includes(s))&&(!st||d.status===st)&&(!ty||d.type===ty)
    }))
}

function editDevice(id){
    var d=devicesData.find(function(x){return x.id===id});
    if(!d)return;
    document.getElementById('deviceModalLabel').textContent='编辑设备';
    document.getElementById('edit-device-id').value=d.id;
    document.getElementById('edit-name').value=d.name;
    document.getElementById('edit-key').value=d.device_key;
    document.getElementById('edit-type').value=d.type;
    document.getElementById('edit-location').value=d.location||'';
    new bootstrap.Modal(document.getElementById('deviceModal')).show()
}

async function saveDevice(){
    var id=document.getElementById('edit-device-id').value;
    var data={
        name:document.getElementById('edit-name').value,
        device_key:document.getElementById('edit-key').value,
        type:document.getElementById('edit-type').value,
        location:document.getElementById('edit-location').value
    };
    if(!data.name||!data.device_key){
        showToast('设备名称和设备key不能为空','error');
        return
    }
    try{
        var r=id?await apiPut('/api/devices/'+id,data):await apiPost('/api/devices',data);
        if(r.success){
            showToast(r.message,'success');
            bootstrap.Modal.getInstance(document.getElementById('deviceModal')).hide();
            loadDevices()
        }else showToast(r.message,'error')
    }catch(e){
        showToast('操作失败','error')
    }
}

async function deleteDevice(id){
    if(!confirm('确定要删除该设备吗？'))return;
    try{
        var r=await apiDelete('/api/devices/'+id);
        if(r.success){
            showToast('设备已删除','success');
            loadDevices()
        }else showToast(r.message,'error')
    }catch(e){
        showToast('删除失败','error')
    }
}