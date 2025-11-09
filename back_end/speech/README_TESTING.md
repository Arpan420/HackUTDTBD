# Testing the Speech Handler and Agentic Framework

## Quick Start

### 1. Install Dependencies

Make sure you have the required packages installed:

```bash
source venv/bin/activate
pip install -r speech/requirements.txt
pip install pyaudio  # For microphone input
```

### 2. Set Up Environment Variables

Make sure your `.env` file has:

```
NVIDIA_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/dbname  # Optional, for database features
```

### 3. Run Tests

**Test Speech Handler Only:**

```bash
cd speech
python test_speech_handler.py
```

**Test Full Agentic System (Microphone → Agent → Response):**

```bash
cd speech
python test_full_system.py
```

**Test with Simulated Audio (no microphone needed):**

```bash
cd speech
python test_full_system.py --simulate
```

**Minimal Test (simplest example):**

```bash
cd speech
python minimal/test_mic_transcription.py
```

## What to Expect

### Speech Handler Test

1. The script will initialize the speech handler and connect to NVIDIA NIM
2. If using microphone: Speak into your microphone
3. You'll see transcriptions appear in real-time as you speak
4. Press Ctrl+C to stop

### Full System Test

1. The system listens to your microphone
2. Transcribes your speech in real-time
3. Detects when you finish speaking (turn detection)
4. Sends your utterance to the agent
5. Gets agent response and displays it
6. Continues the conversation

## Technical Details

### NVIDIA NIM Configuration

- **Endpoint**: `grpc.nvcf.nvidia.com:443`
- **Function-ID UUID**: `1598d209-5e27-4d3c-8079-4751568b1081` (required for NIM)
- **API Type**: Uses high-level streaming API (`streaming_response_generator`)
- **Model**: parakeet-ctc-1.1b-asr

### Streaming vs Batch Processing

The system uses the **high-level streaming API** which works with NVIDIA NIM. This provides:

- Real-time transcription as audio is processed
- Interim results (partial transcriptions)
- Final results when speech segments are complete

The streaming API expects an iterable of audio chunks (bytes) and returns a generator of transcription responses.

## Troubleshooting

### "pyaudio not available"

- Install pyaudio: `pip install pyaudio`
- On macOS, you may need: `brew install portaudio` first
- On Linux, you may need: `sudo apt-get install portaudio19-dev`

### "NVIDIA_API_KEY not found"

- Make sure `.env` file exists in the project root
- Check that the API key is set correctly

### "Failed to connect to Riva server" or "failed to open stateful work request"

- Check your internet connection
- Verify the API key is valid and set in `.env` file
- Make sure you're using the correct function-id UUID: `1598d209-5e27-4d3c-8079-4751568b1081`
- Check if the NIM endpoint is accessible: `grpc.nvcf.nvidia.com:443`

### No transcriptions appearing

- Make sure your microphone is working
- Check microphone permissions (macOS/Linux)
- Try speaking louder or closer to the microphone
- Check that audio format matches (16kHz, 16-bit PCM, mono)

## Testing the Full System

### Unit Tests

Run comprehensive unit tests for all components:

```bash
python speech/test_conversation_system.py
```

### End-to-End Integration Test

Test the complete pipeline with real microphone input:

```bash
python speech/test_full_system.py
```

This tests:

- Speech recognition (microphone → transcription)
- Turn detection (detecting when user finishes speaking)
- Agent processing (LLM + tool calling)
- Response generation
- Conversation state management
- Database integration (memories and todos)

### Component Tests

- **Speech Handler**: `python speech/test_speech_handler.py`
- **Minimal Example**: `python speech/minimal/test_mic_transcription.py`
- **Unit Tests**: `python speech/test_conversation_system.py`
