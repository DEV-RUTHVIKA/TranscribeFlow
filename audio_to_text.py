import whisper

# Load Whisper model once
model = whisper.load_model("base", device="cpu")
print("Whisper loaded successfully!")


def transcribe_audio(audio_file):
    result = model.transcribe(audio_file)
    return result['text']


# --- Example Usage ---
if __name__ == "__main__":
    audio_file = "uploads\\sample.mp3"
    text = transcribe_audio(audio_file)
    print("\n📝 Transcribed Text:\n", text)
    # Save transcription to a text file
    txt_filename = f"{audio_file}.txt"

    with open(txt_filename, "w", encoding="utf-8") as file:
        file.write(text)

    print(f"📁 Transcription saved to: {txt_filename}")
