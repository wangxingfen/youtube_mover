import edge_tts
import asyncio
async def text_to_speech_edge(
    text: str,
    voice: str = "zh-CN-YunxiNeural",
    rate: str = "+50%",
    volume: str = "+200%",
    filename: str = None
) -> str:
    """
    Convert text to speech using Edge TTS (online Microsoft voices)
    
    Args:
        text: Input string to be spoken
        voice: Voice name (default: zh-CN-YunxiNeural)
        rate: Speaking rate adjustment (e.g. "+10%" or "-10%")
        volume: Volume adjustment (e.g. "+10%" or "-10%")
        filename: Optional output path to save as .mp3 file
        
    Returns:
        Path to saved file if filename provided, else None
        
    Raises:
        ValueError: If input text is empty or not a string
        RuntimeError: If TTS fails
    """
    if not text or not isinstance(text, str):
        raise ValueError("Input text must be a non-empty string")
    
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
        
        if filename:
            await communicate.save(filename)
            return filename
        else:
            await communicate.stream()
            return None
            
    except Exception as e:
        raise RuntimeError(f"Edge TTS failed: {str(e)}") from e
async def get_chinese_voices_list():
    voice_list = await edge_tts.list_voices()
    # Filter for Chinese voices
    voice_list = [voice["ShortName"] for voice in voice_list if voice["Locale"].startswith("en-")]
    print(voice_list)
    return voice_list
if __name__ == "__main__":
    asyncio.run(get_chinese_voices_list())
    path="10.mp3"
    asyncio.run(text_to_speech_edge("who you are?",voice="en-CA-LiamNeural",filename=path))
    #print(index_tts("你是谁？好像在哪里见过你呀。",refer_voice_path=r"C:\Users\wangxingfeng\Music\cangjiao.wav", infer_mode="批次推理"))