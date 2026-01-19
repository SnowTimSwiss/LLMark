"""
benchmark_runner.py
Verbesserte 1-10 Punkte Benchmark-Suite für Ollama-Modelle
"""

import time
import json
import re
from .ollama_client import OllamaClient

JUDGE_MODEL = "qwen2.5:14b-instruct"
JUDGE_OPTIONS = {"temperature": 0.0, "top_p": 1.0}

class BenchmarkRunner:
    def __init__(self, client: OllamaClient):
        self.client = client

    # -------------------- PUBLIC --------------------

    def run_benchmark(self, bench_id: str, test_model: str, options=None, progress_callback=None):
        bench_id = bench_id.upper()
        
        # Speed Test bleibt gleich
        if bench_id == "A":
            return self._run_speed(test_model, options=options, progress_callback=progress_callback)
        
        # Kategorie-Tests (mehrere Tasks pro Kategorie)
        elif bench_id in ["B1", "B2", "B3"]:
            category = "B"
            task_id = bench_id[1]
            return self._run_content_task(category, task_id, test_model, options, progress_callback)
        
        elif bench_id in ["C1", "C2", "C3"]:
            category = "C"
            task_id = bench_id[1]
            return self._run_content_task(category, task_id, test_model, options, progress_callback)
        
        elif bench_id in ["D1", "D2", "D3"]:
            category = "D"
            task_id = bench_id[1]
            return self._run_content_task(category, task_id, test_model, options, progress_callback)
        
        elif bench_id in ["E1", "E2", "E3"]:
            category = "E"
            task_id = bench_id[1]
            return self._run_content_task(category, task_id, test_model, options, progress_callback)
        
        elif bench_id in ["F1", "F2", "F3"]:
            category = "F"
            task_id = bench_id[1]
            return self._run_content_task(category, task_id, test_model, options, progress_callback)
        
        elif bench_id in ["G1", "G2", "G3"]:
            category = "G"
            task_id = bench_id[1]
            return self._run_content_task(category, task_id, test_model, options, progress_callback)
        
        elif bench_id in ["H1", "H2", "H3"]:
            category = "H"
            task_id = bench_id[1]
            return self._run_content_task(category, task_id, test_model, options, progress_callback)
        
        elif bench_id in ["I1", "I2", "I3"]:
            category = "I"
            task_id = bench_id[1]
            return self._run_content_task(category, task_id, test_model, options, progress_callback)
        
        elif bench_id in ["J1", "J2", "J3"]:
            category = "J"
            task_id = bench_id[1]
            return self._run_content_task(category, task_id, test_model, options, progress_callback)
        
        # Neue Kategorien
        elif bench_id in ["W1", "W2", "W3"]:  # Knowledge
            category = "W"
            task_id = bench_id[1]
            return self._run_content_task(category, task_id, test_model, options, progress_callback)
        
        elif bench_id in ["X1", "X2", "X3"]:  # Hallucination/Uncertainty
            category = "X"
            task_id = bench_id[1]
            return self._run_content_task(category, task_id, test_model, options, progress_callback)
        
        # Komplette Kategorie-Runs (Durchschnitt aller Tasks)
        elif bench_id in list("BCDEFGHIJWX"):
            return self._run_category(bench_id, test_model, options, progress_callback)
        
        else:
            return {"error": "Unknown benchmark id"}

    def run_category(self, category_id: str, test_model: str, options=None, progress_callback=None):
        """Führt alle Tasks einer Kategorie aus und gibt Durchschnitt zurück"""
        category_id = category_id.upper()
        
        if category_id == "A":
            return self._run_speed(test_model, options=options, progress_callback=progress_callback)
        
        # Tasks der Kategorie bestimmen
        if category_id == "B":
            task_ids = ["B1", "B2", "B3"]
        elif category_id == "C":
            task_ids = ["C1", "C2", "C3"]
        elif category_id == "D":
            task_ids = ["D1", "D2", "D3"]
        elif category_id == "E":
            task_ids = ["E1", "E2", "E3"]
        elif category_id == "F":
            task_ids = ["F1", "F2", "F3"]
        elif category_id == "G":
            task_ids = ["G1", "G2", "G3"]
        elif category_id == "H":
            task_ids = ["H1", "H2", "H3"]
        elif category_id == "I":
            task_ids = ["I1", "I2", "I3"]
        elif category_id == "J":
            task_ids = ["J1", "J2", "J3"]
        elif category_id == "W":
            task_ids = ["W1", "W2", "W3"]
        elif category_id == "X":
            task_ids = ["X1", "X2", "X3"]
        else:
            return {"error": "Unknown category"}
        
        results = []
        total_score = 0
        
        for i, task_id in enumerate(task_ids):
            if progress_callback:
                progress_callback(f"Running {task_id} ({i+1}/{len(task_ids)})...")
            
            result = self._run_content_task(category_id, task_id[1], test_model, options, None)
            results.append(result)
            
        return self.compile_category_result(category_id, results)

    def compile_category_result(self, category_id, results):
        """Erstellt das Kategorie-Ergebnis aus den Einzel-Ergebnissen"""
        total_score = sum(r.get("score", 0) for r in results)
        avg_score = round(total_score / len(results), 2) if results else 0
        
        # Summary Generation
        summary = []
        
        # 1. Overall Impression
        if avg_score >= 9.0:
            summary.append("Excellent performance.")
        elif avg_score >= 7.5:
            summary.append("Good performance.")
        elif avg_score >= 5.0:
            summary.append("Mixed results.")
        else:
            summary.append("Poor performance.")
            
        # 2. Issues (from lowest scoring task)
        sorted_by_score = sorted(results, key=lambda r: r.get("score", 0))
        worst = sorted_by_score[0] if sorted_by_score else None
        
        if worst and worst.get("score", 0) < 9:
            issues = worst.get("issues", [])
            if issues:
                # Take first issue
                issue_text = issues[0]
                summary.append(f"Issue ({worst['id']}): {issue_text}")
            elif worst.get("comment"):
                 # Fallback to judge comment if no issues list
                 comm = worst.get("comment")
                 summary.append(f"Note ({worst['id']}): {comm}")
        
        # 3. Strength (if distinct)
        best = sorted_by_score[-1] if sorted_by_score else None
        if best and best.get("score", 0) >= 9 and best != worst:
            summary.append(f"Strong: {best['name']}")
            
        final_comment = " ".join(summary)
        
        category_def = self.get_category_def(category_id)
        return {
            "id": category_id,
            "category_id": category_id,
            "name": category_def.get("name", category_id),
            "description": category_def.get("description", ""),
            "score": avg_score,
            "comment": final_comment,
            "tasks": results,
            "details": {
                "task_count": len(results),
                "scores": [r.get("score", 0) for r in results],
                "min_score": min([r.get("score", 0) for r in results]) if results else 0,
                "max_score": max([r.get("score", 0) for r in results]) if results else 0
            }
        }

    def _run_category(self, category_id, test_model, options=None, progress_callback=None):
        """Alias für run_category für Abwärtskompatibilität"""
        return self.run_category(category_id, test_model, options, progress_callback)

    # -------------------- SPEED --------------------
    # UNVERÄNDERT von deiner Version

    def _run_speed(self, test_model, options=None, progress_callback=None):
        if progress_callback:
            progress_callback("Warmup (speed)...")

        prompt = "Write the numbers from one to one thousand in English words without explanations."

        # Warmup
        try:
            _ = self.client.generate(test_model, prompt, options=options, stream=False)
        except Exception:
            pass

        if progress_callback:
            progress_callback("Measuring speed...")

        start_t = time.time()
        res = self.client.generate(test_model, prompt, options=options, stream=False)
        end_t = time.time()
        elapsed = max(end_t - start_t, 1e-9)

        eval_count = res.get("eval_count") or res.get("tokens") or len((res.get("response") or "").split())
        eval_duration_ns = res.get("eval_duration", 0)
        tps = (eval_count / eval_duration_ns) * 1_000_000_000 if eval_duration_ns else eval_count / elapsed

        return {
            "id": "A",
            "name": "Velocity/Speed",
            "description": "Velocity/Speed",
            "score": round(tps, 2), # TPS is the "score" now
            "comment": f"{round(tps,2)} tokens/sec",
            "details": {"tokens": int(eval_count), "total_time_s": round(elapsed, 3), "tokens_per_sec": round(tps, 2)}
        }

    # -------------------- CONTENT BENCHMARKS --------------------

    def generate_response(self, bench_id, test_model, options=None, stream=False):
        """Generiert Antwort für einen spezifischen Task"""
        try:
            if len(bench_id) == 1:
                # Für Abwärtskompatibilität: erste Task der Kategorie
                category_def = self.get_category_def(bench_id)
                if category_def and "tasks" in category_def and category_def["tasks"]:
                    task_def = category_def["tasks"][0]
                else:
                    return (None if stream else ""), "Task not found"
            else:
                # Task mit ID (z.B. "B1")
                category_id = bench_id[0]
                task_id = bench_id[1]
                task_def = self.get_task_def(category_id, task_id)
            
            if not task_def:
                return (None if stream else ""), "Task not found"
            
            return self.client.generate(test_model, task_def["prompt"], options=options, stream=stream), None
        except Exception as e:
            return (None if stream else ""), str(e)

    def judge_response(self, bench_id, model_text):
        """Bewertet Antwort für einen spezifischen Task"""
        if len(bench_id) == 1:
            category_id = bench_id
            task_id = "1"  # Standard für Abwärtskompatibilität
        else:
            category_id = bench_id[0]
            task_id = bench_id[1]
        
        task_def = self.get_task_def(category_id, task_id)
        if not task_def:
            return {"score": 0, "issues": ["Task definition not found"], "comment": "Task error"}
        
        return self._judge_response(task_def, model_text)

    def _run_content_task(self, category_id, task_id, test_model, options=None, progress_callback=None):
        """Führt einen einzelnen Content-Task aus"""
        if test_model == JUDGE_MODEL:
            return {"id": f"{category_id}{task_id}", "score": 0, 
                    "comment": "Test model must not equal judge model", "issues": []}

        task_def = self.get_task_def(category_id, task_id)
        if not task_def:
            return {"id": f"{category_id}{task_id}", "score": 0, 
                    "comment": "Task definition not found", "issues": []}

        if progress_callback:
            progress_callback(f"Generating response for {category_id}{task_id}...")

        res, error = self.generate_response(f"{category_id}{task_id}", test_model, options=options)
        if error:
            return {"id": f"{category_id}{task_id}", "score": 0, 
                    "comment": f"Generation error: {error}", "issues": [error]}

        text = res.get("response") if isinstance(res, dict) else res

        if progress_callback:
            progress_callback(f"Judging {category_id}{task_id}...")

        judge_result = self._judge_response(task_def, text)
        
        # Score bereits 1-10 vom Judge
        score = judge_result.get("score", 0)

        return {
            "id": f"{category_id}{task_id}",
            "name": task_def.get("name", f"{category_id}{task_id}"),
            "description": task_def.get("task_desc", task_def.get("description", "")),
            "score": min(10, max(0, score)),
            "comment": judge_result.get("comment", f"Score: {score}/10"),
            "issues": judge_result.get("issues", []),
            "judge_feedback": judge_result,
            "category": category_id
        }

    def _judge_response(self, task_def, model_text):
        """Bewertet eine Antwort mit dem Judge-Modell"""
        facts_section = ""
        if "truths" in task_def:
            facts_section = "\n".join([f"{i}. {fact} => {'CORRECT' if truth else 'INCORRECT'}"
                                       for i, (fact, truth) in enumerate(task_def["truths"].items(), 1)])
        elif "facts" in task_def:
            facts_section = "\n".join([f"{i}. {f}" for i, f in enumerate(task_def["facts"],1)])
        else:
            facts_section = "Facts: none"

        rubric = (
            "Return ONLY a JSON object:\n"
            "{\n"
            "  \"score\": number (1-10, where 10 is perfect),\n"
            "  \"issues\": [...],\n"
            "  \"comment\": \"detailed summary with score explanation and how good of a model it is for that category (max 200 chars)\"\n"
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
Task: {task_def.get('task_desc', task_def.get('description', ''))}

Facts / Truths:
{facts_section}

Model Answer:
---
{model_text if model_text else '[No response]'}
---

Evaluation Criteria:
{task_def.get('criteria', 'General quality assessment')}

{rubric}
"""
        try:
            judge_res = self.client.generate(JUDGE_MODEL, judge_prompt, 
                                           system=system_prompt, options=JUDGE_OPTIONS, stream=False)
        except Exception as e:
            return {
                "score": 1,
                "issues": [f"Judge call failed: {e}"],
                "comment": "Judge call failed, minimal score assigned"
            }

        raw = judge_res.get("response") or ""
        try:
            # Robustes JSON-Parsing mit Regex
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
            else:
                # Fallback: Suche nach geschweiften Klammern
                start = raw.find("{")
                end = raw.rfind("}")
                if start >= 0 and end > start:
                    parsed = json.loads(raw[start:end+1])
                else:
                    raise ValueError("No JSON object found in response")
            
            # Sicherstellen, dass Score 1-10 ist
            score = float(parsed.get("score", 1))
            parsed["score"] = min(10, max(1, round(score)))
            
            # Raw-Feedback vom Judge mitspeichern
            parsed["full_judge_response"] = raw
            
        except Exception as e:
            return {
                "score": 1,
                "issues": [f"Judge JSON parse error: {e}", raw[:200]],
                "comment": "JSON parse error, minimal score assigned",
                "full_judge_response": raw
            }

        return parsed

    # -------------------- BENCHMARK DEFINITIONS --------------------

    def get_category_def(self, category_id):
        """Gibt die Kategorie-Definition zurück"""
        defs = {
            "B": {
                "name": "English Quality",
                "description": "Business English in verschiedenen Kontexten",
                "tasks": ["B1", "B2", "B3"]
            },
            "C": {
                "name": "German Quality", 
                "description": "Deutsche Sprache in Geschäftskontexten",
                "tasks": ["C1", "C2", "C3"]
            },
            "D": {
                "name": "Fact Checking",
                "description": "Faktenprüfung mit verschiedenen Schwierigkeitsgraden",
                "tasks": ["D1", "D2", "D3"]
            },
            "E": {
                "name": "Context Extraction",
                "description": "Informationsextraktion aus verschiedenen Quellen",
                "tasks": ["E1", "E2", "E3"]
            },
            "F": {
                "name": "Logic & Planning",
                "description": "Logisches Denken und Planung",
                "tasks": ["F1", "F2", "F3"]
            },
            "G": {
                "name": "Creative Writing",
                "description": "Kreatives Schreiben in verschiedenen Genres",
                "tasks": ["G1", "G2", "G3"]
            },
            "H": {
                "name": "Technical Explanation",
                "description": "Komplexe Konzepte vereinfachen",
                "tasks": ["H1", "H2", "H3"]
            },
            "I": {
                "name": "Python Coding",
                "description": "Programmierung mit steigendem Schwierigkeitsgrad",
                "tasks": ["I1", "I2", "I3"]
            },
            "J": {
                "name": "Customer Support",
                "description": "Kundenservice in verschiedenen Szenarien",
                "tasks": ["J1", "J2", "J3"]
            },
            "W": {
                "name": "Knowledge",
                "description": "Wissenstests mit klaren Fakten",
                "tasks": ["W1", "W2", "W3"]
            },
            "X": {
                "name": "Uncertainty Handling",
                "description": "Umgang mit unsicheren Informationen",
                "tasks": ["X1", "X2", "X3"]
            }
        }
        return defs.get(category_id, {})

    def get_task_def(self, category_id, task_id):
        """Gibt die Definition eines spezifischen Tasks zurück"""
        tasks = self._get_all_tasks()
        return tasks.get(f"{category_id}{task_id}", {})

    def _get_all_tasks(self):
        """Alle Task-Definitionen"""
        return {
            # ----- ENGLISH QUALITY (B) -----
            "B1": {
                "name": "Business Email - Overdue Invoice",
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
            "B2": {
                "name": "Business Report - Sales Analysis",
                "prompt": (
                    "Write a concise business report analyzing sales performance.\n\n"
                    "Facts:\n"
                    "- Period: Q1 2024 (Jan-Mar)\n"
                    "- Total Revenue: 1.2M EUR\n"
                    "- Previous Quarter (Q4 2023): 0.9M EUR\n"
                    "- Top Product: Model X (400k EUR)\n"
                    "- Region Growth: EU +15%, US +8%, Asia -3%\n"
                    "- Marketing Spend: 150k EUR\n"
                    "- Customer Acquisition Cost: 85 EUR\n"
                    "- Customer Retention Rate: 87%\n"
                    "- New Customers: 3,200\n"
                    "- Average Order Value: 375 EUR\n\n"
                    "Requirements:\n"
                    "- Include: Executive Summary, Key Findings, Recommendations\n"
                    "- Use bullet points where appropriate\n"
                    "- Professional business language\n"
                    "- Highlight both positive and negative trends"
                ),
                "task_desc": "Business Report Writing with Data Analysis",
                "criteria": (
                    "Score based on:\n"
                    "- All data points included (3 points)\n"
                    "- Logical structure (3 points)\n"
                    "- Clear insights from data (2 points)\n"
                    "- Actionable recommendations (2 points)\n"
                    "Deduct for:\n"
                    "- Missing key data\n"
                    "- Poor structure\n"
                    "- No insights or recommendations"
                )
            },
            "B3": {
                "name": "Meeting Minutes",
                "prompt": (
                    "Convert this meeting transcript into formal meeting minutes:\n\n"
                    "Transcript:\n"
                    "Alex: Okay, let's start. First, Project Alpha is delayed by 2 weeks.\n"
                    "Sarah: Because the API documentation isn't ready from Tom's team.\n"
                    "Tom: We'll have it by Wednesday, I promise.\n"
                    "Alex: Budget update: we're 5% under, good news.\n"
                    "Maria: But the design review needs to happen Friday at 2 PM.\n"
                    "Alex: Right. Sarah, can you prepare the prototype?\n"
                    "Sarah: Yes, I'll share it Thursday morning.\n"
                    "Alex: Next meeting: next Monday, same time.\n\n"
                    "Required sections: Attendees, Date/Time, Agenda Items, Decisions, Action Items (with owners), Next Meeting\n"
                    "Add 5+ inferred but reasonable details (room numbers, specific deadlines, etc.)"
                ),
                "task_desc": "Meeting Minutes from Transcript with Inferred Details",
                "criteria": (
                    "Score based on:\n"
                    "- All transcript points covered (3 points)\n"
                    "- Proper formal structure (3 points)\n"
                    "- Logical inferred details (2 points)\n"
                    "- Clear action items with owners (2 points)\n"
                    "Deduct for:\n"
                    "- Missing key information\n"
                    "- Informal language\n"
                    "- No action items or owners"
                )
            },

            # ----- GERMAN QUALITY (C) -----
            "C1": {
                "name": "Formelle Mahnung",
                "prompt": (
                    "Verfassen Sie eine formelle Zahlungserinnerung auf Deutsch.\n\n"
                    "Fakten:\n"
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
                    "- Währung und Dezimalformat\n\n"
                    "Anforderungen:\n"
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
            "C2": {
                "name": "Geschäftliche E-Mail - Terminanfrage",
                "prompt": (
                    "Schreiben Sie eine geschäftliche E-Mail auf Deutsch für eine Terminanfrage.\n\n"
                    "Fakten:\n"
                    "- Ihr Name: Julia Schmidt, Vertriebsleiterin\n"
                    "- Ihre Firma: TechSolutions AG\n"
                    "- Empfänger: Herr Dr. Michael Wagner, Geschäftsführer\n"
                    "- Empfänger-Firma: Innovate GmbH\n"
                    "- Zweck: Vorstellung neues Produkt 'DataSecure Pro'\n"
                    "- Gewünschter Zeitraum: 15.-19. April 2024\n"
                    "- Dauer: 60-90 Minuten\n"
                    "- Format: Vor-Ort-Besuch bevorzugt, Online möglich\n"
                    "- Mit dabei: Technischer Experte Markus Berger\n"
                    "- Anlagen: Produktdatenblatt (wird separat geschickt)\n\n"
                    "Anforderungen:\n"
                    "- Höfliche, aber bestimmte Formulierung\n"
                    "- Mehrere Terminvorschläge machen\n"
                    "- Klare Angabe des Besprechungsziels\n"
                    "- Professionelle Grußformel\n"
                    "- Keine Floskeln wie 'hoffe auf baldige Antwort'"
                ),
                "task_desc": "Deutsche Geschäfts-E-Mail mit Terminanfrage",
                "criteria": (
                    "Score based on:\n"
                    "- Alle Fakten enthalten (3 Punkte)\n"
                    "- Professioneller Geschäftston (2 Punkte)\n"
                    "- Klare Terminvorschläge (2 Punkte)\n"
                    "- Korrekte Grammatik/Rechtschreibung (2 Punkte)\n"
                    "- Angemessene Länge & Struktur (1 Punkt)\n"
                    "Abzug für:\n"
                    "- Umgangssprache\n"
                    "- Unklare Terminangaben\n"
                    "- Fehlende Höflichkeitsformeln\n"
                    "- Rechtschreibfehler"
                )
            },
            "C3": {
                "name": "Protokoll - Besprechung",
                "prompt": (
                    "Verfassen Sie ein formelles Protokoll für diese Team-Besprechung auf Deutsch.\n\n"
                    "Gesprächsnotizen:\n"
                    "09:00 Begrüßung (Anna)\n"
                    "09:05 Projektstatus 'Neue Website': 80% fertig, Verzögerung durch fehlende Bilder\n"
                    "09:15 Budget: 5.000€ über Plan wegen zusätzlicher Entwickler-Stunden\n"
                    "09:25 Marketing: Social Media Kampagne startet 1. Mai\n"
                    "09:35 Probleme: Server-Ausfall letzte Woche für 2 Stunden\n"
                    "09:45 Entscheidung: Wartungsfenster jeden Donnerstag 03:00-04:00\n"
                    "09:55 Aufgaben: Thomas holt Bilder bis Freitag, Lisa erstellt Backup-Plan\n"
                    "10:00 Nächster Termin: 22. April, 09:00\n\n"
                    "Format: TOP, Diskussion, Beschlüsse, Aufgaben (mit Verantwortlichen), Nächste Schritte\n"
                    "Fügen Sie 5+ plausible Details hinzu (Raumnummer, Teilnehmer, spezifische Zahlen)"
                ),
                "task_desc": "Formelles deutsches Besprechungsprotokoll",
                "criteria": (
                    "Score based on:\n"
                    "- Alle Diskussionspunkte erfasst (3 Punkte)\n"
                    "- Korrektes Protokollformat (3 Punkte)\n"
                    "- Klare Aufgabenverteilung (2 Punkte)\n"
                    "- Sinnvolle Zusatzdetails (2 Punkte)\n"
                    "Abzug für:\n"
                    "- Wichtige Informationen fehlen\n"
                    "- Informelle Sprache\n"
                    "- Unklare Verantwortlichkeiten\n"
                    "- Formatfehler"
                )
            },

            # ----- FACT CHECKING (D) -----
            "D1": {
                "name": "Basic Facts - True/False",
                "prompt": (
                    "Evaluate each statement as CORRECT or FALSE and justify briefly:\n\n"
                    "Facts:\n"
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
                "task_desc": "Basic Fact Checking (10 Clear Facts)",
                "truths": {
                    "The Berlin Wall was built in 1961.": True,
                    "The Berlin Wall fell in 1989.": True,
                    "Water boils at a lower temperature at higher atmospheric pressure.": False,
                    "Napoleon lost the Battle of Waterloo.": True,
                    "Switzerland is a member of the EU.": False,
                    "Isaac Newton developed the law of universal gravitation.": True,
                    "The Earth is not a perfect circle.": True,
                    "Albert Einstein won the Nobel Prize in Physics in 1921.": True,
                    "Mount Everest is the highest mountain on Earth.": True,
                    "The UN was founded in 1945.": True
                },
                "criteria": (
                    "Score based on:\n"
                    "- Correct true/false judgment for each fact (1 point each, 10 total)\n"
                    "Deduct for:\n"
                    "- Incorrect judgment\n"
                    "- Poor reasoning\n"
                    "- Unnecessary verbosity"
                )
            },
            "D2": {
                "name": "Mixed Facts - Some Tricky",
                "prompt": (
                    "Evaluate each statement. Some are subtly incorrect:\n\n"
                    "1. Humans have 46 chromosomes in every cell.\n"
                    "2. The Great Wall of China is visible from space with the naked eye.\n"
                    "3. Vitamin C prevents the common cold.\n"
                    "4. Lightning never strikes the same place twice.\n"
                    "5. Bats are blind.\n"
                    "6. Goldfish have a 3-second memory.\n"
                    "7. Sugar causes hyperactivity in children.\n"
                    "8. Humans use only 10% of their brains.\n"
                    "9. Chameleons change color primarily for camouflage.\n"
                    "10. Vikings wore horned helmets."
                ),
                "task_desc": "Mixed Facts with Common Misconceptions",
                "truths": {
                    "Humans have 46 chromosomes in every cell.": False,  # Except gametes
                    "The Great Wall of China is visible from space with the naked eye.": False,
                    "Vitamin C prevents the common cold.": False,
                    "Lightning never strikes the same place twice.": False,
                    "Bats are blind.": False,
                    "Goldfish have a 3-second memory.": False,
                    "Sugar causes hyperactivity in children.": False,
                    "Humans use only 10% of their brains.": False,
                    "Chameleons change color primarily for camouflage.": False,  # Mainly communication
                    "Vikings wore horned helmets.": False
                },
                "criteria": (
                    "Score based on:\n"
                    "- Correct judgment for each fact (1 point each, 10 total)\n"
                    "Deduct for:\n"
                    "- Incorrect judgment\n"
                    "- Oversimplified reasoning\n"
                    "- Not catching subtle falsehoods"
                )
            },
            "D3": {
                "name": "Numerical Facts - Precision",
                "prompt": (
                    "Check these numerical/statistical facts:\n\n"
                    "1. The population of Germany is about 84 million.\n"
                    "2. The speed of light is 299,792,458 meters per second.\n"
                    "3. π (pi) equals 22/7 exactly.\n"
                    "4. The Earth's circumference at the equator is approximately 40,075 km.\n"
                    "5. There are 8 planets in our solar system.\n"
                    "6. A day on Venus is longer than a year on Venus.\n"
                    "7. The human body has 206 bones.\n"
                    "8. Water's boiling point at sea level is exactly 100°C.\n"
                    "9. The atomic number of oxygen is 8.\n"
                    "10. The distance from Earth to Moon averages 384,400 km."
                ),
                "task_desc": "Numerical/Statistical Fact Checking",
                "truths": {
                    "The population of Germany is about 84 million.": True,
                    "The speed of light is 299,792,458 meters per second.": True,
                    "π (pi) equals 22/7 exactly.": False,
                    "The Earth's circumference at the equator is approximately 40,075 km.": True,
                    "There are 8 planets in our solar system.": True,
                    "A day on Venus is longer than a year on Venus.": True,
                    "The human body has 206 bones.": True,
                    "Water's boiling point at sea level is exactly 100°C.": False,  # Approximately
                    "The atomic number of oxygen is 8.": True,
                    "The distance from Earth to Moon averages 384,400 km.": True
                },
                "criteria": (
                    "Score based on:\n"
                    "- Correct judgment (1 point each, 10 total)\n"
                    "Deduct for:\n"
                    "- Missing numerical precision nuances\n"
                    "- Incorrect absolute statements\n"
                    "- No distinction between exact and approximate"
                )
            },

            # ----- CONTEXT EXTRACTION (E) -----
            "E1": {
                "name": "Meeting Transcript Analysis",
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
                    "Extract at least 10 specific points from the transcript."
                ),
                "task_desc": "Information Extraction from Meeting Transcript",
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
            "E2": {
                "name": "Email Thread Summary",
                "prompt": (
                    "Summarize this email thread into key points:\n\n"
                    "Email 1 (Mon 9:00, Maria to Team):\n"
                    "\"Team, please review the attached proposal for client X. Budget: 50k, deadline June 15.\"\n\n"
                    "Email 2 (Mon 11:30, John to Maria):\n"
                    "\"The timeline seems tight. We need 2 more developers. Can we extend to June 30?\"\n\n"
                    "Email 3 (Mon 14:15, Maria to John):\n"
                    "\"Client insists on June 15. We can add 10k budget for contractors. Please confirm.\"\n\n"
                    "Email 4 (Mon 16:45, John to Maria):\n"
                    "\"Agreed. I'll hire contractors. Need approval for extra 10k by tomorrow.\"\n\n"
                    "Email 5 (Tue 10:00, Maria to John):\n"
                    "\"Budget approved. Start immediately. Weekly updates every Monday 10 AM.\"\n\n"
                    "Extract: Key decisions, action items, deadlines, constraints, unresolved issues."
                ),
                "task_desc": "Email Thread Analysis and Summary",
                "criteria": (
                    "Score based on:\n"
                    "- All key points extracted (4 points)\n"
                    "- Clear action items/owners (3 points)\n"
                    "- Correct deadlines/constraints (2 points)\n"
                    "- Identified unresolved issues (1 point)\n"
                    "Deduct for:\n"
                    "- Missing important decisions\n"
                    "- Wrong assignment of actions\n"
                    "- Confused timeline"
                )
            },
            "E3": {
                "name": "Technical Documentation Extraction",
                "prompt": (
                    "Extract specific information from this technical note:\n\n"
                    "System: Database Cluster v3.2\n"
                    "Status: Production, 3 nodes (db01, db02, db03)\n"
                    "Specs: 64GB RAM each, 2TB SSD, Ubuntu 20.04\n"
                    "Issues: db03 shows high CPU (90%) during backup window (02:00-04:00)\n"
                    "Backup: Daily full backup at 02:30, retention 30 days\n"
                    "Maintenance: Monthly patch window first Sunday 01:00-04:00\n"
                    "Contacts: Primary DBA: Sarah (sarah@company.com), Secondary: Tom\n"
                    "Monitoring: Prometheus alerts on CPU>85% for >15min\n"
                    "Planned upgrade: To v3.3 in Q3, requires 4h downtime\n\n"
                    "Create structured output with: Hardware specs, Issues, Schedule, Contacts, Alerts, Upgrade plan."
                ),
                "task_desc": "Technical Information Extraction",
                "criteria": (
                    "Score based on:\n"
                    "- All technical details correctly extracted (4 points)\n"
                    "- Logical structure (3 points)\n"
                    "- Clear categorization (2 points)\n"
                    "- No irrelevant information (1 point)\n"
                    "Deduct for:\n"
                    "- Missing critical specs/issues\n"
                    "- Poor categorization\n"
                    "- Adding non-existent information"
                )
            },

            # ----- LOGIC & PLANNING (F) -----
            "F1": {
                "name": "Simple Timetable",
                "prompt": (
                    "Create a weekly timetable for one class (5A) with these constraints:\n\n"
                    "Teachers:\n"
                    "- Müller: Math (2x per week)\n"
                    "- Schmidt: Sports (1x per week)\n"
                    "- Weber: German (2x per week)\n\n"
                    "Constraints:\n"
                    "- School hours: Mon-Fri, 08:00-13:00\n"
                    "- Each day: 3-4 lessons of 45min\n"
                    "- Math cannot be on Monday\n"
                    "- Sports cannot be on Friday\n"
                    "- German must be on Tuesday\n"
                    "- No teacher teaches two days in a row\n"
                    "- Include breaks: 15min after lesson 2, 30min lunch\n\n"
                    "Output: Clear timetable with days, times, subjects, teachers."
                ),
                "task_desc": "Simple Weekly Timetable with Constraints",
                "criteria": (
                    "Score based on:\n"
                    "- All constraints satisfied (6 points)\n"
                    "- Realistic schedule (2 points)\n"
                    "- Clear formatting (2 points)\n"
                    "Deduct for:\n"
                    "- Constraint violations\n"
                    "- Unrealistic timing\n"
                    "- Missing breaks"
                )
            },
            "F2": {
                "name": "Project Planning",
                "prompt": (
                    "Plan a software project with these requirements:\n\n"
                    "Requirements:\n"
                    "- 5 modules: Auth, Database, API, Frontend, Testing\n"
                    "- Team: 3 developers (A,B,C), 1 tester (D)\n"
                    "- Dependencies: Database before API, Auth before Frontend\n"
                    "- Testing can only start after module is complete\n"
                    "- Each module: Dev time 3-5 days, Testing 1-2 days\n"
                    "- Constraints: Dev A not available days 3-4, Tester D part-time (50%)\n"
                    "- Max 2 modules in parallel\n"
                    "- Deadline: Complete within 15 working days\n\n"
                    "Create: Gantt-like schedule with tasks, assignments, dependencies, timeline."
                ),
                "task_desc": "Project Schedule with Dependencies",
                "criteria": (
                    "Score based on:\n"
                    "- All dependencies respected (4 points)\n"
                    "- Resource constraints handled (3 points)\n"
                    "- Realistic timeline (2 points)\n"
                    "- Clear presentation (1 point)\n"
                    "Deduct for:\n"
                    "- Dependency violations\n"
                    "- Over-allocating resources\n"
                    "- Missing deadline"
                )
            },
            "F3": {
                "name": "Resource Allocation with Conflicts",
                "prompt": (
                    "Allocate resources for these 6 projects with conflicting requirements:\n\n"
                    "Projects (each needs 1 specialist):\n"
                    "1. AI Model - needs GPU specialist\n"
                    "2. Mobile App - needs iOS/Android dev\n"
                    "3. Web Portal - needs Frontend + Backend\n"
                    "4. Database Migration - needs DBA\n"
                    "5. Security Audit - needs Security expert\n"
                    "6. API Integration - needs Backend + API specialist\n\n"
                    "Available specialists (each can handle 1 project at a time):\n"
                    "- Alice: GPU, Backend\n"
                    "- Bob: iOS/Android, Frontend\n"
                    "- Carol: DBA, Backend\n"
                    "- David: Security, API\n"
                    "- Eve: Frontend, API\n\n"
                    "Constraints:\n"
                    "- Project 3 needs TWO specialists\n"
                    "- Project 6 must start after Project 4 finishes\n"
                    "- Alice and Bob cannot work on same project\n"
                    "- Timeline: All projects within 3 weeks, max 3 projects per week\n\n"
                    "Create allocation plan with weekly assignments."
                ),
                "task_desc": "Complex Resource Allocation with Multiple Constraints",
                "criteria": (
                    "Score based on:\n"
                    "- All constraints satisfied (5 points)\n"
                    "- Skills matched correctly (3 points)\n"
                    "- Feasible timeline (2 points)\n"
                    "Deduct heavily for:\n"
                    "- Constraint violations\n"
                    "- Skill mismatches\n"
                    "- Overloaded specialists"
                )
            },

            # ----- CREATIVE WRITING (G) -----
            "G1": {
                "name": "Cyberpunk-Noir Story",
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
            "G2": {
                "name": "Historical Fiction",
                "prompt": (
                    "Write a short scene (200-250 words) set in Renaissance Florence.\n\n"
                    "Requirements:\n"
                    "- Characters: An apprentice painter and a merchant\n"
                    "- Include specific details: fresco, gold florins, silk, workshop\n"
                    "- Time: Early morning\n"
                    "- Conflict: The apprentice has made a mistake in the fresco\n"
                    "- End with a decision or realization\n\n"
                    "Focus on historical accuracy in details and dialogue style."
                ),
                "task_desc": "Historical Fiction with Specific Details",
                "criteria": (
                    "Score based on:\n"
                    "- Historical accuracy (3 points)\n"
                    "- All required elements included (3 points)\n"
                    "- Good scene setting (2 points)\n"
                    "- Satisfying ending (2 points)\n"
                    "Deduct for:\n"
                    "- Anachronisms\n"
                    "- Missing required elements\n"
                    "- Poor pacing\n"
                    "- Modern dialogue"
                )
            },
            "G3": {
                "name": "Technical Product Description",
                "prompt": (
                    "Write a creative but accurate product description for:\n"
                    "\"Quantum Notebook - A notebook that uses quantum entanglement for instant syncing\"\n\n"
                    "Requirements:\n"
                    "- Target audience: Tech-savvy professionals\n"
                    "- Length: 150-200 words\n"
                    "- Tone: Exciting but credible\n"
                    "- Include: 3 key features, 1 use case scenario\n"
                    "- End with a compelling call-to-action\n"
                    "- No exaggerated claims beyond 'quantum entanglement'\n\n"
                    "Make it sound like a real Kickstarter project."
                ),
                "task_desc": "Creative Technical Writing",
                "criteria": (
                    "Score based on:\n"
                    "- Balances creativity and credibility (3 points)\n"
                    "- Clear key features (2 points)\n"
                    "- Engaging tone (2 points)\n"
                    "- Good structure (2 points)\n"
                    "- Strong call-to-action (1 point)\n"
                    "Deduct for:\n"
                    "- Overly technical or too fluffy\n"
                    "- Missing requirements\n"
                    "- Unrealistic claims"
                )
            },

            # ----- TECHNICAL EXPLANATION (H) -----
            "H1": {
                "name": "ELI5 - Quantum Entanglement",
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
            "H2": {
                "name": "Explain Blockchain to Grandma",
                "prompt": (
                    "Explain 'blockchain technology' to your 70-year-old grandmother who uses email but no cryptocurrency.\n\n"
                    "Requirements:\n"
                    "- Use a non-technical analogy (like a recipe book, ledger, etc.)\n"
                    "- Explain why it's secure/trustworthy\n"
                    "- Max. 200 words\n"
                    "- Patient, warm tone\n"
                    "- No mention of Bitcoin unless as example\n"
                    "- End with one practical use she might understand"
                ),
                "task_desc": "Complex Technology for Non-Technical Audience",
                "criteria": (
                    "Score based on:\n"
                    "- Perfect analogy (3 points)\n"
                    "- Clear security explanation (3 points)\n"
                    "- Right tone for audience (2 points)\n"
                    "- Practical example (2 points)\n"
                    "Deduct for:\n"
                    "- Technical jargon\n"
                    "- Confusing analogy\n"
                    "- Wrong tone (patronizing or too technical)\n"
                    "- No practical application"
                )
            },
            "H3": {
                "name": "API vs Library - For Beginners",
                "prompt": (
                    "Explain the difference between an API and a Library to a first-year computer science student.\n\n"
                    "Requirements:\n"
                    "- Use concrete examples they'd understand\n"
                    "- Compare and contrast clearly\n"
                    "- Include when to use each\n"
                    "- Length: 200-250 words\n"
                    "- Tone: Helpful teacher, not textbook\n"
                    "- End with a simple decision flowchart: 'When to choose API vs Library'"
                ),
                "task_desc": "Technical Comparison for Beginners",
                "criteria": (
                    "Score based on:\n"
                    "- Clear differentiation (4 points)\n"
                    "- Good examples (3 points)\n"
                    "- Helpful tone (2 points)\n"
                    "- Useful decision aid (1 point)\n"
                    "Deduct for:\n"
                    "- Confusing or overlapping definitions\n"
                    "- Poor examples\n"
                    "- Too abstract or too technical\n"
                    "- Missing practical guidance"
                )
            },

            # ----- PYTHON CODING (I) -----
            "I1": {
                "name": "Basic Password Validation",
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
            "I2": {
                "name": "Data Processing with Edge Cases",
                "prompt": (
                    "Write a function 'process_sales_data(data)' that:\n"
                    "1. Takes a list of sales dicts: [{'amount': 100, 'currency': 'EUR', 'valid': True}, ...]\n"
                    "2. Returns: total valid sales in EUR, average sale, count of invalid sales\n"
                    "3. Handle edge cases:\n"
                    "   - Missing 'valid' key → treat as invalid\n"
                    "   - Non-numeric amount → skip with warning\n"
                    "   - Non-EUR currencies → convert using rates dict provided\n"
                    "4. Include unit tests for: empty list, all invalid, mixed currencies, missing keys\n"
                    "5. Write clean, readable code with comments"
                ),
                "task_desc": "Python: Data Processing with Error Handling",
                "criteria": (
                    "Score based on:\n"
                    "- Correct core logic (3 points)\n"
                    "- All edge cases handled (3 points)\n"
                    "- Good tests (2 points)\n"
                    "- Code quality/comments (2 points)\n"
                    "Deduct for:\n"
                    "- Missing edge cases\n"
                    "- No tests\n"
                    "- Poor error handling\n"
                    "- Unreadable code"
                )
            },
            "I3": {
                "name": "Debug & Refactor Challenge",
                "prompt": (
                    "This buggy function should find duplicate files by content. Debug and refactor it:\n\n"
                    "def find_duplicates(paths):\n"
                    "    hashes = {}\n"
                    "    for p in paths:\n"
                    "        with open(p) as f:\n"
                    "            data = f.read()\n"
                    "            h = hash(data)\n"
                    "            if h in hashes:\n"
                    "                hashes[h].append(p)\n"
                    "            else:\n"
                    "                hashes[h] = [p]\n"
                    "    return [v for v in hashes.values() if len(v) > 0]\n\n"
                    "Problems to fix:\n"
                    "1. hash() is not stable across runs\n"
                    "2. Files might be binary, not text\n"
                    "3. Large files could cause memory issues\n"
                    "4. Function returns empty lists incorrectly\n"
                    "5. No error handling\n\n"
                    "Provide: Fixed code + explanation of changes"
                ),
                "task_desc": "Python: Debugging and Refactoring",
                "criteria": (
                    "Score based on:\n"
                    "- All bugs identified (3 points)\n"
                    "- Correct fixes implemented (3 points)\n"
                    "- Good explanations (2 points)\n"
                    "- Production-ready code (2 points)\n"
                    "Deduct for:\n"
                    "- Missing bugs\n"
                    "- Introducing new bugs\n"
                    "- Poor explanations\n"
                    "- Inefficient solutions"
                )
            },

            # ----- CUSTOMER SUPPORT (J) -----
            "J1": {
                "name": "Lost Suitcase - De-escalation",
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
            },
            "J2": {
                "name": "Technical Support - Confused User",
                "prompt": (
                    "You're tech support for a cloud service. Customer email:\n"
                    "\"I cannot upload my files. The website says 'error 413' but I don't know what that means. "
                    "My files are not that big, just some photos from vacation. I need this for work now!\"\n\n"
                    "Write a helpful response that:\n"
                    "1. Explains error 413 in simple terms (entity too large)\n"
                    "2. Asks for specific file sizes/types without being accusatory\n"
                    "3. Offers 2-3 solutions (compress, split, use desktop app)\n"
                    "4. Provides a fallback option if nothing works\n"
                    "5. Tone: Patient, helpful, not condescending"
                ),
                "task_desc": "Technical Customer Support",
                "criteria": (
                    "Score based on:\n"
                    "- Clear technical explanation (3 points)\n"
                    "- Practical solutions (3 points)\n"
                    "- Perfect tone (2 points)\n"
                    "- Fallback option (2 points)\n"
                    "Deduct for:\n"
                    "- Jargon without explanation\n"
                    "- Blaming the user\n"
                    "- Unhelpful solutions\n"
                    "- Impatient tone"
                )
            },
            "J3": {
                "name": "Billing Issue - Angry Customer",
                "prompt": (
                    "Customer is furious about double billing:\n"
                    "\"You charged me twice this month! This is theft! I want refund NOW and cancel my subscription! "
                    "I've been a customer for 3 years and this is how you treat me?\"\n\n"
                    "Write a response that:\n"
                    "1. Acknowledges the error immediately\n"
                    "2. Takes full responsibility (no 'system error' excuses)\n"
                    "3. Offers: Immediate refund + credit for next month\n"
                    "4. Tries to retain customer with special offer\n"
                    "5. Provides direct contact for escalation\n"
                    "6. Tone: Apologetic but confident, respectful"
                ),
                "task_desc": "Billing Crisis Management",
                "criteria": (
                    "Score based on:\n"
                    "- Takes full responsibility (3 points)\n"
                    "- Good retention attempt (3 points)\n"
                    "- Appropriate compensation (2 points)\n"
                    "- Perfect crisis tone (2 points)\n"
                    "Deduct for:\n"
                    "- Defensive language\n"
                    "- Poor compensation\n"
                    "- No retention effort\n"
                    "- Unprofessional anger"
                )
            },

            # ----- KNOWLEDGE (W) -----
            "W1": {
                "name": "General Knowledge Quiz",
                "prompt": (
                    "Answer these 10 knowledge questions concisely:\n\n"
                    "1. Who wrote '1984'?\n"
                    "2. What is the capital of Australia?\n"
                    "3. Which element has atomic number 1?\n"
                    "4. In what year did World War II end?\n"
                    "5. What is the largest planet in our solar system?\n"
                    "6. Who painted the Mona Lisa?\n"
                    "7. What is the chemical formula for water?\n"
                    "8. Which country gifted the Statue of Liberty to the USA?\n"
                    "9. What is the speed of sound in air at sea level (approx.)?\n"
                    "10. Who developed the theory of relativity?"
                ),
                "task_desc": "Basic General Knowledge",
                "facts": [
                    "George Orwell wrote '1984'",
                    "Canberra is the capital of Australia",
                    "Hydrogen has atomic number 1",
                    "World War II ended in 1945",
                    "Jupiter is the largest planet",
                    "Leonardo da Vinci painted the Mona Lisa",
                    "H₂O is water's chemical formula",
                    "France gifted the Statue of Liberty",
                    "Speed of sound is about 343 m/s",
                    "Albert Einstein developed relativity"
                ],
                "criteria": (
                    "Score based on:\n"
                    "- Correct answer to each question (1 point each, 10 total)\n"
                    "Deduct for:\n"
                    "- Incorrect answers\n"
                    "- Vague or incomplete answers\n"
                    "- Adding unnecessary information"
                )
            },
            "W2": {
                "name": "Science & Technology Facts",
                "prompt": (
                    "Answer these 10 science/tech questions:\n\n"
                    "1. What does CPU stand for?\n"
                    "2. Which programming language uses 'print' for output?\n"
                    "3. What is the main gas in Earth's atmosphere?\n"
                    "4. What does HTTP stand for?\n"
                    "5. Which organ pumps blood in the human body?\n"
                    "6. What is the freezing point of water in Celsius?\n"
                    "7. What does RAM stand for?\n"
                    "8. Which planet is known as the Red Planet?\n"
                    "9. What is the largest mammal on Earth?\n"
                    "10. What does URL stand for?"
                ),
                "task_desc": "Science and Technology Knowledge",
                "facts": [
                    "CPU = Central Processing Unit",
                    "Python uses 'print' for output",
                    "Nitrogen is main gas in atmosphere",
                    "HTTP = HyperText Transfer Protocol",
                    "Heart pumps blood",
                    "Water freezes at 0°C",
                    "RAM = Random Access Memory",
                    "Mars is the Red Planet",
                    "Blue whale is largest mammal",
                    "URL = Uniform Resource Locator"
                ],
                "criteria": (
                    "Score based on:\n"
                    "- Correct answers (1 point each, 10 total)\n"
                    "Deduct for:\n"
                    "- Wrong answers\n"
                    "- Partial answers\n"
                    "- Confusing similar terms"
                )
            },
            "W3": {
                "name": "Geography & History Facts",
                "prompt": (
                    "Answer these 10 geography/history questions:\n\n"
                    "1. Which river runs through London?\n"
                    "2. Who was the first President of the United States?\n"
                    "3. What is the largest ocean?\n"
                    "4. In which country did the Renaissance begin?\n"
                    "5. What is the longest river in the world?\n"
                    "6. Who discovered penicillin?\n"
                    "7. Which continent is the Sahara Desert in?\n"
                    "8. Who wrote the Declaration of Independence?\n"
                    "9. What is the smallest country in the world?\n"
                    "10. Which year did the Berlin Wall fall?"
                ),
                "task_desc": "Geography and History Knowledge",
                "facts": [
                    "Thames River runs through London",
                    "George Washington was first US President",
                    "Pacific Ocean is the largest",
                    "Renaissance began in Italy",
                    "Nile is longest river (or Amazon, accept both)",
                    "Alexander Fleming discovered penicillin",
                    "Sahara is in Africa",
                    "Thomas Jefferson wrote Declaration",
                    "Vatican City is smallest country",
                    "Berlin Wall fell in 1989"
                ],
                "criteria": (
                    "Score based on:\n"
                    "- Correct answers (1 point each, 10 total)\n"
                    "Deduct for:\n"
                    "- Factual errors\n"
                    "- Imprecise answers\n"
                    "- Missing key details"
                )
            },

            # ----- UNCERTAINTY HANDLING (X) -----
            "X1": {
                "name": "Ambiguous Questions",
                "prompt": (
                    "Answer these questions. If information is missing or unclear, say so:\n\n"
                    "1. How many employees does 'TechCorp' have?\n"
                    "2. What will the stock market do tomorrow?\n"
                    "3. Who will win the next World Cup?\n"
                    "4. Is pineapple on pizza good?\n"
                    "5. What's the exact population of London right now?\n"
                    "6. Can you predict next week's lottery numbers?\n"
                    "7. What's the meaning of life?\n"
                    "8. How do I get rich quickly?\n"
                    "9. What's the best programming language?\n"
                    "10. Will it rain here in 3 months?"
                ),
                "task_desc": "Handling Unanswerable Questions",
                "criteria": (
                    "Score based on:\n"
                    "- Correctly identifies uncertain/unanswerable questions (5 points)\n"
                    "- Provides reasonable disclaimers (3 points)\n"
                    "- Avoids making up facts (2 points)\n"
                    "Deduct heavily for:\n"
                    "- Making up specific numbers/facts\n"
                    "- Presenting opinions as facts\n"
                    "- No uncertainty acknowledgment"
                )
            },
            "X2": {
                "name": "Incomplete Information Scenario",
                "prompt": (
                    "A client asks: 'My website is down and losing money! Fix it now!'\n"
                    "But they provide NO details: no URL, no error messages, nothing.\n\n"
                    "Write your response as a professional support agent.\n"
                    "Requirements:\n"
                    "- Acknowledge the urgency\n"
                    "- Ask SPECIFIC diagnostic questions (provide 5-6)\n"
                    "- Explain why each piece of information is needed\n"
                    "- Offer immediate first steps they can try\n"
                    "- Set realistic expectations\n"
                    "- Never guess the cause without data"
                ),
                "task_desc": "Handling Vague/Incomplete Requests",
                "criteria": (
                    "Score based on:\n"
                    "- Asks specific diagnostic questions (4 points)\n"
                    "- Explains why information is needed (3 points)\n"
                    "- Manages expectations (2 points)\n"
                    "- Avoids guessing (1 point)\n"
                    "Deduct for:\n"
                    "- Guessing causes/solutions\n"
                    "- Vague questions\n"
                    "- Promising unrealistic fixes\n"
                    "- Getting defensive"
                )
            },
            "X3": {
                "name": "Conflicting Information",
                "prompt": (
                    "You receive two contradictory pieces of information:\n\n"
                    "Source A (reliable database): 'Product X requires 8GB RAM minimum'\n"
                    "Source B (user manual): 'Product X requires 4GB RAM minimum'\n\n"
                    "A customer asks: 'How much RAM do I need for Product X?'\n\n"
                    "Write your response that:\n"
                    "1. Acknowledges the contradiction\n"
                    "2. Explains possible reasons for discrepancy\n"
                    "3. Provides safest recommendation\n"
                    "4. Suggests how to verify\n"
                    "5. Offers to check with manufacturer\n"
                    "6. Never presents conflicting info as equally valid"
                ),
                "task_desc": "Handling Conflicting Information",
                "criteria": (
                    "Score based on:\n"
                    "- Acknowledges contradiction clearly (3 points)\n"
                    "- Explains possible reasons (3 points)\n"
                    "- Provides safe recommendation (2 points)\n"
                    "- Offers verification path (2 points)\n"
                    "Deduct for:\n"
                    "- Hiding the conflict\n"
                    "- Picking one arbitrarily without explanation\n"
                    "- Confusing the customer\n"
                    "- No verification options"
                )
            }
        }