#![cfg_attr(target_os = "windows", windows_subsystem = "windows")]

use reqwest::blocking::Client;
use semver::Version;
use serde::Deserialize;
use std::ffi::OsStr;
use std::env;
use std::fs;
use std::fs::OpenOptions;
use std::io::{self, Write};
#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::thread;
use std::time::Duration;
use std::time::{SystemTime, UNIX_EPOCH};

// Icon attribution: Sleep icons created by Freepik - Flaticon
// https://www.flaticon.com/free-icons/sleep

const APP_EXE: &str = "LetMeSleep.exe";
const UPDATER_EXE: &str = "LetMeSleep-Updater.exe";
const REPO: &str = "cytsai1008/let-me-sleep";
#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[derive(Deserialize)]
struct Release {
    tag_name: String,
    assets: Vec<Asset>,
}

#[derive(Deserialize)]
struct Asset {
    name: String,
    browser_download_url: String,
    size: u64,
}

struct Logger {
    file: Option<fs::File>,
}

fn pretty_path(path: &Path, base_dir: &Path) -> String {
    path.strip_prefix(base_dir)
        .map(|p| {
            if p.as_os_str().is_empty() {
                ".".to_string()
            } else {
                p.display().to_string()
            }
        })
        .unwrap_or_else(|_| path.display().to_string())
}

impl Logger {
    fn new(app_dir: &Path) -> Self {
        let log_path = app_dir.join("LetMeSleep-Updater.log");
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(log_path)
            .ok();
        Self { file }
    }

    fn log<S: AsRef<str>>(&mut self, message: S) {
        if let Some(file) = self.file.as_mut() {
            let ts = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs())
                .unwrap_or(0);
            let _ = writeln!(file, "[{ts}] {}", message.as_ref());
            let _ = file.flush();
        }
    }
}

fn parse_version(tag: &str) -> Option<Version> {
    Version::parse(tag.strip_prefix('v').unwrap_or(tag)).ok()
}

fn get_current_version(app_dir: &Path) -> Option<Version> {
    let content = fs::read_to_string(app_dir.join("VERSION")).ok()?;
    parse_version(content.trim())
}

fn check_for_update(
    client: &Client,
    repo: &str,
    current: &Version,
    logger: &mut Logger,
) -> Option<(String, Asset)> {
    let url = format!("https://api.github.com/repos/{}/releases/latest", repo);
    logger.log(format!("Checking latest release: {url}"));

    let resp = client
        .get(&url)
        .header("User-Agent", "LetMeSleep-Updater")
        .send()
        .ok()?;

    if !resp.status().is_success() {
        logger.log(format!("Update check HTTP status: {}", resp.status()));
        return None;
    }

    let release: Release = resp.json().ok()?;
    let latest = parse_version(&release.tag_name)?;

    if latest <= *current {
        logger.log("No update available");
        return None;
    }

    let asset = release.assets.iter().find(|a| a.name.ends_with(".zip"))?;

    Some((
        release.tag_name.clone(),
        Asset {
            name: asset.name.clone(),
            browser_download_url: asset.browser_download_url.clone(),
            size: asset.size,
        },
    ))
}

fn download(
    client: &Client,
    asset: &Asset,
    dest: &Path,
    logger: &mut Logger,
) -> Result<(), String> {
    logger.log(format!(
        "Downloading {} ({:.1} MB)",
        asset.name,
        asset.size as f64 / 1_048_576.0
    ));

    let bytes = client
        .get(&asset.browser_download_url)
        .header("User-Agent", "LetMeSleep-Updater")
        .send()
        .and_then(|r| r.error_for_status())
        .and_then(|r| r.bytes())
        .map_err(|e| format!("Download failed: {e}"))?;

    fs::write(dest, &bytes).map_err(|e| format!("Write failed: {e}"))?;
    logger.log("Download complete");
    Ok(())
}

fn kill_app(process_name: &str, logger: &mut Logger) {
    logger.log(format!("Stopping {process_name}"));
    let _ = Command::new("taskkill")
        .args(["/F", "/IM", process_name])
        .output();
    thread::sleep(Duration::from_secs(2));
}

