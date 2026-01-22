import os
import torch
import argparse
import gradio as gr
import langid
from openvoice import se_extractor
from openvoice.api import ToneColorConverter

# Try importing MeloTTS, if not available prompt user to install
try:
    from melo.api import TTS
except ImportError:
    raise ImportError("MeloTTS is not installed. Please run `pip install git+https://github.com/myshell-ai/MeloTTS.git` or use `setup_env.bat`.")

# Argument Parser
parser = argparse.ArgumentParser()
parser.add_argument("--share", action='store_true', default=False, help="make link public")
args = parser.parse_args()

# Configuration
ckpt_converter = 'checkpoints_v2/converter'
device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
output_dir = 'outputs_v2'
os.makedirs(output_dir, exist_ok=True)

# Global Models Cache
tone_color_converter = None
model_cache = {}

def load_models():
    global tone_color_converter
    try:
        tone_color_converter = ToneColorConverter(f'{ckpt_converter}/config.json', device=device)
        tone_color_converter.load_ckpt(f'{ckpt_converter}/checkpoint.pth')
        print("[INFO] Tone Color Converter loaded successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to load Tone Color Converter from {ckpt_converter}. \nDid you download the V2 checkpoints? Error: {e}")
        tone_color_converter = None

# Supported Languages & Accents mapping for MeloTTS
# Key: UI Label, Value: MeloTTS language code
LANGUAGES = {
    "English (American)": "EN", # Default EN in Melo is usually American/Mixed, but we can specify accents if supported by the installed melo version. 
    # MeloTTS logic: TTS(language='EN') -> checks config. 
    # Actually MeloTTS supports 'EN', 'ES', 'FR', 'ZH', 'JP', 'KR'. 
    # Accents are often handled by speaker IDs within 'EN'.
    "Spanish": "ES",
    "French": "FR",
    "Chinese": "ZH",
    "Japanese": "JP",
    "Korean": "KR"
}

# Example speakers provided by OpenVoice (paths need to exist)
examples = [
    ["The weather is beautiful today, let's go for a walk.", "English (American)", "resources/demo_speaker1.mp3", True],
    ["El resplandor del sol acaricia las olas.", "Spanish", "resources/demo_speaker2.mp3", True],
    ["La vie est belle quand on prend le temps.", "French", "resources/demo_speaker0.mp3", True],
]

def predict(prompt, language_label, ref_audio_path, agree):
    # 1. Validation
    if not agree:
        gr.Warning("Please set the 'Agree' checkbox to proceed.")
        return None
    
    if tone_color_converter is None:
        gr.Warning("Tone Color Converter model is not loaded. Please check console for errors regarding missing checkpoints.")
        return None

    if not prompt or not prompt.strip():
        gr.Warning("Please enter text to synthesize.")
        return None
    
    if not ref_audio_path:
        gr.Warning("Please provide a reference audio file.")
        return None

    language = LANGUAGES.get(language_label, "EN")

    # 2. Get Tone Color of Reference Speaker
    try:
        # se_extractor requires a target directory for caching se
        target_se, audio_name = se_extractor.get_se(ref_audio_path, tone_color_converter, target_dir='processed', vad=True)
    except Exception as e:
        error_msg = f"Error extracting tone color: {str(e)}"
        print(error_msg)
        gr.Warning(error_msg)
        return None

    # 3. Generate Base Audio with MeloTTS
    # Check cache for model
    if language not in model_cache:
        print(f"[INFO] Loading MeloTTS model for {language}...")
        try:
           model_cache[language] = TTS(language=language, device=device)
        except Exception as e:
            error_msg = f"Failed to load MeloTTS model for {language}: {e}"
            print(error_msg)
            gr.Warning(error_msg)
            return None
    
    model = model_cache[language]
    speaker_ids = model.hps.data.spk2id
    
    # Use the first available speaker for the language as base
    # (MeloTTS usually provides 'EN-US', 'EN-BR' etc for EN, but 'Default' or single speaker for others)
    # For simplicity, we pick the first one.
    speaker_key = list(speaker_ids.keys())[0]
    speaker_id = speaker_ids[speaker_key]
    
    src_path = f'{output_dir}/tmp_{language}.wav'
    
    # Generate TTS
    # speed 1.0 default
    model.tts_to_file(prompt, speaker_id, src_path, speed=1.0)

    # 4. Tone Color Conversion
    save_path = f'{output_dir}/output_v2_{language}.wav'
    
    # Load source speaker embedding from MeloTTS (it's inside checkpoints_v2/base_speakers/ses usually, 
    # but MeloTTS api might manage it differently or OpenVoice requires explicit path)
    # Inspecting OpenVoice demo_part3.ipynb:
    # source_se = torch.load(f'checkpoints_v2/base_speakers/ses/{speaker_key}.pth', map_location=device)
    # We need to ensure we can find this file.
    
    # MeloTTS uses underscores, OpenVoice checkponits might use hyphens or vice versa.
    # demo logic: speaker_key = speaker_key.lower().replace('_', '-')
    
    speaker_key_clean = speaker_key.lower().replace('_', '-')
    source_se_path = f'checkpoints_v2/base_speakers/ses/{speaker_key_clean}.pth'
    
    if not os.path.exists(source_se_path):
        # Fallback or error?
        # Maybe user didn't download base_speakers/ses?
        # The demo implies these exist in checkpoints_v2.
        pass

    try:
        source_se = torch.load(source_se_path, map_location=device)
    except FileNotFoundError:
        msg = f"Could not find source speaker embedding at {source_se_path}. Please ensure 'checkpoints_v2/base_speakers/ses' exists."
        print(msg)
        gr.Warning(msg)
        return None

    encode_message = "@MyShell"
    tone_color_converter.convert(
        audio_src_path=src_path, 
        src_se=source_se, 
        tgt_se=target_se, 
        output_path=save_path,
        message=encode_message
    )

    return save_path

# UI Construction
with gr.Blocks(title="OpenVoice V2") as demo:
    gr.Markdown("## OpenVoice V2 (Unofficial Local Web UI)")
    gr.Markdown("Instant voice cloning with multi-lingual support using OpenVoice V2 and MeloTTS.")
    
    with gr.Row():
        with gr.Column():
            input_text = gr.Textbox(label="Text Prompt", value="Hello, this is a test of OpenVoice Version 2.", lines=3)
            language_dropdown = gr.Dropdown(choices=list(LANGUAGES.keys()), value="English (American)", label="Language")
            ref_audio = gr.Audio(label="Reference Audio (Voice to Clone)", type="filepath")
            tos_checkbox = gr.Checkbox(label="I agree to the Terms of Service (CC-BY-NC-4.0)", value=False)
            generate_btn = gr.Button("Generate Voice", variant="primary")
        
        with gr.Column():
            output_audio = gr.Audio(label="Generated Audio", type="filepath")
    
    generate_btn.click(
        fn=predict,
        inputs=[input_text, language_dropdown, ref_audio, tos_checkbox],
        outputs=[output_audio]
    )
    
    gr.Markdown("### Notes")
    gr.Markdown("- Ensure you have downloaded **V2 Checkpoints** into `checkpoints_v2`.")
    gr.Markdown("- Ensure **MeloTTS** is installed.")

if __name__ == "__main__":
    load_models()
    demo.queue()
    demo.launch(share=args.share, show_api=True)
