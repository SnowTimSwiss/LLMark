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
            
            # Add VRAM metrics to result
            if "error" not in res_a:
                res_a['id'] = "A"
                res_a['name'] = "Velocity/Speed"
                res_a['metrics'] = {
                    "peak_vram_mb": monitor.peak_vram,
                    "avg_vram_mb": avg_vram,
                    "gpu_detected": monitor.peak_vram > 500
                }
            
            full_results['benchmarks'].append(res_a)
            full_results['model_estimated_vram_usage_mb'] = avg_vram
            self.benchmark_finished.emit("A", res_a)

        # 2. Phase: Generation (B-X) - Batch Execution
        categories = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "W", "X"]
        
        # Flat list of all subtasks to run
        all_subtasks = []
        for cat_id in categories:
            for i in range(1, 4):
                all_subtasks.append(f"{cat_id}{i}")
                
        generated_responses = {} # Key: subtask_id (e.g. "B1")
        
        self.verbose_log.emit(f"\n--- STARTE PHASE 2: BATCH GENERIERUNG ({len(all_subtasks)} Tasks) ---")
        
        for task_id in all_subtasks:
            if not self.running: break
            self.progress_update.emit(task_id, "Generiere Antwort...")
            
            # Use get_task_def to find prompt
            cat_id = task_id[0]
            t_id = task_id[1]
            task_def = self.runner.get_task_def(cat_id, t_id)
            
            self.verbose_log.emit(f"\n[Task {task_id}] Prompt: {task_def.get('task_desc', '')}")
            
            # Record VRAM for each generation (only for the test model, NOT the judge)
            monitor = HardwareMonitor()
            monitor.start()
            
            stream_gen, error = self.runner.generate_response(task_id, self.test_model, options=runner_options, stream=True)
            
            full_response = ""
            if error:
                self.verbose_log.emit(f"\n[Task {task_id}] Fehler: {error}")
                generated_responses[task_id] = {"error": error}
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
                
                if error:
                    self.verbose_log.emit(f"\n[Task {task_id}] Fehler beim Streamen: {error}")
                    generated_responses[task_id] = {"error": error}
                else:
                    self.verbose_log.emit(f"\n[Task {task_id}] Fertig.")
                    generated_responses[task_id] = {
                        "response": full_response,
                        "metrics": {
                            "peak_vram_mb": monitor.peak_vram,
                            "avg_vram_mb": round(sum(monitor.samples)/len(monitor.samples), 2) if monitor.samples else 0,
                            "gpu_detected": monitor.peak_vram > 500
                        }
                    }
            
            # IMPORTANT: Stop monitor BEFORE judging to avoid measuring the judge model's VRAM
            monitor.stop()


        # 3. Phase: Judging (Batch)
        self.verbose_log.emit("\n--- STARTE PHASE 3: BATCH BEWERTUNG ---")
        
        # We process by category to emit results as whole blocks
        judged_subtasks = {} # Key: subtask_id -> Result Dict
        
        for task_id in all_subtasks:
            if not self.running: break
            self.progress_update.emit(task_id, "Judge bewertet...")
            
            data = generated_responses.get(task_id)
            if not data or "error" in data:
                res = {"id": task_id, "score": 0, "comment": f"Gen Error: {data.get('error', '?')}", "issues": []}
            else:
                self.verbose_log.emit(f"[Task {task_id}] Bewerytung läuft...")
                res = self.runner.judge_response(task_id, data["response"])
                res["metrics"] = data["metrics"]
            
            # Add ID/Name if missing
            res["id"] = task_id
            cat_id = task_id[0]
            t_id = task_id[1]
            task_def = self.runner.get_task_def(cat_id, t_id)
            res["name"] = task_def.get("name", task_id)
            
            judged_subtasks[task_id] = res

        # 4. Aggregation & Emission
        self.verbose_log.emit("\n--- AGGREGATION ---")
        
        total_score = 0
        for cat_id in categories:
             if not self.running: break
             
             # Collect 3 subtasks
             cat_results = []
             for i in range(1, 4):
                 tid = f"{cat_id}{i}"
                 if tid in judged_subtasks:
                     cat_results.append(judged_subtasks[tid])
            
             # Compile Result
             final_res = self.runner.compile_category_result(cat_id, cat_results)
             
             # Emit to UI
             full_results['benchmarks'].append(final_res)
             self.benchmark_finished.emit(cat_id, final_res)
             
             total_score += final_res.get('score', 0)

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
                self.finished.emit(False, "Unknown error during pull")
        except Exception as e:
            self.finished.emit(False, str(e))

