from video_processor_pro import simple_process
import os
import time
from uuid import uuid4
def videos_processor(videos_path):
    if not os.path.exists(videos_path):
        os.mkdir(videos_path)
    if not os.path.exists("temp"):
        os.mkdir("temp")
    while True:
        time.sleep(4)
        try:
            videos=os.listdir(videos_path)
            for video in videos:
                video_path=os.path.join(videos_path,video)
                simple_process(video_path=video_path, output_dir="D:/AI/油管视频汉化/subtitles",add_translation=True, model_size="medium", burn_subtitles=True,replace_audio=True,skip_subtitle_generation=False,volume_factor=3)
                os.rename(video_path,f"D:/AI/油管视频汉化/temp/{uuid4()}.mp4")
                #os.remove(video_path)
        except Exception as e:
            print(e)
if __name__ == '__main__':
    videos_path="temp_videos"
    videos_processor(videos_path)