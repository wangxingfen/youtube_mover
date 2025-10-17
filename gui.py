import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from video_processor_pro import simple_process


class VideoProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube视频汉化工具")
        self.root.geometry("600x700")
        
        # Variables for form fields
        self.video_path = tk.StringVar()
        self.output_dir = tk.StringVar(value="D:/AI/油管视频汉化/subtitles")
        self.model_size = tk.StringVar(value="medium")
        self.volume_factor = tk.DoubleVar(value=3.0)
        self.add_translation = tk.BooleanVar(value=True)
        self.burn_subtitles = tk.BooleanVar(value=True)
        self.replace_audio = tk.BooleanVar(value=True)
        self.skip_subtitle_generation = tk.BooleanVar(value=False)
        # 新增：批量处理目录变量
        self.batch_directory = tk.StringVar()
        self.is_batch_mode = tk.BooleanVar(value=False)
        
        # Create UI
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="YouTube视频汉化工具", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Batch mode toggle
        ttk.Checkbutton(main_frame, text="批量处理模式", variable=self.is_batch_mode, command=self.toggle_batch_mode).grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Video Path (single file mode)
        self.single_file_label = ttk.Label(main_frame, text="视频文件路径:")
        self.single_file_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.video_path).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(0, 5))
        ttk.Button(main_frame, text="浏览...", command=self.browse_video).grid(row=2, column=2, pady=5)
        
        # Batch Directory (batch mode)
        self.batch_dir_label = ttk.Label(main_frame, text="视频文件目录:")
        self.batch_dir_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.batch_directory).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(0, 5))
        ttk.Button(main_frame, text="浏览...", command=self.browse_batch_directory).grid(row=3, column=2, pady=5)
        
        # Initially hide batch mode elements
        self.batch_dir_label.grid_remove()
        self.batch_directory.set("")
        
        # Output Directory
        ttk.Label(main_frame, text="输出目录:").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_dir).grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5, padx=(0, 5))
        ttk.Button(main_frame, text="浏览...", command=self.browse_output_dir).grid(row=4, column=2, pady=5)
        
        # Model Size
        ttk.Label(main_frame, text="模型大小:").grid(row=5, column=0, sticky=tk.W, pady=5)
        model_sizes = ["tiny", "base", "small", "medium", "large"]
        ttk.Combobox(main_frame, textvariable=self.model_size, values=model_sizes, state="readonly").grid(
            row=5, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Volume Factor
        ttk.Label(main_frame, text="音量倍数:").grid(row=6, column=0, sticky=tk.W, pady=5)
        volume_spinbox = ttk.Spinbox(main_frame, from_=0.1, to=10.0, increment=0.1, textvariable=self.volume_factor)
        volume_spinbox.grid(row=6, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Checkboxes
        ttk.Checkbutton(main_frame, text="添加中文翻译", variable=self.add_translation).grid(
            row=7, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Checkbutton(main_frame, text="烧录字幕到视频", variable=self.burn_subtitles).grid(
            row=8, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Checkbutton(main_frame, text="替换原音频", variable=self.replace_audio).grid(
            row=9, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Checkbutton(main_frame, text="跳过字幕生成", variable=self.skip_subtitle_generation).grid(
            row=10, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Process Button
        self.process_button = ttk.Button(main_frame, text="开始处理", command=self.start_processing)
        self.process_button.grid(row=11, column=0, columnspan=3, pady=20)
        
        # Progress Text
        ttk.Label(main_frame, text="处理日志:").grid(row=12, column=0, sticky=tk.W, pady=(10, 5))
        self.progress_text = tk.Text(main_frame, height=15, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.progress_text.yview)
        self.progress_text.configure(yscrollcommand=scrollbar.set)
        self.progress_text.grid(row=13, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        scrollbar.grid(row=13, column=2, sticky=(tk.N, tk.S), pady=(0, 10))
        
        # Configure row weights for resizing
        main_frame.rowconfigure(13, weight=1)
        
    def toggle_batch_mode(self):
        """切换批量处理模式"""
        if self.is_batch_mode.get():
            # 显示批量处理控件，隐藏单文件控件
            self.single_file_label.grid_remove()
            self.batch_dir_label.grid()
            if not self.batch_directory.get():
                self.batch_directory.set(os.path.dirname(self.video_path.get()) if self.video_path.get() else "")
        else:
            # 显示单文件控件，隐藏批量处理控件
            self.single_file_label.grid()
            self.batch_dir_label.grid_remove()
            if not self.video_path.get() and self.batch_directory.get():
                # 尝试设置一个默认文件
                batch_dir = self.batch_directory.get()
                if os.path.exists(batch_dir):
                    try:
                        files = [f for f in os.listdir(batch_dir) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
                        if files:
                            self.video_path.set(os.path.join(batch_dir, files[0]))
                    except:
                        pass
                        
    def browse_video(self):
        filename = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv"), ("所有文件", "*.*")]
        )
        if filename:
            self.video_path.set(filename)
            
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir.set(directory)
            
    # 新增：浏览批量处理目录
    def browse_batch_directory(self):
        directory = filedialog.askdirectory(title="选择批量处理目录")
        if directory:
            self.batch_directory.set(directory)
            
    def start_processing(self):
        # Disable the process button during processing
        self.process_button.config(state=tk.DISABLED)
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.delete(1.0, tk.END)
        self.progress_text.config(state=tk.DISABLED)
        
        # Start processing in a separate thread to prevent UI freezing
        thread = threading.Thread(target=self.process_video)
        thread.start()
        
    def process_video(self):
        try:
            if self.is_batch_mode.get():
                # 批量处理模式
                if not self.batch_directory.get():
                    self.show_error("请选择批量处理目录")
                    return
                    
                if not os.path.exists(self.batch_directory.get()):
                    self.show_error("批量处理目录不存在")
                    return
                    
                # 获取目录中的所有视频文件
                video_extensions = ('.mp4', '.avi', '.mov', '.mkv')
                video_files = [f for f in os.listdir(self.batch_directory.get()) 
                              if f.lower().endswith(video_extensions)]
                
                if not video_files:
                    self.show_error("指定目录中没有找到视频文件")
                    return
                    
                self.log_message(f"开始批量处理目录: {self.batch_directory.get()}")
                self.log_message(f"找到 {len(video_files)} 个视频文件")
                
                # 处理每个视频文件
                for i, video_file in enumerate(video_files, 1):
                    video_path = os.path.join(self.batch_directory.get(), video_file)
                    self.log_message(f"\n正在处理 ({i}/{len(video_files)}): {video_file}")
                    
                    try:
                        output_path = simple_process(
                            video_path=video_path,
                            output_dir=self.output_dir.get(),
                            add_translation=self.add_translation.get(),
                            model_size=self.model_size.get(),
                            burn_subtitles=self.burn_subtitles.get(),
                            replace_audio=self.replace_audio.get(),
                            skip_subtitle_generation=self.skip_subtitle_generation.get(),
                            volume_factor=self.volume_factor.get()
                        )
                        
                        if output_path:
                            self.log_message(f"  完成: {video_file} -> {output_path}")
                        else:
                            self.log_message(f"  失败: {video_file}")
                            
                    except Exception as e:
                        self.log_message(f"  错误: {video_file} - {str(e)}")
                        
                self.log_message(f"\n批量处理完成! 共处理 {len(video_files)} 个文件")
                self.show_info(f"批量处理完成! 共处理 {len(video_files)} 个文件")
                
            else:
                # 单文件处理模式
                if not self.video_path.get():
                    self.show_error("请选择视频文件")
                    return
                    
                if not os.path.exists(self.video_path.get()):
                    self.show_error("视频文件不存在")
                    return
                    
                # Show start message
                self.log_message(f"开始处理视频: {self.video_path.get()}")
                
                # Call the processing function
                output_path = simple_process(
                    video_path=self.video_path.get(),
                    output_dir=self.output_dir.get(),
                    add_translation=self.add_translation.get(),
                    model_size=self.model_size.get(),
                    burn_subtitles=self.burn_subtitles.get(),
                    replace_audio=self.replace_audio.get(),
                    skip_subtitle_generation=self.skip_subtitle_generation.get(),
                    volume_factor=self.volume_factor.get()
                )
                
                if output_path:
                    self.log_message(f"处理完成! 输出文件: {output_path}")
                    self.show_info("视频处理完成!")
                else:
                    self.log_message("处理失败!")
                    self.show_error("视频处理失败，请查看日志")
                
        except Exception as e:
            self.log_message(f"处理过程中出现错误: {str(e)}")
            self.show_error(f"处理出错: {str(e)}")
        finally:
            # Re-enable the process button
            self.root.after(0, lambda: self.process_button.config(state=tk.NORMAL))
            
    def log_message(self, message):
        self.root.after(0, lambda: self._log_message_thread_safe(message))
        
    def _log_message_thread_safe(self, message):
        self.progress_text.config(state=tk.NORMAL)
        self.progress_text.insert(tk.END, message + "\n")
        self.progress_text.see(tk.END)
        self.progress_text.config(state=tk.DISABLED)
        
    def show_error(self, message):
        self.root.after(0, lambda: messagebox.showerror("错误", message))
        
    def show_info(self, message):
        self.root.after(0, lambda: messagebox.showinfo("信息", message))


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoProcessorGUI(root)
    root.mainloop()