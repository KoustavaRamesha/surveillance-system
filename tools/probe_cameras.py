import cv2

print('Probing camera indices 0-7')
for i in range(8):
    cap = cv2.VideoCapture(i)
    opened = cap.isOpened()
    frame_info = None
    if opened:
        ret, frame = cap.read()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            frame_info = f'{w}x{h}'
        else:
            frame_info = 'no-frame'
    print(f'Index {i}: opened={opened}, frame={frame_info}')
    try:
        cap.release()
    except Exception:
        pass
print('Probe complete')
