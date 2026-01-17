# LLMark

LLMark ist ein leistungsstarkes, lokales Benchmark-Tool für LLMs via Ollama. Es kombiniert objektive Leistungsmessung mit einer KI-gestützten Qualitätsbewertung durch ein festes Judge-Modell.

## Features

- **Echtzeit-VRAM-Monitoring**: Überwachen Sie Ihren Grafikspeicher live direkt im GUI (alle 2 Sekunden aktualisierend).
- **Präzise Geschwindigkeitsmessung**: Benchmark A misst die tatsächliche Token-Generierungsrate (Tokens/Sekunde).
- **KI-Fokussierte Bewertung**: Benchmarks B-J werden durch das Judge-Modell (`qwen2.5:14b-instruct`) auf einer Skala von 1-10 bewertet.
- **Responsive GUI**: Dank Hintergrund-Threading bleibt das Interface auch während Hardware-Checks und Benchmarks flüssig.

## Voraussetzungen

1. **Python 3.11+**
2. **Ollama** installiert und laufend.
3. **Judge Modell**: `qwen2.5:14b-instruct` (wird benötigt für die Qualitätsbewertung).

## Installation

1. Installieren Sie die Python-Abhängigkeiten:
   ```bash
   pip install -r requirements.txt
   ```

2. Laden Sie das Judge-Modell herunter:
   ```bash
   ollama pull qwen2.5:14b-instruct
   ```

## Start

Starten Sie die Anwendung am besten direkt über den Python-Interpreter Ihres Virtual Environments:

```bash
.venv\Scripts\python.exe app.py
```

## Nutzung

1. Wählen Sie das zu testende Modell aus der Liste.
2. Klicken Sie auf **"Start Benchmark"**.
3. Verfolgen Sie den Fortschritt in den Tabs "Start" und "Detail-Log".
4. Nach Abschluss werden die Ergebnisse als JSON in `/results` gespeichert und direkt im GUI angezeigt.

## Benchmarks Übersicht

- **A: Geschwindigkeit**: Misst Tokens pro Sekunde (TPS).
- **B: English Quality**: Verfassen einer formellen Business-Email.
- **C: Deutsch Qualität**: Erstellen einer formellen Mahnung.
- **D: Fakten**: Multi-Fakten-Check (Geschichte, Wissenschaft, Geografie).
- **E: Kontext**: Informationsextraktion aus einem Meeting-Transkript.
- **F: Logik**: Lösung eines komplexen Stundenplan-Problems.
- **G: Kreativität**: Storytelling im Cyberpunk-Noir Stil mit festen Begriffen.
- **H: ELI5**: Technische Vereinfachung (Quantenverschränkung für Kinder).
- **I: Programmierung**: Python-Funktion für Passwort-Validierung.
- **J: Rollenspiel**: Empathische Deeskalation im Kundensupport.

---
*Hinweis: Der Gesamt-Score (max. 90) berechnet sich aus der Qualität der Benchmarks B bis J.*
