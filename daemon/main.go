/*
QQBotStation Daemon (Go)
======================
高性能 API 守护进程，替代 Python 简易 HTTP 服务器。
支持 SQLite 数据库直连、REST API、嵌入式 Web 管理面板。

编译:
  cd daemon
  go build -o qqbot-daemon .

跨平台:
  GOOS=windows GOARCH=amd64 go build -o qqbot-daemon.exe .
  GOOS=linux   GOARCH=amd64 go build -o qqbot-daemon .
  GOOS=linux   GOARCH=arm64 go build -o qqbot-daemon-arm64 .

运行:
  ./qqbot-daemon --port 8580 --db ../data/qqbot.db
*/
package main

import (
	"database/sql"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

// ==================== 配置 ====================

type Config struct {
	Port int
	Host string
	DB   string
}

// ==================== 数据库 ====================

type Database struct {
	db *sql.DB
}

func NewDatabase(path string) (*Database, error) {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("创建目录失败: %w", err)
	}
	db, err := sql.Open("sqlite3", path+"?_journal_mode=WAL&_foreign_keys=on")
	if err != nil {
		return nil, fmt.Errorf("打开数据库失败: %w", err)
	}
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("数据库连接失败: %w", err)
	}
	d := &Database{db: db}
	if err := d.initTables(); err != nil {
		return nil, fmt.Errorf("初始化表失败: %w", err)
	}
	return d, nil
}

func (d *Database) initTables() error {
	sqls := []string{
		`CREATE TABLE IF NOT EXISTS tasks (
			id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL DEFAULT 'qq',
			enabled INTEGER NOT NULL DEFAULT 1, config TEXT NOT NULL DEFAULT '{}',
			schedule TEXT NOT NULL DEFAULT '{}', next_run TEXT, last_run TEXT,
			last_status TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
		)`,
		`CREATE TABLE IF NOT EXISTS history (
			id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, task_name TEXT,
			task_type TEXT, status TEXT NOT NULL, message TEXT DEFAULT '',
			time TEXT NOT NULL
		)`,
		`CREATE TABLE IF NOT EXISTS sites (
			id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
			url TEXT NOT NULL, checkin_selector TEXT DEFAULT '',
			success_indicator TEXT DEFAULT '签到成功', need_login INTEGER DEFAULT 0,
			username TEXT DEFAULT '', password TEXT DEFAULT '',
			last_checkin TEXT DEFAULT '-', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
		)`,
		`CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL)`,
		`CREATE INDEX IF NOT EXISTS idx_history_time ON history(time DESC)`,
		`CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type)`,
	}
	for _, s := range sqls {
		if _, err := d.db.Exec(s); err != nil {
			return err
		}
	}
	return nil
}

// ==================== REST API ====================

type ApiServer struct {
	db  *Database
	cfg *Config
}

func NewApiServer(db *Database, cfg *Config) *ApiServer {
	return &ApiServer{db: db, cfg: cfg}
}

func (s *ApiServer) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/api/status", s.handleStatus)
	mux.HandleFunc("/api/tasks", s.handleTasks)
	mux.HandleFunc("/api/tasks/", s.handleTaskByID)
	mux.HandleFunc("/api/history", s.handleHistory)
	mux.HandleFunc("/api/sites", s.handleSites)
	mux.HandleFunc("/api/config", s.handleConfig)
	mux.HandleFunc("/", s.handleWeb)
}

