use keyring::Entry;
use serde::{Deserialize, Serialize};
use std::fs::{self, File};
use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{Mutex, OnceLock};
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::Manager;

const SERVICE_NAME: &str = "FocusTask";
const TOKEN_ACCOUNT: &str = "auth_token";
const USERNAME_ACCOUNT: &str = "auth_username";
const BACKEND_PORT: &str = "8765";
const BACKEND_BINARY: &str = "focus-task-backend";
const BACKEND_DB_NAME: &str = "todo.db";
const BACKEND_SECRET_NAME: &str = "secret.key";

static BACKEND_CHILD: OnceLock<Mutex<Option<Child>>> = OnceLock::new();

#[derive(Serialize, Deserialize)]
struct AuthState {
    token: String,
    username: String,
}

#[derive(Serialize, Deserialize)]
struct NativeNotificationPayload {
    title: String,
    body: String,
}

fn keyring_entry(account: &str) -> Result<Entry, String> {
    Entry::new(SERVICE_NAME, account).map_err(|err| err.to_string())
}

fn backend_child() -> &'static Mutex<Option<Child>> {
    BACKEND_CHILD.get_or_init(|| Mutex::new(None))
}

fn backend_port_is_open() -> bool {
    TcpStream::connect_timeout(
        &format!("127.0.0.1:{BACKEND_PORT}")
            .parse()
            .expect("valid backend address"),
        Duration::from_millis(150),
    )
    .is_ok()
}

fn backend_health_ok() -> bool {
    let addr = format!("127.0.0.1:{BACKEND_PORT}")
        .parse()
        .expect("valid backend address");

    let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(250)) else {
        return false;
    };

    let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(500)));

    let request = format!(
        "GET /api/health HTTP/1.1\r\nHost: 127.0.0.1:{BACKEND_PORT}\r\nConnection: close\r\n\r\n"
    );
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }

    let mut response = String::new();
    if stream.read_to_string(&mut response).is_err() {
        return false;
    }

    response.starts_with("HTTP/1.1 200") && response.contains(r#""status":"ok""#)
}

fn wait_for_backend() -> bool {
    for _ in 0..40 {
        if backend_health_ok() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    false
}

fn ensure_backend_database(resource_dir: &Path, app_data_dir: &Path) -> std::io::Result<PathBuf> {
    fs::create_dir_all(app_data_dir)?;

    let db_path = app_data_dir.join(BACKEND_DB_NAME);
    if !db_path.exists() {
        let seed_db_path = resource_dir.join("seed").join(BACKEND_DB_NAME);
        if seed_db_path.exists() {
            fs::copy(seed_db_path, &db_path)?;
        }
    }

    Ok(db_path)
}

fn ensure_backend_secret(app_data_dir: &Path) -> std::io::Result<String> {
    fs::create_dir_all(app_data_dir)?;

    let secret_path = app_data_dir.join(BACKEND_SECRET_NAME);
    if let Ok(existing) = fs::read_to_string(&secret_path) {
        let trimmed = existing.trim();
        if !trimmed.is_empty() {
            return Ok(trimmed.to_string());
        }
    }

    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    let secret = format!("focus-task-desktop-{now}-{}", std::process::id());
    fs::write(&secret_path, &secret)?;
    Ok(secret)
}

fn start_backend(app: &mut tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    if backend_health_ok() {
        return Ok(());
    }
    if backend_port_is_open() {
        return Err(format!(
            "127.0.0.1:{BACKEND_PORT} 已被占用，但不是 Focus Task 后端服务"
        )
        .into());
    }

    let resource_dir = app.path().resource_dir()?;
    let backend_path = resource_dir.join(BACKEND_BINARY);
    if !backend_path.exists() {
        eprintln!(
            "Focus Task backend binary not found: {}",
            backend_path.display()
        );
        return Ok(());
    }

    let app_data_dir = app.path().app_data_dir()?;
    let db_path = ensure_backend_database(&resource_dir, &app_data_dir)?;
    let secret = ensure_backend_secret(&app_data_dir)?;

    let log_dir = app
        .path()
        .app_log_dir()
        .unwrap_or_else(|_| app_data_dir.join("logs"));
    fs::create_dir_all(&log_dir)?;

    let stdout = File::create(log_dir.join("backend.out.log"))?;
    let stderr = File::create(log_dir.join("backend.err.log"))?;

    let child = Command::new(&backend_path)
        .current_dir(&app_data_dir)
        .env("FOCUS_TASK_BACKEND_PORT", BACKEND_PORT)
        .env(
            "FOCUS_TASK_DATABASE_URL",
            format!("sqlite:///{}", db_path.display()),
        )
        .env("FOCUS_TASK_SECRET_KEY", secret)
        .stdout(Stdio::from(stdout))
        .stderr(Stdio::from(stderr))
        .spawn()?;

    *backend_child().lock().unwrap() = Some(child);

    if !wait_for_backend() {
        stop_backend();
        return Err("Focus Task 后端启动超时".into());
    }

    Ok(())
}

fn stop_backend() {
    if let Some(mut child) = backend_child().lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

#[tauri::command]
fn load_auth_state() -> Result<Option<AuthState>, String> {
    let token_entry = keyring_entry(TOKEN_ACCOUNT)?;
    let username_entry = keyring_entry(USERNAME_ACCOUNT)?;

    let token = match token_entry.get_password() {
        Ok(value) => value,
        Err(keyring::Error::NoEntry) => return Ok(None),
        Err(err) => return Err(err.to_string()),
    };
    let username = match username_entry.get_password() {
        Ok(value) => value,
        Err(keyring::Error::NoEntry) => String::new(),
        Err(err) => return Err(err.to_string()),
    };

    Ok(Some(AuthState { token, username }))
}

#[tauri::command]
fn save_auth_state(state: AuthState) -> Result<(), String> {
    keyring_entry(TOKEN_ACCOUNT)?
        .set_password(&state.token)
        .map_err(|err| err.to_string())?;
    keyring_entry(USERNAME_ACCOUNT)?
        .set_password(&state.username)
        .map_err(|err| err.to_string())?;
    Ok(())
}

#[tauri::command]
fn clear_auth_state() -> Result<(), String> {
    let token_entry = keyring_entry(TOKEN_ACCOUNT)?;
    let username_entry = keyring_entry(USERNAME_ACCOUNT)?;

    if let Err(err) = token_entry.delete_credential() {
        if !matches!(err, keyring::Error::NoEntry) {
            return Err(err.to_string());
        }
    }
    if let Err(err) = username_entry.delete_credential() {
        if !matches!(err, keyring::Error::NoEntry) {
            return Err(err.to_string());
        }
    }

    Ok(())
}

#[tauri::command]
fn open_notification_settings() -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg("x-apple.systempreferences:com.apple.preference.notifications")
            .status()
            .map_err(|err| err.to_string())?;
        return Ok(());
    }

    #[allow(unreachable_code)]
    Err("当前平台暂不支持直接打开通知设置".to_string())
}

