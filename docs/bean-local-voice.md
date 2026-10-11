# Talk to BEAN — local Ollama + Windows voice

BEAN can have a spoken conversation on your Windows PC. Press Enter to use the microphone; BEAN answers through your local Ollama model and Windows speakers. Typing works as well.

This is a **conversation interface**, not a replacement for BEAN's identity, evidence memory, or engineering tools. The model cannot control motors, execute shell commands, change files, or claim capabilities it hasn't verified.

## Quick start (PowerShell)

From the BEAN repository directory after Ollama and a chat model are installed:

    ollama list
    python -m bean.voice --talk

Or:

    .\scripts\bean_talk.ps1

The interface selects an already-installed Ollama chat model without downloading anything. Select a specific installed model with:

    python -m bean.voice --talk --model YOUR_INSTALLED_MODEL_NAME

If Ollama has no models, download a chat model with the Ollama application first. BEAN's local API endpoint is http://127.0.0.1:11434. Ollama respects the OLLAMA_MODELS environment variable, including a preconfigured D:\Ollama\models folder.

## Talking with BEAN

Press **Enter** to listen once through the Windows microphone, or type a message after the You > prompt. BEAN prints its response and speaks it through the Windows default voice. Type /quit to exit. Type /help for commands.

Windows' built-in System.Speech recognizer and synthesizer are used. If recognition is not installed for your language or no microphone is present, typed conversation remains available. No background listening is enabled. Choose an installed SAPI voice with --voice-name "NAME" or change the speed with --rate 1. Windows voice mode needs Windows PowerShell 5.1 and the relevant Windows speech components.

Text-only conversation also works on Linux or macOS:

    python -m bean.voice

## BEAN's identity and continuity

The local model is a reasoning and voice tool, not BEAN's entire existing brain. BEAN's declared identity rules come directly from the Core identity module. The interface optionally reads existing SQLite identity and capability data, without modifying the DB. You can specify the existing BEAN database:

    python -m bean.voice --talk --brain-db "D:\path\to\bean_memory.db"

If there is no BEAN database yet, BEAN will identify itself from its declared Core records. A short rolling session history (up to eight exchanges) is kept in memory, but it is NOT yet a durable autobiographical memory mechanism. The interface cannot independently access private project files, GitHub, or robot hardware.

## Privacy and verified limitations

This integration uses only local Ollama and Windows speech. It never sends speech to a cloud provider or allows a remote Ollama hostname. Press Enter to capture one speech utterance; there is no automatic or background recording. Spoken text is passed on stdin to constant PowerShell code, never embedded as a script.

GitHub CI verifies behavior using offline mocks on Linux and Windows:

    python -m unittest bean.tests.test_local_voice -v

The actual microphone, recognizer language pack, voice selection, and Ollama performance must be verified on the PC where BEAN runs. Green CI cannot guarantee that Windows audio hardware is ready.