// CORS 中间件
func cors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Method == "OPTIONS" {
			w.WriteHeader(200)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func jsonResponse(w http.ResponseWriter, data interface{}, status int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func (s *ApiServer) handleStatus(w http.ResponseWriter, r *http.Request) {
	var total, enabled, sites, hist int
	s.db.db.QueryRow("SELECT COUNT(*) FROM tasks").Scan(&total)
	s.db.db.QueryRow("SELECT COUNT(*) FROM tasks WHERE enabled=1").Scan(&enabled)
	s.db.db.QueryRow("SELECT COUNT(*) FROM sites").Scan(&sites)
	s.db.db.QueryRow("SELECT COUNT(*) FROM history").Scan(&hist)

	jsonResponse(w, map[string]interface{}{
		"status":  "running",
		"version": "1.0.0",
		"platform": "go/" + strings.Title(runtime()),
		"time":    time.Now().Format(time.RFC3339),
		"stats": map[string]int{
			"tasks_total":   total,
			"tasks_enabled": enabled,
			"sites_total":   sites,
			"history_total": hist,
		},
	}, 200)
}

func runtime() string {
	return fmt.Sprintf("%s_%s", os.Getenv("GOOS"), os.Getenv("GOARCH"))
}

func (s *ApiServer) handleTasks(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case "GET":
		rows, err := s.db.db.Query("SELECT id, name, type, enabled, config, schedule, next_run, last_run, last_status FROM tasks ORDER BY created_at DESC")
		if err != nil {
			jsonResponse(w, map[string]string{"error": err.Error()}, 500)
			return
		}
		defer rows.Close()

		tasks := []map[string]interface{}{}
		for rows.Next() {
			var id, name, tp, config, sched, next, last, status string
			var enabled int
			rows.Scan(&id, &name, &tp, &enabled, &config, &sched, &next, &last, &status)
			tasks = append(tasks, map[string]interface{}{
				"id": id, "name": name, "type": tp,
				"enabled": enabled == 1,
				"config":  config, "schedule": sched,
				"_next_run": next, "_last_run": last, "_last_status": status,
			})
		}
		jsonResponse(w, map[string]interface{}{"tasks": tasks}, 200)

	case "POST":
		var body map[string]interface{}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			jsonResponse(w, map[string]string{"error": "无效的JSON"}, 400)
			return
		}
		id := fmt.Sprintf("go-%d", time.Now().UnixNano())
		name, _ := body["name"].(string)
		tp, _ := body["type"].(string)
		if tp == "" {
			tp = "qq"
		}
		now := time.Now().Format(time.RFC3339)
		configJSON, _ := json.Marshal(body)
		schedJSON, _ := json.Marshal(body["schedule"])

		_, err := s.db.db.Exec(
			"INSERT INTO tasks (id, name, type, enabled, config, schedule, created_at, updated_at) VALUES (?,?,?,1,?,?,?,?)",
			id, name, tp, string(configJSON), string(schedJSON), now, now)
		if err != nil {
			jsonResponse(w, map[string]string{"error": err.Error()}, 500)
			return
		}
		jsonResponse(w, map[string]string{"id": id, "message": "任务已创建"}, 201)
	}
}

func (s *ApiServer) handleTaskByID(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/api/tasks/")
	id = strings.Split(id, "/")[0] // 去除子路径

	switch r.Method {
	case "GET":
		var name, tp, config, sched, next, last, status string
		var enabled int
		err := s.db.db.QueryRow(
			"SELECT name, type, enabled, config, schedule, next_run, last_run, last_status FROM tasks WHERE id=?",
			id).Scan(&name, &tp, &enabled, &config, &sched, &next, &last, &status)
		if err != nil {
			jsonResponse(w, map[string]string{"error": "任务不存在"}, 404)
			return
		}
		jsonResponse(w, map[string]interface{}{
			"id": id, "name": name, "type": tp, "enabled": enabled == 1,
			"config": config, "schedule": sched,
			"_next_run": next, "_last_run": last, "_last_status": status,
		}, 200)

	case "DELETE":
		_, err := s.db.db.Exec("DELETE FROM tasks WHERE id=?", id)
		if err != nil {
			jsonResponse(w, map[string]string{"error": err.Error()}, 500)
			return
		}
		jsonResponse(w, map[string]string{"message": "任务已删除"}, 200)

	case "PUT":
		var body map[string]interface{}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			jsonResponse(w, map[string]string{"error": "无效的JSON"}, 400)
			return
		}
		now := time.Now().Format(time.RFC3339)
		if name, ok := body["name"].(string); ok {
			s.db.db.Exec("UPDATE tasks SET name=?, updated_at=? WHERE id=?", name, now, id)
		}
		if enabled, ok := body["enabled"].(bool); ok {
			v := 0
			if enabled {
				v = 1
			}
			s.db.db.Exec("UPDATE tasks SET enabled=?, updated_at=? WHERE id=?", v, now, id)
		}
		jsonResponse(w, map[string]string{"message": "任务已更新"}, 200)
	}
}

