# Orvix Universal System Control Reference (v1.1.0)

The **Orvix Universal Control Layer** extends the agent's capabilities across hardware, desktop applications, operating system services, active processes, network configurations, file systems, media, clipboard, and notifications.

---

## 1. Controllers & Tool APIs

### 1.1 Desktop Application Controller (`tools/app_controller.py`)
- **`launch_app(app_name_or_path: str, args: List[str] = None)`**: Launches an application binary or registered system app (e.g. `notepad`, `calc`, `code`, or absolute path).
- **`close_app(app_name: str, force: bool = False)`**: Terminates running instances of an application by process name.
- **`list_running_apps(limit: int = 50)`**: Lists active desktop applications with window titles, PIDs, and memory usage.
- **`is_app_running(app_name: str)`**: Checks if a given application is currently active.

### 1.2 Hardware & Metrics Controller (`tools/hardware_controller.py`)
- **`get_cpu_info()`**: Processor model, physical/logical core count, current utilization %, and clock frequency.
- **`get_ram_info()`**: Physical RAM (total, used, free GB, %) and virtual swap space metrics.
- **`get_disk_info()`**: All disk partitions, mountpoints, file system types, free/used space.
- **`get_battery_status()`**: Laptop battery percentage, power plug status, and time remaining.
- **`get_display_info()`**: Connected monitors, resolutions, and primary display flag.
- **`get_hardware_summary()`**: Consolidated overview combining OS, CPU, RAM, disks, battery, and displays.

### 1.3 Network Controller (`tools/network_controller.py`)
- **`get_ip_addresses()`**: All assigned IPv4 and IPv6 addresses across network adapters.
- **`ping_host(host: str, count: int = 4)`**: Tests network connectivity and measures latency.
- **`test_port(host: str, port: int, timeout: float = 3.0)`**: Validates if a TCP socket port is open and accepting traffic.
- **`get_active_connections(limit: int = 30)`**: Inspects listening ports and active sockets.
- **`get_wifi_networks()`**: Discovers nearby wireless SSIDs.
- **`flush_dns()`**: Flushes the local operating system DNS cache.

### 1.4 System Service Controller (`tools/service_controller.py`)
- **`list_services(status_filter: str = None, limit: int = 50)`**: Enumerates system services (Windows Services or systemd units).
- **`get_service_status(service_name: str)`**: Checks status of a named service (Running, Stopped, etc.).
- **`start_service(service_name: str)`**: Starts a stopped service.
- **`stop_service(service_name: str)`**: Stops a running service.
- **`restart_service(service_name: str)`**: Restarts an active service.

### 1.5 Process Controller (`tools/process_controller.py`)
- **`list_processes(sort_by: str = "cpu", limit: int = 20)`**: Lists top active processes sorted by CPU or memory usage.
- **`find_process(query: Union[str, int])`**: Locates processes by name substring or PID.
- **`kill_process(target: Union[str, int], force: bool = False)`**: Terminates process safely or with force.
- **`get_process_metrics(pid: int)`**: Detailed metrics on a PID (CPU %, RSS RAM, threads, command line).

### 1.6 File Operations Controller (`tools/file_controller.py`)
- **`get_file_info(path: str)`**: File size, creation/modification timestamps, type, and permissions.
- **`calculate_hash(path: str, algorithm: str = "sha256")`**: Computes SHA-256, MD5, or SHA-1 hashes.
- **`batch_rename(directory: str, search_pattern: str, replacement: str)`**: Batch renames files via regex.
- **`compress_files(sources: List[str], output_path: str, format: str = "zip")`**: Creates .zip or .tar.gz archives.
- **`extract_archive(archive_path: str, destination: str = None)`**: Extracts .zip, .tar, or .tar.gz archives.
- **`find_duplicates(directory: str, max_depth: int = 3)`**: Discovers identical files using size and content hashes.

### 1.7 Media & Peripheral Controller (`tools/media_controller.py`)
- **`get_volume()`**: Current master output volume and mute status.
- **`set_volume(level_percent: int)`**: Sets master output volume (0 to 100).
- **`mute_volume(mute: bool = True)`**: Toggles or sets audio muting.
- **`take_screenshot(output_path: str = None)`**: Captures full desktop screen to a PNG image.

### 1.8 Clipboard & Notifications (`tools/clipboard_tool.py`, `tools/notification_tool.py`)
- **`get_clipboard_text()`**: Reads current text from the system clipboard.
- **`set_clipboard_text(text: str)`**: Copies text to the system clipboard.
- **`show_notification(title: str, message: str, duration_sec: int = 5)`**: Dispatches native OS desktop toast/balloon notifications.

---

## 2. Interactive CLI Shortcuts

| Slash Command | Target Controller | Output |
|---|---|---|
| `/sys` or `/hw` | `hardware_controller.py` | CPU, RAM, Disk, Battery, OS summary |
| `/apps` | `app_controller.py` | Running desktop apps with PIDs and memory |
| `/net` | `network_controller.py` | IP addresses and active listening connections |
| `/svc` | `service_controller.py` | Operating system services and states |
| `/proc` | `process_controller.py` | Top running processes sorted by CPU |
| `/term <cmd>` | `terminal_tools.py` | Direct terminal execution with safety checks |
