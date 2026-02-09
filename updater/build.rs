#[cfg(target_os = "windows")]
fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=../icon.ico");

    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".into());
    let icon_path = std::path::Path::new(&manifest_dir)
        .join("..")
        .join("icon.ico");

    if !icon_path.exists() {
        println!(
            "cargo:warning=icon.ico not found at {}",
            icon_path.display()
        );
        return;
    }

    let mut res = winres::WindowsResource::new();
    res.set_icon(icon_path.to_str().unwrap_or("..\\icon.ico"));

    if let Err(err) = res.compile() {
        println!("cargo:warning=failed to embed updater icon: {err}");
    }
}

#[cfg(not(target_os = "windows"))]
fn main() {}
