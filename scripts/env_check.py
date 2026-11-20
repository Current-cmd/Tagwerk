"""Run on the GPU machine: python scripts/env_check.py"""
import importlib
import shutil
import sys


def check(name, fn):
    try:
        print(f"[ok]   {name}: {fn()}")
        return True
    except Exception as exc:
        print(f"[FAIL] {name}: {exc}")
        return False


def torch_cuda():
    import torch
    built = torch.version.cuda
    assert built and built.startswith("12.6"), f"torch built for CUDA {built}, need 12.6 (Pascal)"
    assert torch.cuda.is_available(), "CUDA not available"
    cc = torch.cuda.get_device_capability(0)
    return f"{torch.__version__} on {torch.cuda.get_device_name(0)} (cc {cc[0]}.{cc[1]}, fp32 only)"


def ct2_int8():
    import ctranslate2
    types = ctranslate2.get_supported_compute_types("cuda")
    assert "int8" in types or "int8_float32" in types, f"no int8 on CUDA: {types}"
    return sorted(types)


def yolo():
    import numpy as np
    from ultralytics import YOLO
    m = YOLO("yolo11s.pt")
    m.predict(np.zeros((640, 640, 3), dtype="uint8"), device=0, verbose=False)
    return "yolo11s ran on GPU"


def aruco():
    import cv2
    cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    return cv2.__version__


def python_version():
    assert sys.version_info >= (3, 12), f"Python {sys.version.split()[0]}; RelateAnything needs 3.12+"
    return sys.version.split()[0]


def ffmpeg():
    path = shutil.which("ffmpeg")
    assert path, "ffmpeg not on PATH (sudo apt install ffmpeg)"
    return path


def relateanything():
    # Installed from github.com/Maelic/RelateAnything (package name: relsgg; needs torch~=2.13, 2.14 is fine).
    mod = importlib.import_module("relsgg")
    assert hasattr(mod, "RelateAnything")
    return "relsgg.RelateAnything importable"


results = [
    check("python >= 3.12", python_version),
    check("ffmpeg", ffmpeg),
    check("torch + CUDA 12.6", torch_cuda),
    check("CTranslate2 int8", ct2_int8),
    check("YOLO11s", yolo),
    check("OpenCV ArUco", aruco),
    check("RelateAnything import", relateanything),
]
sys.exit(0 if all(results) else 1)
