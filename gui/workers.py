import json
from PySide6.QtCore import QThread, Signal
from backend.ollama_client import OllamaClient
from backend.benchmarks import BenchmarkRunner, JUDGE_MODEL

class HardwareMonitor(QThread):
    vram_updated = Signal(float)

    def __init__(self, interval=0.5):
        super().__init__()
        self.interval = interval
        self.running = True
        self.peak_vram = 0.0
        self.samples = []

    def run(self):
        from backend.hardware import get_vram_usage_mb
        while self.running:
            vram = get_vram_usage_mb()
            if vram > self.peak_vram:
                self.peak_vram = vram
            self.samples.append(vram)
            self.vram_updated.emit(vram)
            self.msleep(int(self.interval * 1000))

    def stop(self):
        self.running = False
        self.wait()


class BenchmarkWorker(QThread):
    progress_update = Signal(str, str) # bench_id, message
    verbose_log = Signal(str) # detailed log message
    stream_chunk = Signal(str) # partial response chunk
    benchmark_finished = Signal(str, dict) # bench_id, result
    all_finished = Signal(dict) # full results
    error_occurred = Signal(str)

    def __init__(self, test_model, hardware_info, context_window=None):
        super().__init__()
        self.test_model = test_model
        self.hardware_info = hardware_info
        self.context_window = context_window
        self.client = OllamaClient()
        self.runner = BenchmarkRunner(self.client)
        self.running = True

    def run(self):
        full_results = {
            "model": self.test_model,
            "date": self.hardware_info['date_utc'],
            "system": self.hardware_info,
            "judge_model": JUDGE_MODEL,
            "benchmark_version": "v2",
            "json_format_version": "v2",
            "benchmarks": [],
            "total_score": 0
        }

        # Fetch Model Info (Quantization, Context etc)
        model_info = self.client.show_model_info(self.test_model)
        
        details = model_info.get("details", {})
        if not isinstance(details, dict): details = {}
        
        m_info = model_info.get("model_info", {})
        if not isinstance(m_info, dict): m_info = {}
        
        params = model_info.get("parameters", {})
        if not isinstance(params, dict): params = {}

        m_ctx = m_info.get("llama.context_length")
        if not m_ctx and isinstance(params, str):
            import re
            match = re.search(r"num_ctx\s+(\d+)", params)
            if match:
                m_ctx = int(match.group(1))

        # Override with user setting if provided
        final_context = self.context_window if self.context_window else m_ctx

        full_results["model_details"] = {
            "quantization": details.get("quantization_level"),
            "context_length": final_context,
            "parameter_size": details.get("parameter_size"),
            "family": details.get("family")
        }

        # Set runner options
        runner_options = {}
        if self.context_window:
            runner_options["num_ctx"] = int(self.context_window)

        # 1. Benchmark A: Speed (Remains separate as it measures performance)
        if self.running:
            self.progress_update.emit("A", "Messe Geschwindigkeit...")
            self.verbose_log.emit("--- STARTE BENCHMARK A (SPEED) ---")
            
            monitor = HardwareMonitor()
            monitor.start()
            
            res_a = self.runner.run_benchmark("A", self.test_model, options=runner_options, progress_callback=lambda m: self.progress_update.emit("A", m))
            
            monitor.stop()
            
            if "error" not in res_a:
                self.verbose_log.emit(f"Antwort erhalten ({res_a.get('comment', '')})")
            
            avg_vram = round(sum(monitor.samples)/len(monitor.samples), 2) if monitor.samples else 0
            if "error" not in res_a:
                res_a['id'] = "A"
                res_a['name'] = "Velocity/Speed"
            full_results['benchmarks'].append(res_a)
            full_results['model_estimated_vram_usage_mb'] = avg_vram
            self.benchmark_finished.emit("A", res_a)

        # 2. Phase: Generation (B-X)
        pending_benchmarks = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "W", "X"]
        generated_responses = {}
        
        self.verbose_log.emit("\n--- STARTE PHASE 2: GENERIERUNG (B-X) ---")
        
        for b_id in pending_benchmarks:
            if not self.running: break
            self.progress_update.emit(b_id, "Generiere Antwort...")
            
            # Retrieve category definition clearly (v2 fix)
            bench_def = self.runner.get_category_def(b_id)
            # prompt isn't directly in category_def in v2, it manages sub-tasks
            # For logging, we'll just say we are starting the category
            self.verbose_log.emit(f"\n[Bench {b_id}] Starte Kategorie: {bench_def.get('name', b_id)}")
            
            # Record VRAM for each generation
            monitor = HardwareMonitor()
            monitor.start()
            
            # In benchmarks v2, run_benchmark/run_category handles generation internally for sub-tasks
            # So we don't stream here easily without refactoring benchmarks.py to stream 3 tasks
            # Revert to calling run_benchmark directly which returns the full result with avg score
            # BUT wait, the previous code streamed chunks.
            # benchmarks v2 `run_benchmark` calls `_run_content_task` or `_run_category`.
            # `_run_category` runs 3 tasks sequentially.
            # We lose streaming if we just call `run_benchmark(category)`.
            # However, adapting to v2 FULLY means using `run_benchmark` which orchestrates the 3 tasks.
            # To keep it simple and working: we call `run_benchmark` directly.
            # We lose "live streaming" of text unless we pass a callback, but benchmarks.py progress_callback only takes strings.
            
            # Let's use the runner to do the work.
            
            res = self.runner.run_benchmark(b_id, self.test_model, options=runner_options, progress_callback=lambda m: self.progress_update.emit(b_id, m))
            
            monitor.stop()
            
            # Logic for result handling
            if "error" in res:
                 self.verbose_log.emit(f"\n[Bench {b_id}] Fehler: {res.get('error')}")
            else:
                 self.verbose_log.emit(f"\n[Bench {b_id}] Abgeschlossen. Score: {res.get('score')}")

            # Add metrics placeholders if missing (since run_benchmark might not set them all same way)
            if "metrics" not in res:
                res["metrics"] = {
                    "peak_vram_mb": monitor.peak_vram,
                    "avg_vram_mb": round(sum(monitor.samples)/len(monitor.samples), 2) if monitor.samples else 0,
                    "gpu_detected": monitor.peak_vram > 500
                }

            # Ensure Name is correct for JSON
            if "name" not in res or res["name"] == b_id:
                res["name"] = bench_def.get("name", b_id)
                
            full_results['benchmarks'].append(res)
            self.benchmark_finished.emit(b_id, res)
            
            # Accumulate total score (run_category already computes avg for the category)
            # we do this at the end

        self.verbose_log.emit("\n--- ALLE BENCHMARKS ABGESCHLOSSEN ---")
        
        # Calculate total score based on what we have in full_results
        total_score = sum(b.get('score', 0) for b in full_results['benchmarks'] if b.get('id') not in ["A"])
        full_results['total_score'] = total_score
        
        self.all_finished.emit(full_results)

class PullWorker(QThread):
    progress_update = Signal(str, int) # message, percent
    finished = Signal(bool, str) # success, message

    def __init__(self, model_name):
        super().__init__()
        self.model_name = model_name
        self.client = OllamaClient()

    def run(self):
        def cb(data):
            if "error" in data:
                self.finished.emit(False, data["error"])
                return
            
            status = data.get("status", "")
            total = data.get("total", 0)
            completed = data.get("completed", 0)
            
            percent = 0
            if total > 0:
                percent = int((completed / total) * 100)
            
            self.progress_update.emit(f"{status}", percent)

        try:
            success = self.client.pull_model(self.model_name, progress_callback=cb)
            if success:
                self.finished.emit(True, "Installation complet.")
            else:
                # Callback usually emits error, but safeguard
                self.finished.emit(False, "Unknown error during pull")
        except Exception as e:
            self.finished.emit(False, str(e))
