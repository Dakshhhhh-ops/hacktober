"""Turn a photo into a short video that Chrome can use as a fake webcam.

    python tests/fake_camera.py photo.jpg out.y4m [--dark] [--blur]

Used by tests/browser_check.mjs. Needs OpenCV (opencv-python-headless).
"""
import argparse

import cv2
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image")
    parser.add_argument("out")
    parser.add_argument("--dark", action="store_true", help="10% brightness")
    parser.add_argument("--blur", action="store_true", help="a strong 21 x 21 blur")
    args = parser.parse_args()

    frame = cv2.resize(cv2.imread(args.image), (640, 480), interpolation=cv2.INTER_AREA)
    if args.dark:
        frame = (frame * 0.1).astype(np.uint8)
    if args.blur:
        frame = cv2.blur(frame, (21, 21))
    yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420).tobytes()
    with open(args.out, "wb") as out:
        out.write(b"YUV4MPEG2 W640 H480 F10:1 Ip A1:1 C420jpeg\n")
        for _ in range(10):  # Chrome loops the file
            out.write(b"FRAME\n" + yuv)


if __name__ == "__main__":
    main()
