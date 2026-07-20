from pathlib import Path
import shutil
root = Path(__file__).resolve().parent.parent
src = root / 'yolov8n.pt'
dst_dir = root / 'models'
dst = dst_dir / 'yolov8n.pt'
print('root', root)
print('src exists', src.exists())
print('dst exists', dst.exists())
if src.exists() and not dst.exists():
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    print('moved', src, '->', dst)
else:
    print('no-op')
