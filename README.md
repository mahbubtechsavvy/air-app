# **Air 30X: Real-Time Air Quality and Health Guidance 🌍**

Air 30X is a Streamlit-powered app delivering real-time air quality and weather insights for cities like Dhaka, empowering users to combat pollution and climate change. Leveraging APIs from IQAir, OpenWeatherMap, and Mapbox, it provides AQI, health recommendations, historical air quality graphs, most polluted locations, 7-day weather and AQI forecasts, top 10 most polluted cities globally, and a world air pollution map. A voice call AI agent (powered by ElevenLabs) offers instant medical advice, such as “drink 2–3 liters of fresh water daily” or “limit outdoor time to 30 minutes at AQI >150,” addressing 7 million annual pollution deaths (WHO, 2021). Supporting all 17 SDGs, Air 30X aims to reach 2.5 billion people in polluted regions by 2030 (UNEP, 2024).

# **Demo Video**
Click the image below to watch a demo of Air 30X in action, showcasing its dashboard, voice AI, and more:

# **Features**

- Real-time AQI, health recommendations, and historical air quality graphs for cities like Dhaka.
- Most polluted locations near your city and a world air pollution map.
- Today’s weather, 7-day weather, and AQI forecasts.
- Top 10 live most polluted major cities globally.
- Voice AI agent providing instant medical advice via ElevenLabs.
- SDG-aligned impact, reducing 13% of pollution-linked asthma cases (Anenberg et al., 2018).

# **Prerequisites**

- Python (latest version recommended, e.g., 3.12)
- API keys for:
 - IQAir
 - OpenWeatherMap
 - WAQI 
 - Mapbox
 - ElevenLabs



# **Installation**

**1. Clone the Repository:**
git clone https://github.com/mahbubtechsavvy/ai-app.git
cd ai-app


**2. Set Up a Virtual Environment (recommended):**
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


**3. Install Dependencies:**
pip install -r requirements.txt

Dependencies (from requirements.txt):

streamlit==1.36.0
plotly==5.24.1
requests==2.32.3
pandas==2.2.3
beautifulsoup4==4.12.3
altair==5.3.0
rich==13.7.1
markdown-it-py==3.0.0
mdurl==0.1.2
pygments==2.18.0
matplotlib==3.9.2


**4. Configure API Keys:**

- Run the app and enter your IQAir, OpenWeatherMap, Mapbox, and
ElevenLabs API keys in the Streamlit sidebar.



# **Usage**

**1. Run the App:**
streamlit run app.py


**2. Explore the App:**
- Open http://localhost:8501 in your browser.
- Input API keys in the sidebar.
- Search a city (e.g., Dhaka) to access air quality, weather, and health data.
- Engage the voice AI for real-time medical advice.



# **Project Structure**

- app.py: Main application file.
- requirements.txt: Dependency list.
- Developer_Photo_Covar.png: Developer photo (see below).


# **Contributing**
Contributions are welcome! Fork this repository, create a branch, and submit a pull request with your improvements.

# **License**
This project is licensed under the MIT License. See the LICENSE file for details.

# **Contact**
For support or inquiries:  

- Email: mail.mdmahbuburrahman@gmail.com  
- WhatsApp: 01644274016

