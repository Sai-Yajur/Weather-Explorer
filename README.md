
https://github.com/user-attachments/assets/9d0ad9a8-48b5-4f42-b896-83def665c033
# WEATHER EXPLORER

Weather Explorer is an API-based mapping and weather forecasting application built using Python (Python 3.13+) and its libraries. The application mainly uses CustomTkinter for the UI and the Requests library for API communication.

## Dependencies & Modules

**External Libraries:**

- `customtkinter`
- `requests`
- `Pillow` (installed using pip and imported as `PIL`)
- `matplotlib`
- `tkintermapview`

**Python Standard Libraries (built-in):**

- `os`
- `random`
- `threading`
- `tkinter`
- `datetime`

## Features

- Interactive and visually appealing GUI
- Interactive map
- Five-day weather forecast
- Current weather dashboard displaying location, local time, temperature, wind speed, humidity and weather conditions
- Embedded search bar
- Search using geographical coordinates (latitude and longitude)

## Development Process

I first started creating this application in Python after learning the basics of programming and gaining some knowledge of the Tkinter module. I initially focused on the UI, adding the animated Earth WebP and creating separate frames for the weather page and the About screen.

Once the UI started looking polished, I began working on the backend and integrating weather forecasting APIs. Later, the main UI was shifted from Tkinter to CustomTkinter to improve its appearance.

AI tools like ChatGPT also helped me understand deeper concepts such as threading and handling HTTP requests using the Requests module, while also assisting with parts of the frontend development.

## What I Learned

- The importance of using separate threads alongside the main thread to prevent the UI from freezing.
- Using the Requests module to handle HTTP requests and communicate with APIs.
- Handling file paths and working with external assets.
- Integrating different Python libraries into a single application.
- Animations and image handling with Pillow.

## Future Improvements

- **Air Quality & UV Monitoring:** Integrate additional OpenWeatherMap endpoints to display live Air Quality Index (AQI), pollutant levels and UV index.
- **Offline Data Caching:** Implement local storage using SQLite or JSON to cache recent weather searches and potentially support offline access to cached information.
- **Favourite Bookmarks:** Allow users to save frequently searched cities or coordinates for quick access to weather updates.
- **Severe Weather Alerts:** Introduce notifications and visual UI alerts for hazardous weather conditions, such as severe storms or extreme temperatures.

## Setup

Before running the application, create a Python file named `config.py` in the root directory of the project.

Refer to `config.example.py` for the required format and add your own OpenWeatherMap API key.

The actual `config.py` file is excluded from this repository to prevent exposing API credentials.

## Demo Video

https://github.com/user-attachments/assets/733e3f3c-d010-4386-8441-1ca697341b14
