# MIPS Pipeline Simulator

Ceyhun Eren tarafından geliştirilmiştir.

## Kurulum

```bash
pip install flask
python app.py
```

Tarayıcıda aç: http://localhost:5000

## Özellikler
- 5 aşamalı MIPS pipeline görselleştirmesi (IF, ID, EX, MEM, WB)
- Data Hazard (RAW) tespiti
- Load-Use Hazard tespiti (1 stall)
- Control Hazard tespiti
- CPI ve performans analizi
- Hazır örnek kodlar

## Deploy (Render.com)
1. GitHub'a yükle
2. render.com → New Web Service
3. Build: `pip install flask` | Start: `python app.py`