fn extract_zip(zip_path: &Path, dest: &Path, logger: &mut Logger) -> Result<(), String> {
    logger.log("Extracting archive");
    let file = fs::File::open(zip_path).map_err(|e| format!("Open zip: {e}"))?;
    let mut archive = zip::ZipArchive::new(file).map_err(|e| format!("Invalid zip: {e}"))?;

    for i in 0..archive.len() {
        let mut entry = archive.by_index(i).map_err(|e| format!("Zip entry: {e}"))?;
        let entry_name = entry.name().replace('\\', "/");

        let out_path = if entry_name
            .rsplit('/')
            .next()
            .map(|name| name.eq_ignore_ascii_case(UPDATER_EXE))
            .unwrap_or(false)
        {
            logger.log("Staging updater replacement file");
            dest.join("LetMeSleep-Updater.new.exe")
        } else {
            dest.join(entry.name())
        };

        if entry.is_dir() {
            fs::create_dir_all(&out_path).ok();
        } else {
            if let Some(parent) = out_path.parent() {
                fs::create_dir_all(parent).ok();
            }
            let mut outfile =
                fs::File::create(&out_path).map_err(|e| format!("Create {}: {e}", entry.name()))?;
            io::copy(&mut entry, &mut outfile).map_err(|e| format!("Extract: {e}"))?;
        }
    }
    logger.log("Extraction complete");
    Ok(())
}

fn schedule_updater_replacement(app_dir: &Path, logger: &mut Logger) {
    let staged = app_dir.join("LetMeSleep-Updater.new.exe");
    if !staged.exists() {
        return;
    }

    let target = app_dir.join(UPDATER_EXE);
    logger.log("Scheduling updater self-replacement");

    let src = staged.to_string_lossy().replace('"', "\"\"");
    let dst = target.to_string_lossy().replace('"', "\"\"");
    let ps_script = format!(
        "$src=\"{src}\"; $dst=\"{dst}\"; for($i=0; $i -lt 40; $i++) {{ try {{ Move-Item -LiteralPath $src -Destination $dst -Force -ErrorAction Stop; exit 0 }} catch {{ Start-Sleep -Milliseconds 500 }} }}; exit 1"
    );

    let mut cmd = Command::new("powershell");
    cmd.args([
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-Command",
        &ps_script,
    ]);
    #[cfg(target_os = "windows")]
    {
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    match cmd.spawn() {
        Ok(_) => logger.log("Updater self-replacement scheduled"),
        Err(e) => logger.log(format!("Failed to schedule updater replacement: {e}")),
    }
}

fn find_app_exe(app_dir: &Path, logger: &mut Logger) -> Option<PathBuf> {
    let direct = app_dir.join(APP_EXE);
    if direct.exists() {
        logger.log(format!(
            "Using app executable: {}",
            pretty_path(&direct, app_dir)
        ));
        return Some(direct);
    }

    if let Ok(entries) = fs::read_dir(app_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if !path.is_dir() {
                continue;
            }

            let Some(dir_name) = path.file_name().and_then(OsStr::to_str) else {
                continue;
            };
            if !dir_name.ends_with(".dist") {
                continue;
            }

            let preferred = path.join(APP_EXE);
            if preferred.exists() {
                logger.log(format!(
                    "Using standalone app executable: {}",
                    pretty_path(&preferred, app_dir)
                ));
                return Some(preferred);
            }

            if let Ok(dist_entries) = fs::read_dir(&path) {
                for dist_entry in dist_entries.flatten() {
                    let dist_path = dist_entry.path();
                    if !dist_path.is_file() {
                        continue;
                    }
                    let is_exe = dist_path
                        .extension()
                        .and_then(OsStr::to_str)
                        .map(|ext| ext.eq_ignore_ascii_case("exe"))
                        .unwrap_or(false);
                    if !is_exe {
                        continue;
                    }

                    let file_name = dist_path
                        .file_name()
                        .and_then(OsStr::to_str)
                        .unwrap_or_default();
                    if file_name.eq_ignore_ascii_case(UPDATER_EXE)
                        || file_name.eq_ignore_ascii_case("LetMeSleep-Updater.new.exe")
                    {
                        continue;
                    }

                    logger.log(format!(
                        "Using fallback standalone executable: {}",
                        pretty_path(&dist_path, app_dir)
                    ));
                    return Some(dist_path);
                }
            }
        }
    }

    logger.log(format!(
        "App executable not found in {} (expected {APP_EXE})",
        app_dir.display()
    ));
    None
}

