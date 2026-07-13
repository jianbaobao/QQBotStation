"""
Web管理页面HTML模板 - 普通字符串，无Python f-string冲突
所有JS模板字面量使用原生JS语法
"""
ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QQBotStation 管理面板</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Microsoft YaHei','Segoe UI',sans-serif; background:#1a1b2e; color:#e0e0e0; }
.header { background:#141526; padding:16px 24px; border-bottom:1px solid #2a2b3e; display:flex; align-items:center; }
.header h1 { font-size:18px; color:#c8c8d4; }
.header .status { margin-left:auto; font-size:13px; padding:4px 12px; border-radius:12px; }
.status.online { background:#1b3a1b; color:#4caf50; }
.container { display:flex; min-height:calc(100vh - 56px); }
.sidebar { width:180px; background:#141526; border-right:1px solid #2a2b3e; padding:8px 0; }
.sidebar a { display:block; padding:10px 20px; color:#8888a0; text-decoration:none; font-size:13px; }
.sidebar a:hover { background:#2a2b3e; color:#c8c8d4; }
.sidebar a.active { background:#3a3b5e; color:#7c7cf0; border-left:3px solid #5c5cf0; }
.content { flex:1; padding:24px; overflow-y:auto; }
.card { background:#1e1f32; border:1px solid #2a2b3e; border-radius:8px; padding:16px; margin-bottom:16px; }
.card h2 { font-size:15px; color:#c8c8d4; margin-bottom:12px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th,td { padding:8px 12px; text-align:left; border-bottom:1px solid #2a2b3e; }
th { color:#9c9cb0; font-weight:600; }
.btn { display:inline-block; padding:4px 12px; border:none; border-radius:4px; cursor:pointer; font-size:12px; }
.btn-primary { background:#5c5cf0; color:white; }
.btn-danger { background:#d94a4a; color:white; }
.btn-sm { padding:2px 8px; font-size:11px; }
input,select,textarea { background:#141526; border:1px solid #2a2b3e; border-radius:4px; padding:6px 10px; color:#e0e0e0; width:100%; margin:4px 0; }
.form-row { display:flex; gap:12px; margin:8px 0; }
.form-row > div { flex:1; }
label { display:block; color:#9c9cb0; font-size:12px; margin:4px 0; }
.stats { display:grid; grid-template-columns:repeat(auto-fit, minmax(140px,1fr)); gap:12px; }
.stat-card { background:#141526; border-radius:8px; padding:16px; text-align:center; }
.stat-card .num { font-size:28px; font-weight:700; color:#5c5cf0; }
.stat-card .label { font-size:12px; color:#6a6a80; margin-top:4px; }
</style>
</head>
<body>
<div class="header">
  <h1>&#x1F916; QQBotStation &#xB7; &#x7BA1;&#x7406;&#x9762;&#x677F;</h1>
  <span class="status online" id="statusBadge">&#x25CF; &#x8FD0;&#x884C;&#x4E2D;</span>
</div>
<div class="container">
  <div class="sidebar">
    <a href="#" class="active" onclick="showPage('overview')">&#x1F4CA; &#x6982;&#x89C8;</a>
    <a href="#" onclick="showPage('tasks')">&#x1F4AC; QQ&#x4EFB;&#x52A1;</a>
    <a href="#" onclick="showPage('sites')">&#x1F310; &#x7B7E;&#x5230;&#x7AD9;&#x70B9;</a>
    <a href="#" onclick="showPage('history')">&#x1F4CB; &#x6267;&#x884C;&#x5386;&#x53F2;</a>
  </div>
  <div class="content" id="pageContent">
    <div id="page-overview"></div>
    <div id="page-tasks" style="display:none"></div>
    <div id="page-sites" style="display:none"></div>
    <div id="page-history" style="display:none"></div>
  </div>
</div>
<script>
const BASE = '';
async function api(path, opts) {
  opts = opts || {};
  const r = await fetch(BASE+path, {
    headers: {'Content-Type':'application/json'},
    method: opts.method || 'GET',
    body: opts.body ? JSON.stringify(opts.body) : undefined
  });
  return r.json();
}
function qs(id) { return document.getElementById(id); }
function showPage(name) {
  document.querySelectorAll('.content > div').forEach(function(d){ d.style.display='none'; });
  var el = qs('page-'+name);
  if (el) el.style.display = 'block';
  document.querySelectorAll('.sidebar a').forEach(function(a){ a.classList.remove('active'); });
  if (event && event.target) event.target.classList.add('active');
  if (name==='overview') loadOverview();
  else if (name==='tasks') loadTasks();
  else if (name==='sites') loadSites();
  else if (name==='history') loadHistory();
}
function esc(s) { return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function loadOverview() {
  var stat = await api('/api/status');
  var s = stat.stats || {};
  var qq = await api('/api/qq/status');
  qs('page-overview').innerHTML =
    '<div class="stats">' +
      '<div class="stat-card"><div class="num">'+(s.tasks_total||0)+'</div><div class="label">总任务</div></div>' +
      '<div class="stat-card"><div class="num">'+(s.tasks_enabled||0)+'</div><div class="label">运行中</div></div>' +
      '<div class="stat-card"><div class="num">'+(s.sites_total||0)+'</div><div class="label">签到站点</div></div>' +
      '<div class="stat-card"><div class="num">'+(s.history_total||0)+'</div><div class="label">执行记录</div></div>' +
      '<div class="stat-card"><div class="num">'+(qq.running?'\u2705':'\u274C')+'</div><div class="label">QQ状态</div></div>' +
      '<div class="stat-card"><div class="num">'+Math.round((stat.stats?.db_size||0)/1024)+'KB</div><div class="label">数据库</div></div>' +
    '</div>' +
    '<div class="card" style="margin-top:16px"><h2>系统信息</h2>' +
      '<p>平台: '+esc(stat.platform)+' | 版本: '+esc(stat.version)+' | 时间: '+esc(stat.time)+'</p></div>';
}
async function loadTasks() {
  var r = await api('/api/tasks');
  var tasks = r.tasks || [];
  var html = '<div class="card"><h2>QQ消息任务</h2><table><tr><th>名称</th><th>消息</th><th>群数</th><th>调度</th><th>状态</th><th>操作</th></tr>';
  for (var i=0;i<tasks.length;i++) {
    var t = tasks[i];
    var groups = t.groups||[];
    html += '<tr><td>'+esc(t.name)+'</td><td>'+esc((t.message||'').substring(0,20))+'</td><td>'+groups.length+'</td><td>'+esc(JSON.stringify(t.schedule||{}))+'</td><td>'+(t.enabled?'\u2705':'\u23F8')+'</td>' +
      '<td><button class="btn btn-primary btn-sm" onclick="execTask(\''+t.id+'\')">\u25B6</button> ' +
      '<button class="btn btn-sm" onclick="toggleTask(\''+t.id+'\')">'+(t.enabled?'\u23F8':'\u25B6')+'</button> ' +
      '<button class="btn btn-danger btn-sm" onclick="delTask(\''+t.id+'\')">\u2715</button></td></tr>';
  }
  html += '</table></div>';
  html += '<div class="card"><h2>新建任务</h2>' +
    '<div class="form-row"><div><label>名称</label><input id="tname" placeholder="任务名称"></div>' +
    '<div><label>时间</label><input id="ttime" value="09:00"></div></div>' +
    '<div><label>目标群（每行一个）</label><textarea id="tgroups" rows="2"></textarea></div>' +
    '<div><label>消息内容</label><textarea id="tmsg" rows="2"></textarea></div>' +
    '<button class="btn btn-primary" onclick="createTask()">创建任务</button></div>';
  qs('page-tasks').innerHTML = html;
}
async function execTask(id) { await api('/api/tasks/'+id+'/execute',{method:'POST'}); alert('已触发执行'); }
async function toggleTask(id) { await api('/api/tasks/'+id+'/toggle',{method:'POST'}); loadTasks(); }
async function delTask(id) { await api('/api/tasks/'+id,{method:'DELETE'}); loadTasks(); }
async function createTask() {
  var groups = qs('tgroups').value.split('\n').filter(function(g){ return g.trim(); });
  await api('/api/tasks',{method:'POST',body:{name:qs('tname').value,message:qs('tmsg').value,groups:groups,schedule:{type:'daily',time:qs('ttime').value}}});
  loadTasks();
}
async function loadSites() {
  var r = await api('/api/sites');
  var sites = r.sites || [];
  var html = '<div class="card"><h2>签到站点</h2><table><tr><th>名称</th><th>URL</th><th>状态</th><th>上次</th><th>操作</th></tr>';
  for (var i=0;i<sites.length;i++) {
    var s = sites[i];
    html += '<tr><td>'+esc(s.name)+'</td><td>'+esc((s.url||'').substring(0,30))+'</td><td>'+(s.checkin_selector?'\u2705':'\u26A0\uFE0F')+'</td><td>'+(s.last_checkin||'-')+'</td>' +
      '<td><button class="btn btn-primary btn-sm" onclick="checkinSite('+s.id+')">\u25B6</button> ' +
      '<button class="btn btn-danger btn-sm" onclick="delSite('+s.id+')">\u2715</button></td></tr>';
  }
  html += '</table></div>';
  qs('page-sites').innerHTML = html;
}
async function checkinSite(id) { await api('/api/sites/'+id+'/checkin',{method:'POST'}); alert('签到请求已发送'); }
async function delSite(id) { await api('/api/sites/'+id,{method:'DELETE'}); loadSites(); }
async function loadHistory() {
  var r = await api('/api/history?limit=50');
  var h = r.history || [];
  var html = '<div class="card"><h2>执行历史</h2><table><tr><th>时间</th><th>任务</th><th>类型</th><th>状态</th><th>详情</th></tr>';
  for (var i=0;i<h.length;i++) {
    var e = h[i];
    var t = (e._time||e.time||'Time').substring(0,16);
    var color = e.status==='success' ? '#4caf50' : '#f44336';
    html += '<tr><td>'+esc(t)+'</td><td>'+esc(e.task_name||'-')+'</td><td>'+esc(e.task_type||'-')+'</td><td style="color:'+color+'">'+esc(e.status)+'</td><td>'+esc((e.message||'').substring(0,40))+'</td></tr>';
  }
  html += '</table></div>';
  qs('page-history').innerHTML = html;
}
loadOverview();
</script>
</body>
</html>"""
