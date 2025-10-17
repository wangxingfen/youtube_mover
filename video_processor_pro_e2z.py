import os
import argparse
import whisper
import pysrt
from voice import index_tts
from moviepy import VideoFileClip,CompositeAudioClip,AudioFileClip
from voice import text_to_speech_edge
import cv2
import time
import re
from PIL import Image, ImageDraw, ImageFont
import asyncio
from translate import chanslater_z2e
from collections import defaultdict
import subprocess
import shutil
import numpy as np
from pathlib import Path
def fast_merge_av(video_path, audio_path, output_path=None):
    """
    快速合并音频视频的优化版本
    """
    if output_path is None:
        video_stem = Path(video_path).stem
        output_path = f"{video_stem}_merged.mp4"
    
    # 检查输入和输出路径是否相同，如果相同则创建临时文件
    temp_output = None
    final_output_path = output_path
    if os.path.abspath(video_path) == os.path.abspath(output_path):
        # 创建临时输出文件路径
        temp_output = output_path.replace(".mp4", "_temp.mp4")
        output_path = temp_output
    
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
        
        # 如果使用了临时文件，需要将它重命名为最终输出文件
        if temp_output:
            shutil.move(temp_output, final_output_path)
            output_path = final_output_path
            
        print("合并成功!")
        return output_path
    except FileNotFoundError:
        print("错误: 未找到FFmpeg，请先安装FFmpeg")
        return None
    except subprocess.CalledProcessError as e:
        # 如果使用了临时文件但失败了，清理临时文件
        if temp_output and os.path.exists(temp_output):
            os.remove(temp_output)
            
        print(f"FFmpeg错误: {e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)}")
        return None

