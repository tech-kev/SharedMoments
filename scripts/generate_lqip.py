#!/usr/bin/env python3
"""Generate LQIP (Low-Quality Image Placeholders) and media dimensions for all existing items."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import SessionLocal, Item
from app.utils import generate_lqip
import shutil
import subprocess


IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm', 'mkv'}
IMAGE_CONTENT_TYPES = {'image', 'galleryStartWithImage'}
VIDEO_CONTENT_TYPES = {'video', 'video-mov', 'galleryStartWithVideo'}

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))
IMAGES_FOLDER = os.path.join(BASEDIR, 'uploads', 'images')
VIDEOS_FOLDER = os.path.join(BASEDIR, 'uploads', 'videos')
THUMBS_FOLDER = os.path.join(BASEDIR, 'uploads', 'thumbs')


def ensure_video_thumbnail(filename):
    """Generate video thumbnail if it doesn't exist, return path or None."""
    thumb_name = os.path.splitext(filename)[0] + '.jpg'
    thumb_path = os.path.join(THUMBS_FOLDER, thumb_name)

    if os.path.exists(thumb_path):
        return thumb_path

    video_path = os.path.join(VIDEOS_FOLDER, filename)
    if not os.path.exists(video_path):
        video_path = os.path.join(IMAGES_FOLDER, filename)
        if not os.path.exists(video_path):
            return None

    os.makedirs(THUMBS_FOLDER, exist_ok=True)

    ffmpeg_bin = shutil.which('ffmpeg')
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
    if not ffmpeg_bin:
        print("  ERROR: ffmpeg not found")
        return None

    try:
        subprocess.run([
            ffmpeg_bin, '-i', video_path,
            '-ss', '00:00:00.5',
            '-frames:v', '1',
            '-vf', 'scale=800:-1',
            '-q:v', '5',
            '-update', '1',
            '-y', thumb_path
        ], capture_output=True, timeout=10)
    except Exception as e:
        print(f"  ERROR: Thumbnail generation failed: {e}")
        return None

    return thumb_path if os.path.exists(thumb_path) else None


def find_image_path(filename):
    """Find the actual path of an image file."""
    path = os.path.join(IMAGES_FOLDER, filename)
    if os.path.exists(path):
        return path
    path = os.path.join(VIDEOS_FOLDER, filename)
    if os.path.exists(path):
        return path
    return None


def main():
    session = SessionLocal()
    try:
        # Items die LQIP oder Dimensionen brauchen
        items = session.query(Item).filter(
            Item.contentURL.isnot(None),
            Item.contentURL != '',
            Item.contentType.in_(list(IMAGE_CONTENT_TYPES | VIDEO_CONTENT_TYPES))
        ).all()

        # Nur Items die noch kein LQIP oder keine Dimensionen haben
        items = [i for i in items if i.blurPlaceholder is None or i.mediaWidth is None]

        total = len(items)
        if total == 0:
            print("All items already have LQIP and dimensions.")
            return

        print(f"Processing {total} items...\n")

        success = 0
        skipped = 0

        for i, item in enumerate(items, 1):
            first_url = item.contentURL.split(';')[0].strip()
            if not first_url:
                print(f"  [{i}/{total}] Item {item.id}: No contentURL, skipping")
                skipped += 1
                continue

            lqip, width, height = None, None, None

            if item.contentType in IMAGE_CONTENT_TYPES:
                img_path = find_image_path(first_url)
                if img_path:
                    lqip, width, height = generate_lqip(img_path)
                else:
                    print(f"  [{i}/{total}] Item {item.id}: File not found: {first_url}")
                    skipped += 1
                    continue

            elif item.contentType in VIDEO_CONTENT_TYPES:
                thumb_path = ensure_video_thumbnail(first_url)
                if thumb_path:
                    lqip, width, height = generate_lqip(thumb_path)
                else:
                    print(f"  [{i}/{total}] Item {item.id}: Could not generate video thumbnail: {first_url}")
                    skipped += 1
                    continue

            if lqip and width and height:
                if item.blurPlaceholder is None:
                    item.blurPlaceholder = lqip
                item.mediaWidth = width
                item.mediaHeight = height
                session.commit()
                size = len(lqip.encode('ascii'))
                print(f"  [{i}/{total}] Item {item.id}: OK ({width}x{height}, {size} bytes LQIP)")
                success += 1
            else:
                print(f"  [{i}/{total}] Item {item.id}: Generation failed for {first_url}")
                skipped += 1

        print(f"\nDone! {success} processed, {skipped} skipped.")

    finally:
        session.close()


if __name__ == '__main__':
    main()
