import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import re
from groq import Groq
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Konfigurasi halaman
st.set_page_config(
    page_title="YouTube Video Summarizer",
    page_icon="🎥",
    layout="wide"
)

# Fungsi untuk mendapatkan video ID dari URL YouTube
def extract_video_id(url):
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

# Fungsi untuk mendapatkan transcript
def get_transcript(video_id, preferred_language='id'):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Debug info
        st.write("Available transcripts:", transcript_list.manual_generated_transcripts)
        
        # Coba dapatkan transcript dalam bahasa yang diinginkan
        try:
            transcript = transcript_list.find_transcript([preferred_language])
        except:
            try:
                transcript = transcript_list.find_transcript(['en'])
            except:
                try:
                    available_transcripts = transcript_list.find_generated_transcript([preferred_language, 'en'])
                    transcript = available_transcripts
                except:
                    transcript = transcript_list.find_transcript([])
        
        return transcript.fetch()
    except Exception as e:
        st.error(f"""
        Transcript tidak dapat diambil. Error: {str(e)}
        
        Kemungkinan penyebab:
        1. Video tidak memiliki subtitle
        2. Subtitle dinonaktifkan oleh pembuat video
        
        Saran:
        1. Coba video YouTube lain yang memiliki subtitle
        2. Pastikan video yang dipilih memiliki subtitle yang aktif
        """)
        return None

# Fungsi untuk merangkum transcript
def summarize_transcript(transcript_text, api_key):
    # Validasi API key
    if not api_key or len(api_key.strip()) == 0:
        st.error("Please provide a valid Groq API key in the settings")
        return None
    
    try:
        client = Groq(api_key=api_key)
        
        prompt = f"""
        Berikut adalah transkrip video YouTube. Tolong buatkan rangkuman yang informatif:

        {transcript_text}

        Rangkuman harus mencakup:
        1. Poin-poin utama
        2. Kesimpulan penting
        3. Format dalam bentuk bullet points
        """
        
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Anda adalah asisten yang ahli dalam merangkum konten dengan jelas dan informatif."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="mixtral-8x7b-32768",
            temperature=0.5,
        )
        
        return completion.choices[0].message.content
    
    except Exception as e:
        st.error(f"Error in summarization: {str(e)}")
        return None

def main():
    st.title("YouTube Video Summarizer 🎥")
    
    # Sidebar settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # API Key input
        api_key = st.text_input(
            "Groq API Key",
            value=st.secrets.get("GROQ_API_KEY", ""),
            type="password",
            help="Enter your Groq API key. Get one at https://console.groq.com"
        )
        
        # Language selection
        language = st.selectbox(
            "Preferred Language",
            ["Indonesian", "English"],
            help="Select preferred transcript language"
        )
        
        # Save API key to session state
        if api_key:
            st.session_state['api_key'] = api_key
        
        # Display API status
        if 'api_key' in st.session_state and st.session_state['api_key']:
            st.success("API Key is set! ✅")
        else:
            st.warning("API Key not set! ⚠️")
    
    # Language code mapping
    language_codes = {
        "Indonesian": "id",
        "English": "en"
    }
    
    # Main content
    st.write("### Enter YouTube URL 🔗")
    url = st.text_input("Paste the URL of the YouTube video you want to summarize:")
    
    if url:
        video_id = extract_video_id(url)
        if video_id:
            # Display video
            st.video(url)
            
            # Process button
            if st.button("🎯 Generate Summary", type="primary"):
                # Check API key
                if not api_key:
                    st.error("Please enter your Groq API key in the settings first!")
                    return
                
                # Get transcript
                with st.spinner("📝 Fetching transcript..."):
                    transcript = get_transcript(video_id, language_codes[language])
                    
                if transcript:
                    # Combine transcript text
                    transcript_text = " ".join([entry['text'] for entry in transcript])
                    
                    # Show raw transcript
                    with st.expander("📜 Show Raw Transcript"):
                        st.text(transcript_text)
                    
                    # Generate summary
                    with st.spinner("🤖 Generating summary..."):
                        summary = summarize_transcript(transcript_text, api_key)
                        if summary:
                            st.success("Summary generated successfully! ✨")
                            st.subheader("📋 Summary")
                            st.write(summary)
        else:
            st.error("❌ Invalid YouTube URL. Please check the URL and try again.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    ### 💡 Tips:
    - Make sure the video has subtitles enabled
    - Try different languages if one doesn't work
    - For best results, use videos with clear audio and proper subtitles
    """)

if __name__ == "__main__":
    main()