func (s *ApiServer) handleHistory(w http.ResponseWriter, r *http.Request) {
	if r.Method == "DELETE" {
		s.db.db.Exec("DELETE FROM history")
		jsonResponse(w, map[string]string{"message": "历史已清空"}, 200)
		return
	}

	rows, err := s.db.db.Query("SELECT task_id, task_name, task_type, status, message, time FROM history ORDER BY time DESC LIMIT 100")
	if err != nil {
		jsonResponse(w, map[string]string{"error": err.Error()}, 500)
		return
	}
	defer rows.Close()

	hist := []map[string]interface{}{}
	for rows.Next() {
		var tid, name, tp, status, msg, t string
		rows.Scan(&tid, &name, &tp, &status, &msg, &t)
		hist = append(hist, map[string]interface{}{
			"task_id": tid, "task_name": name, "task_type": tp,
			"status": status, "message": msg, "_time": t,
		})
	}
	jsonResponse(w, map[string]interface{}{"history": hist}, 200)
}

func (s *ApiServer) handleSites(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" {
		jsonResponse(w, map[string]string{"error": "仅支持GET"}, 405)
		return
	}
	rows, err := s.db.db.Query("SELECT id, name, url, checkin_selector, success_indicator, need_login, last_checkin FROM sites ORDER BY name")
	if err != nil {
		jsonResponse(w, map[string]string{"error": err.Error()}, 500)
		return
	}
	defer rows.Close()

	sites := []map[string]interface{}{}
	for rows.Next() {
		var id int
		var name, url, selector, indicator, last string
		var needLogin int
		rows.Scan(&id, &name, &url, &selector, &indicator, &needLogin, &last)
		sites = append(sites, map[string]interface{}{
			"id": id, "name": name, "url": url,
			"checkin_selector": selector, "success_indicator": indicator,
			"need_login": needLogin == 1, "last_checkin": last,
		})
	}
	jsonResponse(w, map[string]interface{}{"sites": sites}, 200)
}

func (s *ApiServer) handleConfig(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" {
		jsonResponse(w, map[string]string{"error": "仅支持GET"}, 405)
		return
	}
	rows, err := s.db.db.Query("SELECT key, value FROM config")
	if err != nil {
		jsonResponse(w, map[string]string{"error": err.Error()}, 500)
		return
	}
	defer rows.Close()

	cfg := map[string]string{}
	for rows.Next() {
		var k, v string
		rows.Scan(&k, &v)
		cfg[k] = v
	}
	jsonResponse(w, cfg, 200)
}

func (s *ApiServer) handleWeb(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		jsonResponse(w, map[string]string{"error": "not found"}, 404)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(200)
	w.Write([]byte(AdminHTML))
}

// ==================== 入口 ====================

func main() {
	port := flag.Int("port", 8580, "API 端口")
	host := flag.String("host", "0.0.0.0", "绑定地址")
	dbPath := flag.String("db", "../data/qqbot.db", "SQLite 数据库路径")
	flag.Parse()

	cfg := &Config{Port: *port, Host: *host, DB: *dbPath}

	fmt.Printf("QQBotStation Daemon (Go)\n")
	fmt.Printf("  数据库: %s\n", cfg.DB)
	fmt.Printf("  监听:   %s:%d\n", cfg.Host, cfg.Port)

	db, err := NewDatabase(cfg.DB)
	if err != nil {
		log.Fatalf("数据库初始化失败: %v", err)
	}
	defer db.db.Close()

	api := NewApiServer(db, cfg)
	mux := http.NewServeMux()
	api.RegisterRoutes(mux)

	server := &http.Server{
		Addr:    fmt.Sprintf("%s:%d", cfg.Host, cfg.Port),
		Handler: cors(mux),
	}

	// 信号处理
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigChan
		fmt.Println("\n收到退出信号，正在关闭...")
		server.Close()
	}()

	fmt.Printf("API 服务器已启动: http://%s:%d\n", cfg.Host, cfg.Port)
	if err := server.ListenAndServe(); err != http.ErrServerClosed {
		log.Fatalf("服务器错误: %v", err)
	}
	fmt.Println("服务器已停止")
}

// 用于交叉编译检测
func init() {
	if v := os.Getenv("GOOS"); v != "" {
		os.Setenv("GOOS", v)
	}
	if v := os.Getenv("GOARCH"); v != "" {
		os.Setenv("GOARCH", v)
	}
}