fn launch_app(app_path: &Path, app_dir: &Path, logger: &mut Logger, extra_args: &[&str]) {
    if app_path.exists() {
        logger.log(format!("Launching {}", pretty_path(app_path, app_dir)));
        let mut command = Command::new(&app_path);
        if !extra_args.is_empty() {
            command.args(extra_args);
        }
        let _ = command.spawn();
    } else {
        logger.log(format!("{} not found", pretty_path(app_path, app_dir)));
    }
}

fn is_app_running(process_name: &str, logger: &mut Logger) -> bool {
    let mut command = Command::new("tasklist");
    command.args([
        "/FI",
        &format!("IMAGENAME eq {process_name}"),
        "/FO",
        "CSV",
        "/NH",
    ]);
    #[cfg(target_os = "windows")]
    {
        command.creation_flags(CREATE_NO_WINDOW);
    }

    match command.output() {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout).to_lowercase();
            let running = stdout.contains(&process_name.to_lowercase());
            logger.log(format!("{process_name} running: {running}"));
            running
        }
        Err(e) => {
            logger.log(format!("Failed to query running process: {e}"));
            false
        }
    }
}

fn default_app_dir() -> PathBuf {
    if let Ok(exe) = env::current_exe()
        && let Some(parent) = exe.parent()
    {
        return parent.to_path_buf();
    }

    env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();

    let mut skip_update = false;
    let mut app_dir_arg: Option<PathBuf> = None;
    for arg in args.iter().skip(1) {
        if arg == "--no-update" {
            skip_update = true;
        } else if !arg.starts_with('-') && app_dir_arg.is_none() {
            app_dir_arg = Some(PathBuf::from(arg));
        }
    }

    let app_dir = app_dir_arg.unwrap_or_else(default_app_dir);
    let mut logger = Logger::new(&app_dir);
    logger.log("Updater started");
    logger.log(format!("Using app dir: {}", pretty_path(&app_dir, &app_dir)));

    let primary_app_path = app_dir.join(APP_EXE);
    let app_path = if primary_app_path.exists() {
        logger.log(format!(
            "Using app executable: {}",
            pretty_path(&primary_app_path, &app_dir)
        ));
        primary_app_path.clone()
    } else {
        logger.log(format!(
            "Primary app path missing ({}), searching fallback",
            pretty_path(&primary_app_path, &app_dir)
        ));
        find_app_exe(&app_dir, &mut logger).unwrap_or(primary_app_path.clone())
    };
    let app_process_name = app_path
        .file_name()
        .and_then(OsStr::to_str)
        .unwrap_or(APP_EXE)
        .to_string();

    if skip_update {
        if is_app_running(&app_process_name, &mut logger) {
            logger.log("--no-update set and app already running; skipping update check");
            launch_app(&app_path, &app_dir, &mut logger, &[]);
            return Ok(());
        }
        logger.log("--no-update set but app is not running; continuing with update check");
    }

    let current = get_current_version(&app_dir).unwrap_or(Version::new(0, 0, 0));
    logger.log(format!("Current version: v{current}"));

    let client = Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(|e| format!("HTTP error: {e}"))?;

    let Some((tag, asset)) = check_for_update(&client, REPO, &current, &mut logger) else {
        logger.log("App is up to date");
        launch_app(&app_path, &app_dir, &mut logger, &[]);
        return Ok(());
    };

    let latest = parse_version(&tag).unwrap();
    logger.log(format!("Updating: v{current} -> v{latest}"));

    let temp_zip = env::temp_dir().join("letmesleep_update.zip");
    if let Err(e) = download(&client, &asset, &temp_zip, &mut logger) {
        logger.log(format!("ERROR: {e}"));
        return Err(e);
    }

    kill_app(&app_process_name, &mut logger);

    if let Err(e) = extract_zip(&temp_zip, &app_dir, &mut logger) {
        logger.log(format!("ERROR: {e}"));
        return Err(e);
    }

    fs::write(app_dir.join("VERSION"), latest.to_string())
        .map_err(|e| format!("Write version: {e}"))?;
    let _ = fs::remove_file(&temp_zip);

    schedule_updater_replacement(&app_dir, &mut logger);

    logger.log(format!("Update complete: v{latest}"));
    let launch_after_update = if primary_app_path.exists() {
        primary_app_path
    } else {
        find_app_exe(&app_dir, &mut logger).unwrap_or(app_path)
    };
    launch_app(&launch_after_update, &app_dir, &mut logger, &[]);
    Ok(())
}

fn main() {
    if run().is_err() {
        std::process::exit(1);
    }
}
