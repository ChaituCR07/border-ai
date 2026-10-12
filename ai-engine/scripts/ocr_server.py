import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI, File, UploadFile  # noqa: E402

from app.anpr.ocr import PaddleOcrEngine  # noqa: E402

app = FastAPI(title="OCR server")
engine = PaddleOcrEngine(lang="en", device="cpu")


@app.post("/ocr")
def ocr(file: UploadFile = File(...)):
    image = cv2.imdecode(np.frombuffer(file.file.read(), np.uint8), cv2.IMREAD_COLOR)
    res = engine.read(image)
    return {"text": res.text, "confidence": res.confidence, "lines": res.lines}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8100)
