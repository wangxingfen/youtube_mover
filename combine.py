import subprocess
from pathlib import Path
import os

def fast_merge_av(video_path, audio_path, output_path=None):
    """
    快速合并音频视频的优化版本
    """
    if output_path is None:
        video_stem = Path(audio_path).stem
        output_path = f"{video_stem}_merged.mp4"
    
    # 使用硬件加速（如果可用）
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',        # 视频流直接复制
        '-c:a', 'aac',         # 音频编码为AAC（兼容性好）
        '-map', '0:v:0',       # 选择第一个视频流
        '-map', '1:a:0',       # 选择第二个音频流
        '-shortest',
        '-y',
        output_path
    ]
    
    # 设置进程优先级（Linux/Mac）
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True
        )
        print("合并成功!")
        return output_path
    except FileNotFoundError:
        print("错误: 未找到FFmpeg，请先安装FFmpeg")
        return None
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg错误: {e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)}")
        return None

# 批量处理版本
def batch_merge_av(file_pairs):
    """
    批量合并多个文件
    file_pairs: [(video1, audio1), (video2, audio2), ...]
    """
    success_count = 0
    for video, audio in file_pairs:
        if fast_merge_av(video, audio):
            success_count += 1
    
    print(f"批量处理完成: {success_count}/{len(file_pairs)} 成功")
# Example usage
if __name__ == "__main__":
    base_path = "pre_combine_videos"
    files=os.listdir(base_path)
    video_files = [os.path.join(base_path, f) for f in files if f.endswith(".mp4")]
    audio_files = [os.path.join(base_path, f) for f in files if f.endswith(".mp3")]
    file_pairs = [(video_files[i], audio_files[i]) for i in range(len(video_files))]
    batch_merge_av(file_pairs)

    # Example of how to use the function
    #fast_merge_av("9.mp4", "9.mp3", "output_video3.mp4")
    pass