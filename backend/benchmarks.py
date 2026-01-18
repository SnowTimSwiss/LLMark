"""
benchmark_runner.py
Einfache 1-10 Punkte Version von BenchmarkRunner für Ollama-Modelle
"""

import time
import json
from .ollama_client import OllamaClient

JUDGE_MODEL = "qwen2.5:14b-instruct"
JUDGE_OPTIONS = {"temperature": 0.0, "top_p": 1.0}

class BenchmarkRunner:
    def __init__(self, client: OllamaClient):
        self.client = client

    # -------------------- PUBLIC --------------------

    def run_benchmark(self, bench_id: str, test_model: str, progress_callback=None):
        bench_id = bench_id.upper()
        if bench_id == "A":
            return self._run_speed(test_model, progress_callback)
        elif bench_id in list("BCDEFGHIJ"):
            return self._run_content(bench_id, test_model, progress_callback)
        else:
            return {"error": "Unknown benchmark id"}

    # -------------------- SPEED --------------------

    def _run_speed(self, test_model, progress_callback=None):
        if progress_callback:
            progress_callback("Warmup (speed)...")

        prompt = "Write the numbers from one to one thousand in English words without explanations."

        # Warmup
        try:
            _ = self.client.generate(test_model, prompt, stream=False)
        except Exception:
            pass

        if progress_callback:
            progress_callback("Measuring speed...")

        start_t = time.time()
        res = self.client.generate(test_model, prompt, stream=False)
        end_t = time.time()
        elapsed = max(end_t - start_t, 1e-9)

        eval_count = res.get("eval_count") or res.get("tokens") or len((res.get("response") or "").split())
        eval_duration_ns = res.get("eval_duration", 0)
        tps = (eval_count / eval_duration_ns) * 1_000_000_000 if eval_duration_ns else eval_count / elapsed

        return {
            "name": "A",
            "description": "Velocity/Speed",
            "score": round(tps, 2), # TPS is the "score" now
            "comment": f"{round(tps,2)} tokens/sec",
            "details": {"tokens": int(eval_count), "total_time_s": round(elapsed, 3), "tokens_per_sec": round(tps, 2)},
            "metrics": {
                "avg_vram_mb": res.get("avg_vram_mb"),
                "peak_vram_mb": res.get("peak_vram_mb"),
                "gpu_detected": res.get("gpu_detected")
            },
            "raw_response_preview": (res.get("response") or "")[:200]
        }

    # -------------------- CONTENT BENCHMARKS --------------------

    def generate_response(self, bench_id, test_model, stream=False):
        bench_def = self.get_benchmark_def(bench_id)
        try:
            return self.client.generate(test_model, bench_def["prompt"], stream=stream), None
        except Exception as e:
            return None if stream else "", str(e)

    def judge_response(self, bench_id, model_text):
        bench_def = self.get_benchmark_def(bench_id)
        return self._judge_response(bench_id, model_text, bench_def)

    def _run_content(self, bench_id, test_model, progress_callback=None):
        if test_model == JUDGE_MODEL:
            return {"name": bench_id, "score": 0, "comment": "Test model must not equal judge model", "issues": []}

        if progress_callback:
            progress_callback(f"Generating response for benchmark {bench_id}...")

        text, error = self.generate_response(bench_id, test_model)
        if error:
            return {"name": bench_id, "score": 0, "comment": f"Generation error: {error}", "issues": [error]}

        if progress_callback:
            progress_callback(f"Judging benchmark {bench_id}...")

        judge_result = self.judge_response(bench_id, text)
        
        # Score bereits 1-10 vom Judge
        score = judge_result.get("score", 0)

        return {
            "name": bench_id,
            "description": bench_def.get("name", bench_id),
            "score": min(10, max(0, score)),
            "comment": judge_result.get("comment", f"Score: {score}/10"),
            "issues": judge_result.get("issues", []),
            "response_preview": text[:300],
            "judge_raw": judge_result
        }

    def _judge_response(self, bench_id, model_text, bench_def):
        facts_section = ""
        if "truths" in bench_def:
            facts_section = "\n".join([f"{i}. {fact} => {'CORRECT' if truth else 'INCORRECT'}"
                                       for i, (fact, truth) in enumerate(bench_def["truths"].items(), 1)])
        elif "facts" in bench_def:
            facts_section = "\n".join([f"{i}. {f}" for i, f in enumerate(bench_def["facts"],1)])
        else:
            facts_section = "Facts: none"

        rubric = (
            "Return ONLY a JSON object:\n"
            "{\n"
            "  \"score\": number (1-10, where 10 is perfect),\n"
            "  \"issues\": [...],\n"
            "  \"comment\": \"short summary with score explanation\"\n"
            "}\n\n"
            "Score guide:\n"
            "10: Perfect, meets all criteria\n"
            "8-9: Very good, minor issues\n"
            "6-7: Good, some issues\n"
            "4-5: Average, multiple issues\n"
            "2-3: Poor, many issues\n"
            "1: Very poor or incomplete"
        )

        system_prompt = (
            "You are a strict but fair benchmark judge. Evaluate objectively based on the criteria. "
            "Give a score from 1-10 where 10 is perfect. Output ONLY JSON."
        )

        judge_prompt = f"""
Benchmark: {bench_id}
Task: {bench_def.get('task_desc','')}

Facts / Truths:
{facts_section}

Model Answer:
---
{model_text}
---

Evaluation Criteria:
{bench_def.get('criteria', 'General quality assessment')}

{rubric}
"""
        try:
            judge_res = self.client.generate(JUDGE_MODEL, judge_prompt, system=system_prompt, options=JUDGE_OPTIONS, stream=False)
        except Exception as e:
            return {
                "score": 1,
                "issues": [f"Judge call failed: {e}"],
                "comment": "Judge call failed, minimal score assigned"
            }

        raw = judge_res.get("response") or ""
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            parsed = json.loads(raw[start:end+1])
            
            # Sicherstellen, dass Score 1-10 ist
            score = float(parsed.get("score", 1))
            parsed["score"] = min(10, max(1, round(score)))
            
        except Exception as e:
            return {
                "score": 1,
                "issues": [f"Judge JSON parse error: {e}", raw[:200]],
                "comment": "JSON parse error, minimal score assigned"
            }

        return parsed

    # -------------------- BENCH DEFINITIONS --------------------
    def get_benchmark_def(self, bench_id):
        defs = {
            "B": {
                "name": "English Quality",
                "prompt": (
                    "Write a formal business email reminding a customer of an overdue invoice.\n\n"
                    "Facts (10 minimum):\n"
                    "- Invoice number: INV-2024-019\n"
                    "- Original due date: 15 March 2024\n"
                    "- Outstanding amount: 1,250 EUR\n"
                    "- Payment is 30 days overdue\n"
                    "- Payment method: Bank transfer\n"
                    "- Customer Name: John Doe\n"
                    "- Customer Address: 12 Baker Street, London\n"
                    "- Company Name: ACME Corp.\n"
                    "- Company Contact Email: finance@acme.com\n"
                    "- Late fee policy applies after 45 days\n"
                    "- Currency and decimal format\n\n"
                    "Requirements:\n"
                    "- Professional and polite tone\n"
                    "- Clear subject line\n"
                    "- Explicit call to action with a deadline\n"
                    "- No casual language\n"
                    "- No threats of legal action"
                ),
                "task_desc": "Formal Business English Email with Explicit Facts (10+)",
                "criteria": (
                    "Score based on:\n"
                    "- All facts included correctly (2 points)\n"
                    "- Professional tone (2 points)\n"
                    "- Clear subject line (2 points)\n"
                    "- Explicit deadline/call to action (2 points)\n"
                    "- Overall quality and polish (2 points)\n"
                    "Deduct for:\n"
                    "- Missing or incorrect facts\n"
                    "- Unprofessional language\n"
                    "- Missing subject/deadline\n"
                    "- Redundant wording"
                )
            },

            "C": {
                "name": "German Quality",
                "prompt": (
                    "Verfassen Sie eine formelle Zahlungserinnerung auf Deutsch.\n\n"
                    "Facts (10+):\n"
                    "- Rechnungsnummer: RE-77821\n"
                    "- Rechnungsdatum: 01.02.2024\n"
                    "- Zahlungsziel: 15.02.2024\n"
                    "- Betrag: 860 CHF\n"
                    "- Zahlungsverzug: 45 Tage\n"
                    "- Firma: Muster GmbH\n"
                    "- Kunde: Max Mustermann\n"
                    "- Bankkontodetails: CH93 0076 2011 6238 5295 7\n"
                    "- Ort: Zürich\n"
                    "- Mahngebühren nach 30 Tagen\n"
                    "- Währung und Dezimalformat"
                    "\n\nAnforderungen:\n"
                    "- Formelle Anrede (Sie)\n"
                    "- Betreffzeile\n"
                    "- Klare Zahlungsfrist\n"
                    "- Sachlicher Ton\n"
                    "- Keine Umgangssprache"
                ),
                "task_desc": "Formelle deutsche Mahnung (10+ Fakten)",
                "criteria": (
                    "Score based on:\n"
                    "- All facts included correctly (3 points)\n"
                    "- Formal German (Sie-Anrede) (2 points)\n"
                    "- Clear subject line (2 points)\n"
                    "- Proper deadline (2 points)\n"
                    "- Grammar and style (1 point)\n"
                    "Deduct for:\n"
                    "- Informal language\n"
                    "- Missing facts\n"
                    "- Missing subject/deadline\n"
                    "- Grammar errors"
                )
            },

            "D": {
                "name": "Fact Checking",
                "prompt": (
                    "Evaluate each statement as CORRECT or FALSE and justify briefly:\n\n"
                    "Facts (10 minimum):\n"
                    "1. The Berlin Wall was built in 1961.\n"
                    "2. The Berlin Wall fell in 1989.\n"
                    "3. Water boils at a lower temperature at higher atmospheric pressure.\n"
                    "4. Napoleon lost the Battle of Waterloo.\n"
                    "5. Switzerland is a member of the EU.\n"
                    "6. Isaac Newton developed the law of universal gravitation.\n"
                    "7. The Earth is not a perfect circle.\n"
                    "8. Albert Einstein won the Nobel Prize in Physics in 1921.\n"
                    "9. Mount Everest is the highest mountain on Earth.\n"
                    "10. The UN was founded in 1945."
                ),
                "task_desc": "Strict Multi-Fact Checking (10+ Facts)",
                "criteria": (
                    "Score based on:\n"
                    "- Correct true/false judgment for each fact (1 point each, 10 total)\n"
                    "Deduct for:\n"
                    "- Incorrect judgment\n"
                    "- Poor reasoning\n"
                    "- Unnecessary verbosity"
                )
            },

            "E": {
                "name": "Context Extraction",
                "prompt": (
                    "Meeting Transcript:\n"
                    "Alex: Project X finished by Friday.\n"
                    "Sarah: API fix, need documentation from Tom.\n"
                    "Tom: On vacation until Monday.\n"
                    "Alex: Bernd takes over documentation until Wednesday.\n"
                    "Bernd: Server Error 500.\n"
                    "Alex: Next meeting Thursday 14:00.\n\n"
                    "Create:\n"
                    "1. Task list with responsible persons and deadlines\n"
                    "2. Open issues with impacts\n"
                    "3. Next meeting time\n"
                    "Facts: At least 10 specific points should be extracted."
                ),
                "task_desc": "Information Extraction (10+ Facts)",
                "criteria": (
                    "Score based on:\n"
                    "- All 10+ facts extracted correctly (5 points)\n"
                    "- Good structure/organization (3 points)\n"
                    "- Complete deadlines and responsibilities (2 points)\n"
                    "Deduct for:\n"
                    "- Missing facts\n"
                    "- Poor structure\n"
                    "- Incomplete information"
                )
            },

            "F": {
                "name": "Logic/Timetable",
                "prompt": (
                    "Create a complete timetable for two classes 1A, 2B.\n\n"
                    "Teachers:\n"
                    "- Müller: Math, Mon/Tue only\n"
                    "- Meier: German, Tue–Thu\n"
                    "- Schmidt: Sports, Mon–Fri\n\n"
                    "Rooms:\n"
                    "- R101: 08:00–10:00 only\n"
                    "- R102: all day\n\n"
                    "Subjects: Math 2x per week, German 2x, Sports 1x per class.\n"
                    "No double bookings for teachers or rooms.\n"
                    "Facts: At least 10 different constraints must be correctly fulfilled."
                ),
                "task_desc": "Constraint Satisfaction / Timetable (10+ Facts)",
                "criteria": (
                    "Score based on:\n"
                    "- All constraints satisfied (6 points)\n"
                    "- Complete timetable (2 points)\n"
                    "- No contradictions (2 points)\n"
                    "Deduct heavily for:\n"
                    "- Rule violations\n"
                    "- Incomplete schedule\n"
                    "- Contradictions"
                )
            },

            "G": {
                "name": "Creative Writing",
                "prompt": (
                    "Write the beginning of a story (approx. 200-300 words).\n"
                    "Genre: Cyberpunk-Noir.\n"
                    "Setting: A rain-soaked city in the year 2099.\n"
                    "Required terms (all must appear):\n"
                    "- neon umbrella\n"
                    "- defective replicant\n"
                    "- coffee machine\n\n"
                    "The story must end with a dramatic cliffhanger."
                ),
                "task_desc": "Creative Writing: Cyberpunk-Noir with Constraints",
                "criteria": (
                    "Score based on:\n"
                    "- All required terms included (3 points)\n"
                    "- Correct genre/atmosphere (3 points)\n"
                    "- Dramatic cliffhanger ending (2 points)\n"
                    "- Good writing style (2 points)\n"
                    "Deduct for:\n"
                    "- Missing required terms\n"
                    "- Wrong genre/atmosphere\n"
                    "- No cliffhanger\n"
                    "- Poor writing style"
                )
            },

            "H": {
                "name": "ELI5 Complexity",
                "prompt": (
                    "Explain the scientific concept of 'Quantum Entanglement' to an 8-year-old child.\n\n"
                    "Requirements:\n"
                    "- No complex technical terms without simple explanation\n"
                    "- Use an analogy with toys or everyday objects\n"
                    "- Max. 150 words\n"
                    "- The tone must be child-friendly and engaging"
                ),
                "task_desc": "Technical Simplification (ELI5): Quantum Entanglement",
                "criteria": (
                    "Score based on:\n"
                    "- Understandable for 8-year-old (4 points)\n"
                    "- Good analogy used (3 points)\n"
                    "- Correct scientific simplification (2 points)\n"
                    "- Appropriate tone/length (1 point)\n"
                    "Deduct for:\n"
                    "- Too complicated for children\n"
                    "- Missing analogy\n"
                    "- Scientific errors\n"
                    "- Wrong tone or too long"
                )
            },

            "I": {
                "name": "Python Coding",
                "prompt": (
                    "Write a Python function named 'is_valid_password(pw)' that checks a password.\n"
                    "Criteria for 'True':\n"
                    "1. At least 10 characters long\n"
                    "2. Contains at least one number\n"
                    "3. Contains at least one special character (e.g. !@#$%^&*)\n"
                    "4. Contains no spaces\n\n"
                    "The function must contain a docstring and show an example call at the end."
                ),
                "task_desc": "Python Programming: Password Validation",
                "criteria": (
                    "Score based on:\n"
                    "- Correct logic (4 points)\n"
                    "- All criteria checked (2 points each, 8 total)\n"
                    "- Docstring included (1 point)\n"
                    "- Example included (1 point)\n"
                    "Deduct for:\n"
                    "- Logical errors\n"
                    "- Missing criteria\n"
                    "- Missing docstring/example\n"
                    "- Poor naming/syntax"
                )
            },

            "J": {
                "name": "Customer Support",
                "prompt": (
                    "Situation: You are in the customer support of an airline.\n"
                    "Customer: 'My suitcase was lost! I'm in Paris and have a wedding tomorrow morning, "
                    "for which my suit was in the suitcase. This is an absolute catastrophe! What are you doing now?!'\n\n"
                    "Write a reply email (max. 200 words).\n"
                    "Requirements:\n"
                    "- Respond extremely empathically and de-escalating\n"
                    "- No standard phrases ('We apologize for the inconvenience') but real empathy\n"
                    "- Mention concrete next steps (tracking, compensation, emergency purchase option)\n"
                    "- Maintain professionalism"
                ),
                "task_desc": "Roleplay / De-escalation: Lost Suitcase",
                "criteria": (
                    "Score based on:\n"
                    "- Empathetic response (4 points)\n"
                    "- Concrete next steps (3 points)\n"
                    "- No hollow phrases (2 points)\n"
                    "- Professional style (1 point)\n"
                    "Deduct for:\n"
                    "- Defensive or unempathetic\n"
                    "- No concrete help\n"
                    "- Using standard phrases\n"
                    "- Unprofessional style"
                )
            }
        }
        return defs.get(bench_id, {})