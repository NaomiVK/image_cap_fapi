# Image Alt Text Generator

A FastAPI application that generates alt text descriptions for images and PDFs with French translations.

## Features

- Upload and process multiple images and PDFs
- Generate concise alt text for images
- Extract and summarize text content from PDFs
- Automatic translation to French
- Export descriptions to CSV
- Copy text functionality

## Requirements

- Python 3.8+
- System dependencies (install via apt on Debian/Ubuntu):
  - tesseract-ocr
  - libtesseract-dev
  - poppler-utils

## Installation

1. Clone the repository
2. Install the system dependencies:
   ```
   sudo apt-get update
   sudo apt-get install -y tesseract-ocr libtesseract-dev poppler-utils
   ```
3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
OPENROUTER_API_KEY=your_openrouter_api_key
```

## Usage

1. Start the FastAPI server:
   ```
   python main.py
   ```
   
2. Open your browser and navigate to `http://localhost:8000`

3. Upload images or PDFs using the form

4. View the generated descriptions and translations

5. Download the CSV file with all descriptions

## API Endpoints

- `GET /`: Home page with upload form
- `POST /upload/`: Upload and process files
- `GET /download-csv/`: Download the CSV file with all descriptions
- `GET /reset/`: Reset the application (clear temporary files and CSV data)
- `GET /health`: Health check endpoint to verify the API is running

## Notes

- The application uses LM Studio API for image analysis, which should be running locally at `http://localhost:1234`
- French translations are provided by OpenRouter API using the Mixtral model