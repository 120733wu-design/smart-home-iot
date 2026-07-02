/**
 * 用户管理 - admin_users.js
 * 用户列表展示、角色修改、密码重置、账号删除
 */
(function () {
    'use strict';

    let currentEditUserId = null;
    let roleModal = null;
    let deleteModal = null;

    // ========== 初始化 ==========
    function init() {
        roleModal = new bootstrap.Modal(document.getElementById('roleModal'));
        deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
        loadUsers();

        document.getElementById('btn-refresh').addEventListener('click', loadUsers);
        document.getElementById('btn-confirm-role').addEventListener('click', confirmRoleChange);
        document.getElementById('btn-confirm-delete').addEventListener('click', confirmDelete);
    }

    // ========== 加载用户列表 ==========
    async function loadUsers() {
        try {
            const res = await apiGet('/api/admin/users');
            if (!res.success) {
                showToast('加载用户列表失败: ' + (res.message || '权限不足'), 'danger');
                return;
            }
            renderStats(res.data);
            renderTable(res.data);
        } catch (e) {
            console.error('加载用户列表失败:', e);
            showToast('网络错误', 'danger');
        }
    }

    // ========== 统计卡片 ==========
    function renderStats(users) {
        document.getElementById('stat-total').textContent = users.length;
        const admins = users.filter(function (u) { return u.role === 'admin'; });
        document.getElementById('stat-admin').textContent = admins.length;
        document.getElementById('stat-user').textContent = users.length - admins.length;
    }

    // ========== 渲染表格 ==========
    function renderTable(users) {
        const tbody = document.getElementById('user-table-body');
        if (!users.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">暂无用户</td></tr>';
            return;
        }

        let html = '';
        users.forEach(function (u, idx) {
            const roleBadge = u.role === 'admin'
                ? '<span class="badge bg-danger">管理员</span>'
                : '<span class="badge bg-secondary">普通用户</span>';
            const faceStatus = u.face_enabled
                ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>已录入</span>'
                : '<span class="badge bg-light text-muted"><i class="bi bi-dash-circle me-1"></i>未录入</span>';
            const isSelf = u.id === (window._currentUserId || 0);

            html += '<tr>';
            html += '<td class="ps-4 fw-bold text-muted">' + (idx + 1) + '</td>';
            html += '<td><span class="fw-bold">' + escapeHtml(u.username) + '</span>' + (isSelf ? ' <small class="text-muted">(当前)</small>' : '') + '</td>';
            html += '<td>' + roleBadge + '</td>';
            html += '<td>' + faceStatus + '</td>';
            html += '<td class="small text-muted">' + (u.created_at_str || '-') + '</td>';
            html += '<td class="text-end pe-4">';
            html += '<div class="btn-group btn-group-sm">';

            // 角色切换按钮
            html += '<button class="btn btn-outline-warning btn-change-role" data-user-id="' + u.id + '" data-username="' + escapeHtml(u.username) + '" data-role="' + u.role + '" title="修改角色">';
            html += '<i class="bi bi-person-badge"></i>';
            html += '</button> ';

            // 密码重置按钮
            html += '<button class="btn btn-outline-info btn-reset-pwd" data-user-id="' + u.id + '" data-username="' + escapeHtml(u.username) + '" title="重置密码">';
            html += '<i class="bi bi-key"></i>';
            html += '</button> ';

            // 删除按钮（不允许删除自己或最后一个admin）
            if (!isSelf) {
                html += '<button class="btn btn-outline-danger btn-delete" data-user-id="' + u.id + '" data-username="' + escapeHtml(u.username) + '" data-role="' + u.role + '" title="删除用户">';
                html += '<i class="bi bi-trash"></i>';
                html += '</button>';
            }

            html += '</div></td></tr>';
        });
        tbody.innerHTML = html;

        // 绑定事件
        tbody.querySelectorAll('.btn-change-role').forEach(function (btn) {
            btn.addEventListener('click', function () {
                openRoleModal(this.dataset.userId, this.dataset.username, this.dataset.role);
            });
        });
        tbody.querySelectorAll('.btn-reset-pwd').forEach(function (btn) {
            btn.addEventListener('click', function () {
                resetPassword(this.dataset.userId, this.dataset.username);
            });
        });
        tbody.querySelectorAll('.btn-delete').forEach(function (btn) {
            btn.addEventListener('click', function () {
                openDeleteModal(this.dataset.userId, this.dataset.username);
            });
        });
    }

    // ========== 角色修改 ==========
    function openRoleModal(userId, username, currentRole) {
        currentEditUserId = userId;
        document.getElementById('role-username').textContent = username;
        document.getElementById('role-select').value = currentRole;
        roleModal.show();
    }

    async function confirmRoleChange() {
        const newRole = document.getElementById('role-select').value;
        try {
            const res = await apiPut('/api/admin/users/' + currentEditUserId + '/role', { role: newRole });
            if (res.success) {
                showToast(res.message, 'success');
                roleModal.hide();
                loadUsers();
            } else {
                showToast(res.message || '修改失败', 'danger');
            }
        } catch (e) {
            showToast('网络错误', 'danger');
        }
    }

    // ========== 密码重置 ==========
    async function resetPassword(userId, username) {
        if (!confirm('确定要将用户 ' + username + ' 的密码重置为 123456 吗？')) return;
        try {
            const res = await apiPost('/api/admin/users/' + userId + '/reset-password');
            if (res.success) {
                showToast(res.message, 'success');
            } else {
                showToast(res.message || '重置失败', 'danger');
            }
        } catch (e) {
            showToast('网络错误', 'danger');
        }
    }

    // ========== 删除用户 ==========
    function openDeleteModal(userId, username) {
        currentEditUserId = userId;
        document.getElementById('delete-username').textContent = username;
        deleteModal.show();
    }

    async function confirmDelete() {
        try {
            const res = await apiDelete('/api/admin/users/' + currentEditUserId);
            if (res.success) {
                showToast(res.message, 'success');
                deleteModal.hide();
                loadUsers();
            } else {
                showToast(res.message || '删除失败', 'danger');
            }
        } catch (e) {
            showToast('网络错误', 'danger');
        }
    }

    init();
})();
