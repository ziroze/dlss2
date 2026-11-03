import platform, shutil, socket
import psutil

ALLOWED_OPERATIONS = {"system_info", "resource_usage", "disk_usage", "network_summary"}

def run_diagnostic(operation: str, arguments: dict | None = None) -> dict:
    if operation not in ALLOWED_OPERATIONS:
        raise ValueError("Diagnostic operation is not allowed")
    args = arguments or {}
    if args:
        raise ValueError("This diagnostic accepts no arguments")
    if operation == "system_info":
        return {"hostname": socket.gethostname(), "platform": platform.platform(),
                "system": platform.system(), "release": platform.release(),
                "architecture": platform.machine(), "python": platform.python_version(),
                "cpu_count": psutil.cpu_count(logical=True)}
    if operation == "resource_usage":
        vm = psutil.virtual_memory()
        return {"cpu_percent": psutil.cpu_percent(interval=0.2),
                "memory_total": vm.total, "memory_available": vm.available,
                "memory_percent": vm.percent, "boot_time": psutil.boot_time()}
    if operation == "disk_usage":
        usage = shutil.disk_usage("/")
        return {"path": "/", "total": usage.total, "used": usage.used,
                "free": usage.free, "percent": round(usage.used / usage.total * 100, 2)}
    if operation == "network_summary":
        counters = psutil.net_io_counters()
        return {"bytes_sent": counters.bytes_sent, "bytes_received": counters.bytes_recv,
                "packets_sent": counters.packets_sent, "packets_received": counters.packets_recv}
    raise ValueError("Unsupported diagnostic")
