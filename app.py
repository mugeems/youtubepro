import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from yt_dlp import YoutubeDL
import re
import requests

# Page config
st.set_page_config(
    page_title="YouTube Transcript & Summary",
    page_icon="🎥",
    layout="wide",
)

# Sidebar
with st.sidebar:
    st.header('🎥 YouTube Transcript & Summary', divider='gray')
    
    # API Settings
    with st.expander("Advanced Settings"):
        groq_api = st.text_input("Groq API Key", type="password")
        xai_api = st.text_input("xAI API Key", type="password")
    
    # Input URL
    video_url = st.text_input("Enter YouTube Video URL")
    
    # Choose Action
    action = st.radio(
        "Choose Action",
        ["Transcript", "Summary"]
    )
    
    if action == "Summary":
        summary_length = st.select_slider(
            "Summary Length",
            options=["Short", "Medium", "Long"],
            value="Medium"
        )
        
    # Choose AI Model
    model = st.radio(
        "Choose AI Model",
        ["Groq (Llama-3)", "xAI (Grok)"]
    )

def extract_video_id(url):
    pattern = r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_video_info(url):
    with YoutubeDL() as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title'),
                'description': info.get('description'),
                'thumbnail': info.get('thumbnail')
            }
        except Exception as e:
            st.error(f"Error fetching video info: {str(e)}")
            return None

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['id', 'en'])
        return transcript
    except Exception as e:
        st.error(f"Error fetching transcript: {str(e)}")
        return None

def format_transcript_with_timestamps(transcript):
    formatted = ""
    for entry in transcript:
        time = int(entry['start'])
        minutes = time // 60
        seconds = time % 60
        formatted += f"[{minutes:02d}:{seconds:02d}] {entry['text']}\n"
    return formatted

def generate_summary(transcript_text, model, api_key, length):
    length_tokens = {
        "Short": 300,
        "Medium": 600,
        "Long": 1000
    }
    
    if model == "Groq (Llama-3)":
        endpoint = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.2-90b-vision-preview",
            "messages": [{
                "role": "system",
                "content": f"Buatkan rangkuman dalam bahasa Indonesia dengan panjang sekitar {length_tokens[length]} kata dari transkrip berikut ini:"
            }, {
                "role": "user",
                "content": transcript_text
            }]
        }
    else:  # xAI (Grok)
        endpoint = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "grok-beta",
            "messages": [{
                "role": "system",
                "content": f"Buatkan rangkuman dalam bahasa Indonesia dengan panjang sekitar {length_tokens[length]} kata dari transkrip berikut ini:"
            }, {
                "role": "user",
                "content": transcript_text
            }]
        }

    try:
        response = requests.post(endpoint, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"Error generating summary: {str(e)}")
        return None

def main():
    if not video_url:
        st.info("Please enter a YouTube URL to begin")
        return

    video_id = extract_video_id(video_url)
    if not video_id:
        st.error("Invalid YouTube URL")
        return

    video_info = get_video_info(video_url)
    if not video_info:
        return

    transcript = get_transcript(video_id)
    if not transcript:
        return

    # Display video info
    st.title(video_info['title'])
    st.image(video_info['thumbnail'])

    if action == "Transcript":
        st.subheader("📝 Transcript with Timestamps")
        formatted_transcript = format_transcript_with_timestamps(transcript)
        st.text_area("", formatted_transcript, height=400)
        st.download_button(
            "Download Transcript",
            formatted_transcript,
            file_name=f"{video_info['title']}_transcript.txt"
        )
    else:  # Summary
        if not (groq_api if model == "Groq (Llama-3)" else xai_api):
            st.error(f"Please provide {model} API key in Advanced Settings")
            return

        st.subheader("📚 Summary")
        transcript_text = " ".join([t['text'] for t in transcript])
        summary = generate_summary(
            transcript_text,
            model,
            groq_api if model == "Groq (Llama-3)" else xai_api,
            summary_length
        )
        
        if summary:
            st.markdown(summary)
            st.download_button(
                "Download Summary",
                summary,
                file_name=f"{video_info['title']}_summary.txt"
            )

if __name__ == "__main__":
    main()