// AdminHTML 是嵌入式 Web 管理面板
const AdminHTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QQBotStation</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Microsoft YaHei','Segoe UI',sans-serif;background:#1a1b2e;color:#e0e0e0}
.header{background:#141526;padding:16px 24px;border-bottom:1px solid #2a2b3e}
.header h1{font-size:18px;color:#c8c8d4}
.container{display:flex;min-height:calc(100vh - 56px)}
.sidebar{width:180px;background:#141526;border-right:1px solid #2a2b3e;padding:8px 0}
.sidebar a{display:block;padding:10px 20px;color:#8888a0;text-decoration:none;font-size:13px}
.sidebar a:hover{background:#2a2b3e;color:#c8c8d4}
.sidebar a.active{background:#3a3b5e;color:#7c7cf0;border-left:3px solid #5c5cf0}
.content{flex:1;padding:24px}
.card{background:#1e1f32;border:1px solid #2a2b3e;border-radius:8px;padding:16px;margin-bottom:16px}
.card h2{font-size:15px;margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #2a2b3e}
th{color:#9c9cb0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}
.stat-c{background:#141526;border-radius:8px;padding:16px;text-align:center}
.stat-c .n{font-size:28px;font-weight:700;color:#5c5cf0}
.stat-c .l{font-size:12px;color:#6a6a80}
.btn{display:inline-block;padding:4px 12px;border:none;border-radius:4px;cursor:pointer;font-size:12px}
.btn-pri{background:#5c5cf0;color:white}
.btn-del{background:#d94a4a;color:white}
</style>
</head>
<body>
<div class="header"><h1>QQBotStation</h1></div>
<div class="container">
<div class="sidebar" id="sidebar"></div>
<div class="content" id="content"></div>
</div>
<script>
const S=[['overview','Overview'],['tasks','Tasks'],['sites','Sites'],['history','History']];
let cur='overview';
async function g(p){const r=await fetch(p);return r.json()}
function show(n){cur=n;
  document.getElementById('sidebar').innerHTML=S.map(([id,lb]) => '<a href="#" class="'+(cur===id?'active':'')+'" onclick="show(\''+id+'\')">'+lb+'</a>').join('');
  if(cur==='overview')ov();else if(cur==='tasks')ts();else if(cur==='sites')st();else if(cur==='history')hi();
}
async function ov(){const s=await g('/api/status'),st=s.stats||{};document.getElementById('content').innerHTML=
  '<div class="stats"><div class="stat-c"><div class="n">'+(st.tasks_total||0)+'</div><div class="l">Tasks</div></div>'+
  '<div class="stat-c"><div class="n">'+(st.tasks_enabled||0)+'</div><div class="l">Active</div></div>'+
  '<div class="stat-c"><div class="n">'+(st.sites_total||0)+'</div><div class="l">Sites</div></div>'+
  '<div class="stat-c"><div class="n">'+(st.history_total||0)+'</div><div class="l">History</div></div></div>';}
async function ts(){const r=await g('/api/tasks'),ts=r.tasks||[];let h='<div class="card"><h2>Tasks</h2><table><tr><th>Name</th><th>Type</th><th>Status</th></tr>';
  for(const t of ts)h+='<tr><td>'+(t.name||'')+'</td><td>'+t.type+'</td><td>'+(t.enabled?'Active':'Paused')+'</td></tr>';
  h+='</table></div>';document.getElementById('content').innerHTML=h;}
async function st(){const r=await g('/api/sites'),ss=r.sites||[];let h='<div class="card"><h2>Sites</h2><table><tr><th>Name</th><th>URL</th><th>Status</th></tr>';
  for(const s of ss)h+='<tr><td>'+(s.name||'')+'</td><td>'+(s.url||'').substring(0,30)+'</td><td>'+(s.checkin_selector?'Ready':'Pending')+'</td></tr>';
  h+='</table></div>';document.getElementById('content').innerHTML=h;}
async function hi(){const r=await g('/api/history'),hh=r.history||[];let h='<div class="card"><h2>History</h2><table><tr><th>Time</th><th>Task</th><th>Status</th></tr>';
  for(const e of hh){const t=(e._time||'').substring(0,16);h+='<tr><td>'+t+'</td><td>'+(e.task_name||'-')+'</td><td>'+e.status+'</td></tr>';}
  h+='</table></div>';document.getElementById('content').innerHTML=h;}
show('overview');
</script>
</body>
</html>`
