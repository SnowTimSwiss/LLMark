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

    def __init__(self, test_model, hardware_info):
        super().__init__()
        self.test_model = test_model
        self.hardware_info = hardware_info
        self.client = OllamaClient()
        self.runner = BenchmarkRunner(self.client)
        self.running = True

    def run(self):
        full_results = {
            "model": self.test_model,
            "date": self.hardware_info['date_utc'],
            "system": self.hardware_info,
            "judge_model": JUDGE_MODEL,
            "benchmark_version": "v1",
            "json_format_version": "v1",
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

        full_results["model_details"] = {
            "quantization": details.get("quantization_level"),
            "context_length": m_info.get("llama.context_length") or params.get("num_ctx"),
            "parameter_size": details.get("parameter_size"),
            "family": details.get("family")
        }

        # 1. Benchmark A: Speed (Remains separate as it measures performance)
        if self.running:
            self.progress_update.emit("A", "Messe Geschwindigkeit...")
            self.verbose_log.emit("--- STARTE BENCHMARK A (SPEED) ---")
            
            monitor = HardwareMonitor()
            monitor.start()
            
            res_a = self.runner.run_benchmark("A", self.test_model, progress_callback=lambda m: self.progress_update.emit("A", m))
            
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

        # 2. Phase: Generation (B-J)
        pending_benchmarks = ["B", "C", "D", "E", "F", "G", "H", "I", "J"]
        generated_responses = {}
        
        self.verbose_log.emit("\n--- STARTE PHASE 2: GENERIERUNG (B-J) ---")
        
        for b_id in pending_benchmarks:
            if not self.running: break
            self.progress_update.emit(b_id, "Generiere Antwort...")
            
            bench_def = self.runner.get_benchmark_def(b_id)
            self.verbose_log.emit(f"\n[Bench {b_id}] Prompt:\n{bench_def.get('prompt', '')}")
            self.verbose_log.emit(f"[Bench {b_id}] Antwort:\n")
            
            # Record VRAM for each generation
            monitor = HardwareMonitor()
            monitor.start()
            
            stream_gen, error = self.runner.generate_response(b_id, self.test_model, stream=True)
            
            full_response = ""
            if error:
                self.verbose_log.emit(f"\n[Bench {b_id}] Fehler: {error}")
                generated_responses[b_id] = {"error": error}
            else:
                try:
                    for chunk in stream_gen:
                        if not self.running: break
                        if "error" in chunk:
                            error = chunk["error"]
                            break
                        
                        text = chunk.get("response", "")
                        full_response += text
                        self.stream_chunk.emit(text)
                        
                        if chunk.get("done"):
                            break
                except Exception as e:
                    error = str(e)
                
                monitor.stop()
                
                if error:
                    self.verbose_log.emit(f"\n[Bench {b_id}] Fehler beim Streamen: {error}")
                    generated_responses[b_id] = {"error": error}
                else:
                    self.verbose_log.emit("\n[Bench " + b_id + "] Generierung abgeschlossen.")
                    generated_responses[b_id] = {
                        "response": full_response,
                        "metrics": {
                            "peak_vram_mb": monitor.peak_vram,
                            "avg_vram_mb": round(sum(monitor.samples)/len(monitor.samples), 2) if monitor.samples else 0,
                            "gpu_detected": monitor.peak_vram > 500
                        }
                    }
        # 3. Phase: Judging (B-F)
        self.verbose_log.emit("\n--- STARTE PHASE 3: BEWERTUNG (JUDGE) ---")
        
        total_score = 0
        for b_id in pending_benchmarks:
            if not self.running: break
            self.progress_update.emit(b_id, "Warte auf Judge Bewertung...")
            
            data = generated_responses.get(b_id)
            if not data or "error" in data:
                res = {"score": 0, "comment": f"Generation Error: {data.get('error', 'Unknown')}", "issues": [], "metrics": {}}
                self.verbose_log.emit(f"[Bench {b_id}] Überspringe Judge wegen Vorfehler.")
            else:
                self.verbose_log.emit(f"[Bench {b_id}] Judge bewertet...")
                res = self.runner.judge_response(b_id, data["response"])
                self.verbose_log.emit(f"[Bench {b_id}] Judge Ergebnis:\n{json.dumps(res, indent=2, ensure_ascii=False)}")
                res["metrics"] = data["metrics"] # Carry over generation metrics

            if "id" not in res:
                res["id"] = b_id
            if "name" not in res or res["name"] == b_id:
                bench_def = self.runner.get_benchmark_def(b_id)
                res["name"] = bench_def.get("name", b_id)
            
            full_results['benchmarks'].append(res)
            self.benchmark_finished.emit(b_id, res)
            total_score += res.get('score', 0)

        self.verbose_log.emit("\n--- ALLE BENCHMARKS ABGESCHLOSSEN ---")
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