#[tauri::command]
fn send_native_notification(payload: NativeNotificationPayload) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        let script = format!(
            "display notification {} with title {} sound name \"default\"",
            applescript_string(&payload.body),
            applescript_string(&payload.title)
        );
        Command::new("osascript")
            .arg("-e")
            .arg(script)
            .status()
            .map_err(|err| err.to_string())?;
        return Ok(());
    }

    #[allow(unreachable_code)]
    Err("当前平台暂不支持原生通知".to_string())
}

#[cfg(target_os = "macos")]
fn applescript_string(value: &str) -> String {
    format!("{:?}", value)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            load_auth_state,
            save_auth_state,
            clear_auth_state,
            open_notification_settings,
            send_native_notification
        ])
        .setup(|app| {
            // ─── Custom Chinese Menu for macOS ───
            #[cfg(target_os = "macos")]
            {
                let app_menu = Submenu::with_items(
                    app,
                    "Focus Task",
                    true,
                    &[
                        &MenuItem::with_id(app, "about", "关于 Focus Task", true, None::<&str>)?,
                        &PredefinedMenuItem::separator(app)?,
                        &MenuItem::with_id(app, "quit", "退出 Focus Task", true, Some("Cmd+Q"))?,
                    ],
                )?;

                let file_menu = Submenu::with_items(
                    app,
                    "文件",
                    true,
                    &[
                        &MenuItem::with_id(app, "new_task", "新建任务", true, Some("Cmd+N"))?,
                        &PredefinedMenuItem::separator(app)?,
                        &MenuItem::with_id(app, "close_window", "关闭窗口", true, Some("Cmd+W"))?,
                    ],
                )?;

                let edit_menu = Submenu::with_items(
                    app,
                    "编辑",
                    true,
                    &[
                        &MenuItem::with_id(app, "undo", "撤销", true, Some("Cmd+Z"))?,
                        &MenuItem::with_id(app, "redo", "重做", true, Some("Cmd+Shift+Z"))?,
                        &PredefinedMenuItem::separator(app)?,
                        &MenuItem::with_id(app, "cut", "剪切", true, Some("Cmd+X"))?,
                        &MenuItem::with_id(app, "copy", "复制", true, Some("Cmd+C"))?,
                        &MenuItem::with_id(app, "paste", "粘贴", true, Some("Cmd+V"))?,
                        &MenuItem::with_id(app, "select_all", "全选", true, Some("Cmd+A"))?,
                    ],
                )?;

                let view_menu = Submenu::with_items(
                    app,
                    "视图",
                    true,
                    &[&MenuItem::with_id(
                        app,
                        "fullscreen",
                        "进入全屏幕",
                        true,
                        Some("Ctrl+Cmd+F"),
                    )?],
                )?;

                let window_menu = Submenu::with_items(
                    app,
                    "窗口",
                    true,
                    &[
                        &MenuItem::with_id(app, "minimize", "最小化", true, Some("Cmd+M"))?,
                        &PredefinedMenuItem::separator(app)?,
                        &MenuItem::with_id(app, "close_win", "关闭窗口", true, Some("Cmd+W"))?,
                    ],
                )?;

                let help_menu = Submenu::with_items(
                    app,
                    "帮助",
                    true,
                    &[&MenuItem::with_id(
                        app,
                        "help",
                        "Focus Task 帮助",
                        true,
                        None::<&str>,
                    )?],
                )?;

                let menu = Menu::with_items(
                    app,
                    &[
                        &app_menu,
                        &file_menu,
                        &edit_menu,
                        &view_menu,
                        &window_menu,
                        &help_menu,
                    ],
                )?;
                app.set_menu(menu)?;
            }

            if let Err(err) = start_backend(app) {
                eprintln!("Failed to start Focus Task backend: {err}");
            }

            #[cfg(debug_assertions)]
            {
                let window = app.get_webview_window("main").unwrap();
                window.open_devtools();
            }
            Ok(())
        })
        .on_menu_event(|app, event| match event.id().as_ref() {
            "quit" => {
                app.exit(0);
            }
            "close_window" | "close_win" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.close();
                }
            }
            "minimize" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.minimize();
                }
            }
            _ => {}
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|_app_handle, event| match event {
            tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => stop_backend(),
            _ => {}
        });
}