class VideoProcessor:
    def __init__(self, model_size="base"):
        """
        初始化视频处理器
        :param model_size: Whisper模型大小 ("tiny", "base", "small", "medium", "large")
        """
        print(f"正在加载Whisper {model_size} 模型...")
        self.model = whisper.load_model(model_size)
        
    def transcribe_audio(self, video_path, language="zh"):
        """
        从视频中提取音频并转录
        :param video_path: 视频文件路径
        :param language: 音频语言
        :return: 转录结果
        """
        print("正在转录音频...")
        result = self.model.transcribe(video_path, temperature=0,language=language, verbose=True)
        return result
    
    def translate_text(self, text, target_lang="en"):
        """
        使用专业翻译模型翻译文本到目标语言
        :param text: 待翻译文本
        :param target_lang: 目标语言代码
        :return: 翻译后的文本
        """
        return chanslater_z2e(text)

    def create_subtitle_file(self, segments, output_path, add_translation=False):
        """
        创建字幕文件
        :param segments: 转录的片段
        :param output_path: 输出文件路径
        :param add_translation: 是否添加翻译
        """
        subs = pysrt.SubRipFile()
        
        for i, segment in enumerate(segments):
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text'].strip()
            
            # 创建字幕项
            sub = pysrt.SubRipItem(
                index=i+1,
                start=self._seconds_to_time(start_time),
                end=self._seconds_to_time(end_time),
                text=text
            )
            subs.append(sub)
            
            # 如果需要添加翻译
            if add_translation:
                translated_text = self.translate_text(text)
                # 用换行符连接原文和译文，英文在前，中文在后
                combined_text = f"{text}\n{translated_text}"
                sub.text = combined_text
        
        subs.save(output_path, encoding='utf-8')
        print(f"字幕文件已保存至: {output_path}")
        return subs
    
    def _seconds_to_time(self, seconds):
        """
        将秒数转换为时间格式
        :param seconds: 秒数
        :return: SubRipTime对象
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds - int(seconds)) * 1000)
        return pysrt.SubRipTime(hours=hours, minutes=minutes, seconds=secs, milliseconds=millisecs)
    
    def burn_subtitles_to_video(self, video_path, subtitle_path, output_path, replace_audio=False,volume_factor=2,sounds_files=None):
        """
        将字幕烧录到视频中，使用FFmpeg提高效率
        :param video_path: 输入视频路径
        :param subtitle_path: 字文件路径
        :param output_path: 输出视频路径
        :param replace_audio: 是否用生成的语音替换原音频
        """
        print("正在将字幕烧录到视频中...")
        
        # 检查文件是否存在
        if not os.path.exists(video_path):
            raise ValueError(f"视频文件不存在: {video_path}")
            
        if not os.path.exists(subtitle_path):
            raise ValueError(f"字幕文件不存在: {subtitle_path}")
        
        # 确保字幕文件使用UTF-8编码并标准化格式
        try:
            with open(subtitle_path, 'r', encoding='utf-8') as f:
                subtitle_content = f.read()
            # 重新以UTF-8编码写入，确保文件格式统一
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(subtitle_content)
        except UnicodeDecodeError:
            # 如果不是UTF-8编码，尝试其他编码并转换为UTF-8
            try:
                with open(subtitle_path, 'r', encoding='gbk') as f:
                    subtitle_content = f.read()
                with open(subtitle_path, 'w', encoding='utf-8') as f:
                    f.write(subtitle_content)
            except UnicodeDecodeError:
                # 尝试使用兼容性更强的编码
                with open(subtitle_path, 'r', encoding='utf-8', errors='ignore') as f:
                    subtitle_content = f.read()
                with open(subtitle_path, 'w', encoding='utf-8') as f:
                    f.write(subtitle_content)
        
        # 转换路径为绝对路径并处理特殊字符
        video_path = os.path.abspath(video_path)
        subtitle_path = os.path.abspath(subtitle_path)
        output_path = os.path.abspath(output_path)
        
        # 处理Windows路径中的特殊字符，使用POSIX路径避免转义问题
        escaped_subtitle_path = subtitle_path.replace('\\', '/').replace(':', '\\:')

        # 构造FFmpeg命令，强制指定UTF-8编码
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f"subtitles='{escaped_subtitle_path}':charenc=utf-8:force_style='PrimaryColour=&H00FFFFFF,Outline=1,Shadow=0,BackColour=&H80000000,FontName=STXINGKA.TTF,FontSize=14'",
            '-y',  # 覆盖输出文件
            '-strict', '-2',  # 兼容编码
            output_path
        ]
        
        try:
            # 执行FFmpeg命令
            result = subprocess.run(ffmpeg_cmd, capture_output=True)
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                print(f"FFmpeg执行失败: {error_msg}")
                # 尝试备用方案，使用更简单的样式配置
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-vf', f"subtitles='{escaped_subtitle_path}':charenc=utf-8",
                    '-y',
                    '-strict', '-2',
                    output_path
                ]
                result = subprocess.run(ffmpeg_cmd, capture_output=True)
                
                if result.returncode != 0:
                    error_msg = result.stderr.decode('utf-8', errors='ignore')
                    raise RuntimeError(f"FFmpeg执行失败: {error_msg}")
                
            print(f"已生成带字幕的视频: {output_path}")
        except FileNotFoundError:
            raise RuntimeError("未找到FFmpeg，请确保FFmpeg已安装并在系统PATH中")
        except Exception as e:
            raise RuntimeError(f"烧录字幕时发生错误: {str(e)}")
        
        # 处理音频替换
        # 传递原始路径给音频处理函数，而不是转义后的路径
        if replace_audio:
            self._replace_audio_with_generated_speech(video_path, subtitle_path, output_path, volume_factor, sounds_files)
        else:
            # 使用moviepy保留原始音频
            self._merge_original_audio(video_path, output_path)
        
        print(f"已完成视频处理: {output_path}")

    def _replace_audio_with_generated_speech(self, video_path, subtitle_path, output_path, volume_factor, sounds_files):
        """
        用生成的语音替换原音频
        """
        print("正在生成并合并语音...")
        # 初始化变量以便在异常情况下也能清理
        original_video = None
        subtitled_video = None
        final_video = None
        final_audio = None
        new_audio_tracks = []
        
        try:
            # 生成语音片段
            output_dir = os.path.dirname(output_path)
            audio_files, timestamps,durations = asyncio.run(self.generate_speech_for_subtitles(subtitle_path, output_dir,soundfiles_path=sounds_files))
            
            # 使用moviepy合并音频
            original_video = VideoFileClip(video_path)
            subtitled_video = VideoFileClip(output_path)
            
            # 创建新的音频轨道 - 保留原始音频，并添加生成的语音
            new_audio_tracks = [original_video.audio]  # 保留原始音频
            
            # 添加生成的语音片段
            speech_clips = []  # 保存语音剪辑引用以便清理
            for audio_file, timestamp,duration in zip(audio_files, timestamps,durations):
                if audio_file and os.path.exists(audio_file):
                    speech_clip = AudioFileClip(audio_file)
                    speech_clip = speech_clip.with_speed_scaled(factor=(speech_clip.duration/duration))
                    speech_clip = speech_clip.with_volume_scaled(factor=volume_factor)
                    speech_clip = speech_clip.with_start(timestamp)
                    new_audio_tracks.append(speech_clip)
                    speech_clips.append(speech_clip)  # 保存引用以便稍后清理
            
            # 合并音频轨道
            if new_audio_tracks:
                final_audio = CompositeAudioClip(new_audio_tracks)
                final_audio_path=output_path.replace(".mp4", "_final_audio.mp3")
                final_audio.write_audiofile(final_audio_path)
                final_video_path=output_path.replace(".mp4", "_final.mp4")
                fast_merge_av(output_path, final_audio_path, output_path)
            else:
                fast_merge_av(output_path, None, output_path)
            
            # 显式关闭视频剪辑以释放资源
            if original_video:
                original_video.close()
            if subtitled_video:
                subtitled_video.close()
            if final_audio:
                final_audio.close()
            
            # 清理音频轨道
            for track in new_audio_tracks:
                if hasattr(track, 'close'):
                    track.close()

            
            # 清理临时音频文件
            audio_dir = os.path.join(output_dir, "audio_segments")
            if os.path.exists(audio_dir):
                shutil.rmtree(audio_dir)
                
        except Exception as e:
            # 确保即使出现异常也释放资源
            if original_video:
                original_video.close()
            if subtitled_video:
                subtitled_video.close()
            if final_video:
                final_video.close()
            if final_audio:
                final_audio.close()
            
            # 清理音频轨道
            for track in new_audio_tracks:
                if hasattr(track, 'close'):
                    track.close()
                    
            print(f"警告: 合并音频时出现问题: {e}")
            print("将继续使用原音频版本")

    def _merge_original_audio(self, video_path, output_path):
        """
        合并原始音频到视频
        """
        print("正在合并原始音频...")
        # 初始化变量以便在异常情况下也能清理
        original_video = None
        subtitled_video = None
        final_video = None
        
        try:
            original_video = VideoFileClip(video_path)
            subtitled_video = VideoFileClip(output_path)
            final_video = subtitled_video.with_audio(original_video.audio)
            final_output_path = output_path.replace(".mp4", "_final.mp4")
            final_video.write_videofile(final_output_path, codec="libx264", audio_codec="aac",
                                       preset="ultrafast", threads=8)
            
            # 显式关闭视频剪辑以释放资源
            if original_video:
                original_video.close()
            if subtitled_video:
                subtitled_video.close()
            if final_video:
                final_video.close()
            
            # 删除临时无音频视频文件
            time.sleep(1)  # 等待文件句柄释放
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(final_output_path, output_path)
        except Exception as e:
            # 确保即使出现异常也释放资源
            if original_video:
                original_video.close()
            if subtitled_video:
                subtitled_video.close()
            if final_video:
                final_video.close()
                
            print(f"警告: 合并音频时出现问题: {e}")
            print("将继续使用无音频版本")

    async def generate_speech_for_subtitles(self, subtitle_path, output_dir,soundfiles_path=None):
        """
        使用edge_tts为中文字幕生成语音
        :param subtitle_path: 字幕文件路径
        :param output_dir: 音频文件输出目录
        :return: 音频文件路径列表和时间戳列表
        """
        print("正在为中文字幕生成语音...")
        
        subtitles = pysrt.open(subtitle_path, encoding='utf-8')
        audio_files = []
        timestamps = []
        durations = []
        
        # 确保音频输出目录存在
        audio_dir = os.path.join(output_dir, "audio_segments")
        os.makedirs(audio_dir, exist_ok=True)
        
        for i, subtitle in enumerate(subtitles):
            # 提取中文字幕（假设在第二行）
            lines = subtitle.text.split('\n')
            chinese_text = lines[1] if len(lines) >= 2 else lines[0]
            
            # 清理文本
            chinese_text = re.sub(r'<[^>]+>', '', chinese_text).strip()
            
            if chinese_text and not soundfiles_path:
                # 生成音频文件路径
                audio_file = os.path.join(audio_dir, f"segment_{i:04d}.mp3")
                for attempt in range(100):
                # 使用edge_tts生成语音
                    try:
                        await text_to_speech_edge(text=chinese_text, filename=audio_file,voice="en-CA-LiamNeural")

                        #audio_file=index_tts(chinese_text,refer_voice_path=r"C:\Users\wangxingfeng\Music\cangjiao.wav",infer_mode="批次推理")
                        
                        if os.path.exists(audio_file):
                            audio_files.append(audio_file)
                            timestamps.append(subtitle.start.ordinal / 1000.0)  # 转换为秒
                            #保留两位小数
                            durations.append(round((subtitle.end.ordinal / 1000.0 - subtitle.start.ordinal / 1000.0),3))
                            break                            
                    except Exception as e:
                        print(f"生成语音失败 for subtitle {i}: {e}")
                        time.sleep(5)
            else:
                timestamps.append(subtitle.start.ordinal / 1000.0)  # 转换为秒
                #保留两位小数
                durations.append(round((subtitle.end.ordinal / 1000.0 - subtitle.start.ordinal / 1000.0),3))
        if soundfiles_path:
            audio_files=os.listdir(soundfiles_path)
        
        return audio_files, timestamps,durations

    def process_video(self, video_path, output_dir, add_translation=False, model_size="base", burn_subtitles=False, replace_audio=False, audio_path=None, skip_subtitle_generation=False, subtitle_file=None,volume_factor=2,sounds_files=None):
        """
        处理视频的主要方法
        :param video_path: 输入视频路径
        :param output_dir: 输出目录
        :param add_translation: 是否添加翻译
        :param model_size: Whisper模型大小
        :param burn_subtitles: 是否将字幕烧录到视频中
        :param replace_audio: 是否用生成的语音替换原音频
        :param audio_path: 音频文件路径（可选）
        :param skip_subtitle_generation: 是否跳过字幕生成直接使用现有字幕文件
        :param subtitle_file: 现有的字幕文件路径
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取视频文件名（不含扩展名）
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        if skip_subtitle_generation and subtitle_file and os.path.exists(subtitle_file):
            # 直接使用提供的字幕文件
            print(f"跳过字幕生成，直接使用字幕文件: {subtitle_file}")
            bilingual_subtitle_path = subtitle_file
        else:
            # 转录音频
            transcription_result = self.transcribe_audio(audio_path if audio_path else video_path)
            
            # 创建仅英文的字幕文件
            english_subtitle_path = os.path.join(output_dir, f"{video_name}_en.srt")
            self.create_subtitle_file(transcription_result["segments"], english_subtitle_path, False)
            
            # 如果需要翻译，则创建双语字幕文件
            bilingual_subs = None
            if add_translation:
                bilingual_subtitle_path = os.path.join(output_dir, f"{video_name}_en-zh.srt")
                bilingual_subs = self.create_subtitle_file(transcription_result["segments"], bilingual_subtitle_path, True)
            else:
                bilingual_subtitle_path = english_subtitle_path

        # 初始化输出视频路径
        output_video_path = os.path.join(output_dir, f"{video_name}_with_subtitles.mp4")

        # 如果需要将字幕烧录到视频中
        if burn_subtitles and add_translation:
            output_video_path = os.path.join(output_dir, f"{video_name}_with_subtitles.mp4")
            # 使用双语字幕烧录到视频
            self.burn_subtitles_to_video(video_path, bilingual_subtitle_path, output_video_path, replace_audio,volume_factor,sounds_files)
        elif burn_subtitles:
            output_video_path = os.path.join(output_dir, f"{video_name}_with_subtitles.mp4")
            # 使用英文字幕烧录到视频
            self.burn_subtitles_to_video(video_path, bilingual_subtitle_path, output_video_path, replace_audio,volume_factor,sounds_files)
        elif replace_audio and not burn_subtitles:
            # 如果只需要替换音频而不需要烧录字幕
            self._process_audio_only(video_path, output_dir, bilingual_subtitle_path, audio_path, volume_factor, sounds_files)
        else:
            output_video_path = os.path.join(output_dir, f"{video_name}_with_subtitles.mp4")
        
        print("视频处理完成！")
        return output_video_path

    def _process_audio_only(self, video_path, output_dir, subtitle_path, audio_path, volume_factor, sounds_files):
        """
        仅处理音频，不烧录字幕
        """
        output_video_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(video_path))[0]}_with_audio.mp4")
        print("正在生成并合并语音...")
        # 初始化变量以便在异常情况下也能清理
        original_video = None
        final_video = None
        final_audio = None
        new_audio_tracks = []
        
        try:
            # 生成语音片段
            audio_files, timestamps,durations = asyncio.run(self.generate_speech_for_subtitles(subtitle_path, output_dir,soundfiles_path=sounds_files))
            
            # 使用moviepy合并音频
            original_video = VideoFileClip(video_path)
            
            # 创建新的音频轨道 - 保留原始音频，并添加生成的语音
            new_audio_tracks = []
            
            # 添加原始音频（如果存在）
            if audio_path:
                # 如果提供了audio_path，使用该音频文件作为原始音频
                original_audio = AudioFileClip(audio_path)
                new_audio_tracks.append(original_audio)
            elif original_video.audio is not None:
                # 否则使用视频中的原始音频
                new_audio_tracks.append(original_video.audio)
            
            # 添加生成的语音片段
            speech_clips = []  # 保存语音剪辑引用以便清理
            for audio_file, timestamp,duration in zip(audio_files, timestamps,durations):
                if audio_file and os.path.exists(audio_file):
                    speech_clip = AudioFileClip(audio_file)
                    speech_clip = speech_clip.with_speed_scaled(factor=(speech_clip.duration/duration))  # Speed up by 50%
                    speech_clip = speech_clip.with_volume_scaled(volume_factor)
                    speech_clip = speech_clip.with_start(timestamp)
                    new_audio_tracks.append(speech_clip)
                    speech_clips.append(speech_clip)  # 保存引用以便稍后清理
            
            # 合并音频轨道
            if new_audio_tracks:
                final_audio = CompositeAudioClip(new_audio_tracks)
                final_video = original_video.with_audio(final_audio)
            else:
                final_video = original_video
                
            final_video.write_videofile(output_video_path, codec="libx264", audio_codec="aac", 
                                       preset="ultrafast", threads=8)
            
            # 显式关闭视频剪辑以释放资源
            if original_video:
                original_video.close()
            if final_video:
                final_video.close()
            if final_audio:
                final_audio.close()
            
            # 清理音频轨道
            for track in new_audio_tracks:
                if hasattr(track, 'close'):
                    track.close()
            
            # 清理临时音频文件
            audio_dir = os.path.join(output_dir, "audio_segments")
            if os.path.exists(audio_dir):
                shutil.rmtree(audio_dir)
        except Exception as e:
            # 确保即使出现异常也释放资源
            if original_video:
                original_video.close()
            if final_video:
                final_video.close()
            if final_audio:
                final_audio.close()
            
            # 清理音频轨道
            for track in new_audio_tracks:
                if hasattr(track, 'close'):
                    track.close()
                    
            print(f"警告: 处理音频时出现问题: {e}")

    def _pre_render_universal_template(self, width, font_en, font_zh):
        """
        预渲染通用字幕模板，可以用于所有字幕
        :param width: 视频宽度
        :param font_en: 英文字体
        :param font_zh: 中文字体
        :return: 通用模板图像
        """
        margin = 36
        max_line_width = width - margin * 2
        line_spacing = 10
        
        # 预计算最大高度，使用更保守的估算以减少内存使用
        # 估算最大可能的高度（假设最多3行英文+3行中文）
        max_en_height = self._calculate_text_height(['A'] * 3, font_en)  # 最多3行英文
        max_zh_height = self._calculate_text_height(['中'] * 3, font_zh)  # 最多3行中文
        estimated_max_height = int(max_en_height + max_zh_height + line_spacing) + 20
        
        # 创建一个优化尺寸的透明图像作为通用模板
        template_image = Image.new('RGBA', (width, min(estimated_max_height, 300)), (0, 0, 0, 0))
        return template_image

    def _calculate_text_height(self, lines, font):
        """
        计算文本行的高度
        :param lines: 文本行列表
        :param font: 字体
        :return: 文本总高度
        """
        if not lines:
            return 0
            
        try:
            # 创建一个临时图像用于计算文本尺寸
            temp_image = Image.new('RGBA', (1, 1))
            draw = ImageDraw.Draw(temp_image)
            
            total_height = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_height = bbox[3] - bbox[1]
                total_height += line_height
                
            return total_height
        except:
            # 如果计算失败，返回默认高度
            return len(lines) * 20

    def _render_subtitle_on_template(self, template, subtitle_text, font_en, font_zh):
        """
        在通用模板上渲染特定字幕文本
        :param template: 通用模板图像
        :param subtitle_text: 要渲染的字幕文本
        :param font_en: 英文字体
        :param font_zh: 中文字体
        :return: 包含实际字幕内容的图像
        """
        width, _ = template.size
        margin = 36
        max_line_width = width - margin * 2
        line_spacing = 10
        
        # 分离英文字幕和中文字幕
        lines = subtitle_text.split('\n')
        if len(lines) >= 2:
            english_text = lines[0]  # 第一行是英文
            chinese_text = lines[1]  # 第二行是中文
        else:
            english_text = subtitle_text
            chinese_text = ""
        
        # 清理字幕文本
        english_text = re.sub(r'<[^>]+>', '', english_text)
        chinese_text = re.sub(r'<[^>]+>', '', chinese_text)
        
        # 使用缓存的文本分割方法
        en_lines = self._wrap_text_cached(english_text, font_en, max_line_width)
        zh_lines = self._wrap_text_cached(chinese_text, font_zh, max_line_width)
        
        # 计算总文本高度
        total_height = self._calculate_text_height(en_lines, font_en) + \
                      self._calculate_text_height(zh_lines, font_zh)
        
        if en_lines and zh_lines:
            total_height += line_spacing
            
        # 如果总高度超出模板，创建新的适当大小的图像
        if total_height + 20 > template.height:
            subtitle_image = Image.new('RGBA', (width, int(total_height) + 20), (0, 0, 0, 0))
        else:
            subtitle_image = template.copy()  # 复用模板
            
        draw = ImageDraw.Draw(subtitle_image)
        
        # 绘制文本
        current_y = 10
        current_y = self._draw_text_lines_optimized(draw, en_lines, font_en, width, current_y)
        
        # 在英文字幕和中文字幕之间添加行距
        if en_lines and zh_lines:
            current_y += line_spacing
            
        self._draw_text_lines_optimized(draw, zh_lines, font_zh, width, current_y)
        
        return subtitle_image

    def _wrap_text_cached(self, text, font, max_width):
        """
        使用缓存优化的文本分割方法
        """
        if not text:
            return []
        
        # 为字体创建缓存字典
        if not hasattr(self, '_char_width_cache'):
            self._char_width_cache = defaultdict(dict)
            
        font_cache = self._char_width_cache[id(font)]
        
        lines = []
        current_line = ""
        
        for char in text:
            # 使用缓存获取字符宽度
            if char in font_cache:
                char_width = font_cache[char]
            else:
                try:
                    bbox = ImageDraw.ImageDraw(Image.new('RGBA', (1, 1))).textbbox((0, 0), char, font=font)
                    char_width = bbox[2] - bbox[0]
                except:
                    char_width = 20  # 默认大小
                font_cache[char] = char_width
            
            test_line = current_line + char
            # 计算测试行的宽度
            line_width = sum(font_cache.get(c, char_width) for c in test_line)
            
            if line_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        
        if current_line:
            lines.append(current_line)
            
        return lines

    def _draw_text_lines_optimized(self, draw, lines, font, width, start_y):
        """
        优化的多行文本绘制方法
        """
        current_y = start_y
        margin = 36
        
        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                line_height = bbox[3] - bbox[1]
            except:
                text_width = len(line) * 20
                line_height = 40
                
            x = (width - text_width) // 2
            
            # 绘制白色描边（通过在周围绘制多个偏移的黑色文本来实现）
            outline_color = (255, 255, 255)  # 白色描边
            text_color = (0, 0, 0)           # 黑色文字
            
            # 绘制描边 - 在文字周围8个方向绘制白色文本
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    if dx != 0 or dy != 0:  # 不在中心位置绘制
                        draw.text((x + dx, current_y + dy), line, font=font, fill=outline_color)
            
            # 绘制黑色文字在最上层（中心位置）
            draw.text((x, current_y), line, font=font, fill=text_color)
            
            current_y += line_height
                
        return current_y

    def _overlay_subtitle_image(self, frame, subtitle_image):
        """
        将预渲染的字幕图像叠加到视频帧上
        """
        frame_height, frame_width = frame.shape[:2]
        subtitle_height, subtitle_width = subtitle_image.height, subtitle_image.width
        
        # 计算字幕图像在帧上的位置（底部居中）
        y_offset = frame_height - subtitle_height - 36  # 距离底部的边距
        x_offset = (frame_width - subtitle_width) // 2
        
        # 确保偏移量不会导致负索引
        y_offset = max(0, y_offset)
        x_offset = max(0, x_offset)
        
        # 确保字幕图像不会超出帧边界
        end_y = min(y_offset + subtitle_height, frame_height)
        end_x = min(x_offset + subtitle_width, frame_width)
        
        # 调整字幕图像大小以适应帧边界
        crop_height = end_y - y_offset
        crop_width = end_x - x_offset
        
        # 检查区域大小是否有效
        if crop_height <= 0 or crop_width <= 0:
            return frame
            
        cropped_subtitle = subtitle_image.crop((0, 0, crop_width, crop_height))
        
        # 将PIL图像转换为OpenCV格式
        subtitle_array = np.array(cropped_subtitle)
        
        # 检查是否有Alpha通道
        has_alpha = subtitle_array.shape[2] == 4 if len(subtitle_array.shape) > 2 else False
        
        if has_alpha:
            # 分离BGR和Alpha通道
            subtitle_bgr = subtitle_array[:, :, :3]
            alpha_channel = subtitle_array[:, :, 3] / 255.0
            
            # 创建ROI
            roi = frame[y_offset:end_y, x_offset:end_x]
            
            # 应用Alpha混合
            for c in range(3):  # BGR channels
                roi[:, :, c] = (1.0 - alpha_channel) * roi[:, :, c] + alpha_channel * subtitle_bgr[:, :, 2-c]
        else:
            # 没有Alpha通道，直接复制
            frame[y_offset:end_y, x_offset:end_x] = subtitle_array
            
        return frame

