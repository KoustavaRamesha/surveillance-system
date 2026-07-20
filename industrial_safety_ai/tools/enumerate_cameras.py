import cv2

print('Enumerating camera indices 0..7')
for i in range(8):
    cap = cv2.VideoCapture(i)
    opened = cap.isOpened()
    got = False
    res = None
    if opened:
        ok, frame = cap.read()
        got = ok
        if ok and frame is not None:
            h, w = frame.shape[:2]
            res = f"{w}x{h}"
    print(f"index={i}, opened={opened}, got_frame={got}, resolution={res}")
    try:
        cap.release()
    except Exception:
        pass

print('\nOpenCV build info:')
print(cv2.getBuildInformation().split('\n')[:20])
