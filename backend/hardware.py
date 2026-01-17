import platform
import psutil
import datetime
import warnings
import subprocess
import re

# Suppress pynvml deprecation warning
warnings.filterwarnings("ignore", category=FutureWarning, message="The pynvml package is deprecated")

try:
    import pynvml
except ImportError:
    pynvml = None
import cpuinfo

def get_vram_usage_mb():
    """
    Returns current global VRAM usage in MB.
    Tries NVIDIA first, then Windows Counters.
    """
    # NVIDIA
    if pynvml:
        try:
            pynvml.nvmlInit()
            if pynvml.nvmlDeviceGetCount() > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                pynvml.nvmlShutdown()
                return round(mem.used / 1024 / 1024, 2)
        except:
            pass
    
    # Windows Counters (AMD/Intel/Generic)
    if platform.system() == "Windows":
        try:
            # Check Dedicated Usage
            cmd = "powershell \"(Get-Counter '\\GPU Adapter Memory(*)\\Dedicated Usage' -ErrorAction SilentlyContinue).CounterSamples.CookedValue | Measure-Object -Sum | Select-Object -ExpandProperty Sum\""
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(cmd, shell=True, startupinfo=startupinfo).decode('utf-8', errors='ignore').strip()
            if output:
                val = float(output.replace(',', '.'))
                return round(val / 1024 / 1024, 2)
        except:
            pass
    return 0.0

def get_hardware_info():
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": "Unknown",
        "ram_total_gb": 0.0,
        "gpu": None,
        "vram_total_mb": None,
        "vram_used_mb": None,
        "date_utc": datetime.datetime.utcnow().isoformat()
    }

    # CPU
    try:
        cpu_info = cpuinfo.get_cpu_info()
        info['cpu'] = cpu_info.get('brand_raw', platform.processor())
    except Exception:
        info['cpu'] = platform.processor()

    # RAM
    try:
        info['ram_total_gb'] = round(psutil.virtual_memory().total / (1024 ** 3), 2)
    except Exception:
        pass

    # GPU (NVIDIA via pynvml)
    gpu_found = False
    try:
        if pynvml:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                info['gpu'] = name
                
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                info['vram_total_mb'] = round(mem_info.total / 1024 / 1024, 2)
                gpu_found = True
            pynvml.nvmlShutdown()
    except Exception:
        pass

    if not gpu_found and platform.system() == "Windows":
        # AMD / Generic via Registry key for accurate VRAM size (using winreg)
        try:
            import winreg
            
            # 1. Get Name via CIM (fallback if winreg lookup fails to match)
            # Keeping this for info['gpu'] name if not set
            if not info['gpu']:
                 try:
                    cmd_name = "powershell \"Get-CimInstance Win32_VideoController | Select-Object -First 1 Name | Select-Object -ExpandProperty Name\""
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    name_out = subprocess.check_output(cmd_name, shell=True, startupinfo=startupinfo).decode('utf-8', errors='ignore').strip()
                    if name_out:
                         info['gpu'] = name_out
                 except:
                     pass

            # 2. Get Accurate VRAM Size via Registry
            # iterate keys in HKLM\SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}
            key_path = r"SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                    count = winreg.QueryInfoKey(key)[0]
                    max_vram = 0
                    
                    for i in range(count):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    # HardwareInformation.qwMemorySize is a QWORD
                                    vram_size, val_type = winreg.QueryValueEx(subkey, "HardwareInformation.qwMemorySize")
                                    # Sometimes it's bytes, sometimes 0 if not dedicated
                                    if vram_size and isinstance(vram_size, int) and vram_size > 0:
                                        if vram_size > max_vram:
                                            max_vram = vram_size
                                except FileNotFoundError:
                                    # Property doesn't exist on this adapter entry (e.g. basic render driver)
                                    pass
                        except Exception:
                            pass
                    
                    if max_vram > 0:
                        info['vram_total_mb'] = round(max_vram / 1024 / 1024, 2)
                        
            except Exception as e:
                # Permission error or path missing
                pass

        except Exception:
             pass

    # Current usage
    info['vram_used_mb'] = get_vram_usage_mb()

    return info

    return info
