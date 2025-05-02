Air 30X: Real-Time Air Quality and Health Guidance 🌍
Air 30X is a Streamlit-based app that delivers real-time air quality and weather insights for cities like Dhaka, empowering users to protect their health and combat climate change. Using APIs like IQAir, OpenWeatherMap, and Mapbox, it provides AQI, health recommendations, historical air quality graphs, and more. A voice call AI agent (powered by ElevenLabs) offers instant medical advice, such as “drink 2–3 liters of fresh water daily,” helping users tackle pollution’s 7 million annual deaths (WHO, 2021). Air 30X supports all 17 SDGs and aims to reach 2.5 billion people in polluted regions by 2030 (UNEP, 2024).
Features

Real-Time Data: AQI, health recommendations, historical air quality graphs, most polluted locations near cities like Dhaka, today’s weather, 7-day weather and AQI forecasts, top 10 most polluted cities globally, and a world air pollution map.
Voice AI Guidance: Instant medical advice via a voice call AI agent, e.g., “limit outdoor time to 30 minutes at AQI >150.”
SDG Impact: Reduces 13% of pollution-linked asthma cases (Anenberg et al., 2018) while supporting global sustainability goals.
User-Friendly Interface: Built with Streamlit for easy navigation and data visualization.

Prerequisites

Python (latest version recommended, e.g., 3.12)
API keys for:
IQAir
OpenWeatherMap
Mapbox
ElevenLabs (for voice AI)



Installation

Clone the Repository:
git clone https://github.com/your-username/air30x.git
cd air30x


Set Up a Virtual Environment (recommended):
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install Dependencies:
pip install -r requirements.txt

Dependencies listed in requirements.txt:

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


Configure API Keys:

Run streamlit run app.py and enter your API keys (IQAir, OpenWeatherMap, Mapbox, ElevenLabs) in the Streamlit sidebar as prompted.



Usage

Run the App:streamlit run app.py


Access the App:
Open your browser and go to http://localhost:8501.
Enter your API keys in the sidebar.
Search for a city (e.g., Dhaka) to view air quality, weather data, and health recommendations.
Use the voice AI feature to get real-time medical advice (no additional setup required).



Project Structure

app.py: Main application file for Air 30X.
requirements.txt: List of Python dependencies.
Developer_Photo_Covar.png: Developer photo for project representation (displayed below).

Screenshots
[Add screenshots of the app’s dashboard, e.g., AQI gauge, heat map, or voice AI interface. Create a /screenshots folder, upload images, and link them here, e.g., ![Dashboard](screenshots/dashboard.png).]
Visual Representation

Contributing
Contributions are welcome! Please fork the repository, create a new branch, and submit a pull request with your changes.
License
This project is licensed under the MIT License. See the LICENSE file for details.
Contact
For questions or support, reach out at:  

Email: mail.mdmahbuburrahman@gmail.com  
WhatsApp: 01644274016