class ContinuousTestWorker(QThread):
    status_update = Signal(str)
    progress_update = Signal(str, int) # task, percent
    log_update = Signal(str)
    error_occurred = Signal(str)
    all_finished = Signal()

    def __init__(self, token, models, hardware_info, context_window=None):
        super().__init__()
        self.token = token
        self.models = models
        self.hardware_info = hardware_info
        self.context_window = context_window
        self.client = OllamaClient()
        self.running = True

    def run(self):
        from backend.benchmarks import BenchmarkRunner, JUDGE_MODEL
        from backend.contribution import ContributionManager
        
        runner = BenchmarkRunner(self.client)
        contrib = ContributionManager()

        # 1. Ensure Judge is present
        if not self.client.check_model_availability(JUDGE_MODEL):
            self.status_update.emit(f"Pulling Judge: {JUDGE_MODEL}")
            self.log_update.emit(f"Pulling Judge: {JUDGE_MODEL}...")
            
            pull_error = [None]
            def pull_cb(data):
                if "error" in data:
                    pull_error[0] = data["error"]
                elif "total" in data and data["total"] > 0:
                    percent = int((data["completed"] / data["total"]) * 100)
                    self.progress_update.emit(f"Pulling Judge", percent)
            
            success = self.client.pull_model(JUDGE_MODEL, progress_callback=pull_cb)
            if not success or pull_error[0]:
                self.error_occurred.emit(f"Could not pull judge model {JUDGE_MODEL}: {pull_error[0] or 'Unknown error'}")
                return

        # 2. Run through models once
        for model in self.models:
            if not self.running:
                break

            self.status_update.emit(f"Current Model: {model}")
            self.log_update.emit(f"\n--- Starting automated test for {model} ---")

            # A. Pull Model
            if not self.client.check_model_availability(model):
                self.log_update.emit(f"Pulling {model}...")
                
                model_pull_error = [None]
                def model_pull_cb(data):
                    if "error" in data:
                        model_pull_error[0] = data["error"]
                    elif "total" in data and data["total"] > 0:
                        percent = int((data["completed"] / data["total"]) * 100)
                        self.progress_update.emit(f"Pulling {model}", percent)
                
                success = self.client.pull_model(model, progress_callback=model_pull_cb)
                if not success or model_pull_error[0]:
                    self.log_update.emit(f"Failed to pull {model} ({model_pull_error[0] or 'Unknown error'}), skipping to next model...")
                    continue

            # B. Run Benchmark
            self.log_update.emit(f"Running benchmark for {model}...")
            
            # Refresh hardware info for correct timestamp
            from backend.hardware import get_hardware_info
            current_hw = get_hardware_info()
            
            full_results = {
                "model": model,
                "date": current_hw['date_utc'],
                "system": current_hw,
                "judge_model": JUDGE_MODEL,
                "benchmark_version": "v2",
                "json_format_version": "v2",
                "benchmarks": [],
                "total_score": 0
            }

            model_info = self.client.show_model_info(model)
            details = model_info.get("details", {})
            m_info = model_info.get("model_info", {})
            
            full_results["model_details"] = {
                "quantization": details.get("quantization_level"),
                "context_length": self.context_window or m_info.get("llama.context_length"),
                "parameter_size": details.get("parameter_size"),
                "family": details.get("family")
            }

            runner_options = {}
            if self.context_window:
                runner_options["num_ctx"] = int(self.context_window)

            # Benchmark A
            res_a = runner.run_benchmark("A", model, options=runner_options)
            res_a['id'] = "A"
            res_a['name'] = "Velocity/Speed"
            full_results['benchmarks'].append(res_a)

            # Benchmarks B-X
            categories = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "W", "X"]
            all_subtasks = [f"{c}{i}" for c in categories for i in range(1,4)]
            
            gen_responses = {}
            for tid in all_subtasks:
                if not self.running: break
                self.progress_update.emit(f"Gen {tid}", 0)
                resp, err = runner.generate_response(tid, model, options=runner_options)
                gen_responses[tid] = {"response": resp, "error": err}

            if not self.running: break

            total_score = 0
            for cat_id in categories:
                cat_results = []
                for i in range(1, 4):
                    tid = f"{cat_id}{i}"
                    data = gen_responses.get(tid, {})
                    if data.get("error"):
                        res = {"id": tid, "score": 0, "comment": f"Error: {data['error']}"}
                    else:
                        res = runner.judge_response(tid, data["response"])
                    
                    res["id"] = tid
                    td = runner.get_task_def(cat_id, str(i))
                    res["name"] = td.get("name", tid)
                    cat_results.append(res)
                
                final_res = runner.compile_category_result(cat_id, cat_results)
                full_results['benchmarks'].append(final_res)
                total_score += final_res.get('score', 0)

            full_results['total_score'] = total_score

            # C. Upload
            self.log_update.emit(f"Uploading results for {model}...")
            try:
                pr_url = contrib.upload_authenticated(self.token, full_results)
                self.log_update.emit(f"Successfully uploaded! PR: {pr_url}")
            except Exception as e:
                self.log_update.emit(f"Upload failed: {e}")

        self.log_update.emit("\nAll automated tests completed.")
        self.all_finished.emit()

    def stop(self):
        self.running = False
