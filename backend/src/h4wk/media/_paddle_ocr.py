"""Worker OCR CPU cô lập vì PaddleX và T19 cần hai bản OpenCV khác nhau."""

import json
import sys
from pathlib import Path

DETECTOR = "PaddlePaddle/PP-OCRv5_mobile_det"
DET_REV = "0d63e78e2b680928f6b1747d76a08db6e645efb7"
RECOGNIZER = "meomeo163/PP-OCRv5-vi-latin-rec-v4"
REC_REV = "ddff1130d4fc32d5d75db4515983f5b9a071ae00"


def model_dir(repo: str, revision: str, subdir: str = "") -> Path:
    from huggingface_hub import snapshot_download

    files = [subdir + name for name in ("inference.json", "inference.yml", "inference.pdiparams")]
    return Path(snapshot_download(repo, revision=revision, allow_patterns=files)) / subdir


def main() -> None:
    from paddleocr import PaddleOCR

    model = PaddleOCR(
        device="cpu",
        cpu_threads=2,
        enable_mkldnn=False,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_detection_model_dir=str(model_dir(DETECTOR, DET_REV)),
        text_recognition_model_name="latin_PP-OCRv5_mobile_rec",
        text_recognition_model_dir=str(model_dir(RECOGNIZER, REC_REV, "inference/")),
    )
    with Path(sys.argv[1]).open("w", encoding="utf-8") as out:
        for path in json.load(sys.stdin):
            (page,) = model.predict(path)
            lines = []
            for text, score, box in zip(
                page["rec_texts"], page["rec_scores"], page["rec_boxes"], strict=True
            ):
                left, top, right, bottom = map(int, box)
                lines.append(
                    {
                        "text": text,
                        "score": float(score),
                        "bbox": [left, top, right - left, bottom - top],
                    }
                )
            out.write(json.dumps(lines, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