def simple_process(video_path, output_dir="./output", add_translation=False, model_size="medium", burn_subtitles=False, replace_audio=False, audio_path=None, skip_subtitle_generation=False, subtitle_file=None,volume_factor=2.0,soundfiles_path=None):
    """
    简单处理函数，直接使用参数而不通过命令行参数
    :param video_path: 输入视频文件路径
    :param output_dir: 输出目录
    :param add_translation: 是否添加中文翻译
    :param model_size: Whisper模型大小
    :param burn_subtitles: 是否将字幕烧录到视频中
    :param replace_audio: 是否用生成的语音替换原音频
    :param audio_path: 音频文件路径（可选）
    :param skip_subtitle_generation: 是否跳过字幕生成直接使用现有字幕文件
    :param subtitle_file: 现有的字幕文件路径
    """
    # 检查输入文件是否存在
    if not os.path.exists(video_path):
        print(f"错误: 视频文件 '{video_path}' 不存在")
        return
    
    # 如果提供了音频文件路径，检查音频文件是否存在
    if audio_path and not os.path.exists(audio_path):
        print(f"错误: 音频文件 '{audio_path}' 不存在")
        return
    
    # 如果跳过字幕生成，检查字幕文件是否存在
    if skip_subtitle_generation and subtitle_file:
        if not os.path.exists(subtitle_file):
            print(f"错误: 字幕文件 '{subtitle_file}' 不存在")
            return
    elif skip_subtitle_generation and not subtitle_file:
        print("错误: 跳过字幕生成时必须提供字幕文件")
        return
    
    # 创建处理器并处理视频
    processor = VideoProcessor(model_size=model_size)
    output_video_path=processor.process_video(video_path, output_dir, add_translation, model_size, burn_subtitles, replace_audio, audio_path, skip_subtitle_generation, subtitle_file,volume_factor,soundfiles_path)
    return output_video_path

if __name__ == "__main__":
    simple_process(video_path="c2.mp4", output_dir="D:/AI/油管视频汉化/subtitles",add_translation=True, model_size="medium", burn_subtitles=True,replace_audio=True,skip_subtitle_generation=False,volume_factor=3)

    #simple_process("D:/AI/油管视频汉化/subtitles/2_with_subtitles.mp4", "D:/AI/油管视频汉化/subtitles",soundfiles_path=r"D:\AI\油管视频汉化\subtitles\audio_segments", add_translation=False, model_size="medium", burn_subtitles=False,replace_audio=True,audio_path="D:/AI/油管视频汉化/2.mp3",skip_subtitle_generation=True,subtitle_file="D:/AI/油管视频汉化/subtitles/2_en-zh.srt")
    #VideoProcessor().burn_subtitles_to_video("D:/AI/油管视频汉化/2.mp4", "D:/AI/油管视频汉化/subtitles/2_en-zh.srt", "D:/AI/油管视频汉化/test_burned.mp4")