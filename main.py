import io
import csv
import base64
from typing import List, Optional
import requests
from fastapi import FastAPI, File, UploadFile, Request, Form, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from pdf2image import convert_from_bytes
import uvicorn
import os
from config import OPENROUTER_API_KEY, LM_STUDIO_API_URL, OPENROUTER_API_URL, HOST, PORT, DEBUG

app = FastAPI(title="Image Alt Text Generator", description="Generate alt text descriptions for images and PDFs with French translations")

# Create directories if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("static/temp", exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Reuse functions from the original application
def convert_pdf_to_images(pdf_bytes):
    """Convert PDF bytes to list of PIL Images"""
    try:
        images = convert_from_bytes(pdf_bytes)
        return images
    except Exception as e:
        print(f"Error converting PDF: {str(e)}")
        return []

def get_vision_analysis(image, is_pdf=False, vision_model="meta-llama/llama-3.2-11b-vision-instruct"):
    """Send image to OpenRouter API and get analysis"""
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')

    if is_pdf:
        prompt = (
            "Analyze and describe the text content in this page. "
            "Format your response with HTML tags for better readability: "
            "<p> for paragraphs, <ul><li> for bullet points, <ol><li> for numbered lists, "
            "<h3> for section headings, and <br> for line breaks. "
            "Maintain any hierarchical structure present in the text. "
            "Use clear section breaks if multiple topics are covered. "
            "Be thorough but concise, and ensure the formatting enhances readability."
        )
        max_tokens = 800  # Increased to allow for formatting characters
    else:
        prompt = (
            "Create a short, concise alt text for this image suitable for a website. "
            "DO NOT start with phrases like 'The image depicts', 'The image shows', or similar. "
            "Instead, directly describe the main subject in 15-20 words maximum. "
            "Focus only on the key elements necessary for accessibility. "
            "Use simple, direct language without unnecessary words."
        )
        max_tokens = 50

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}},
                {"type": "text", "text": prompt}
            ]
        }
    ]

    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": messages,
            "model": vision_model,
            "temperature": 0.7,
            "max_tokens": max_tokens,
            "top_p": 0.90
        }
        
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        analysis = response.json()['choices'][0]['message']['content'].strip()
        
        # Ensure proper HTML formatting for PDF descriptions
        if is_pdf and not analysis.startswith("<"):
            # If the LLM didn't use HTML tags, add basic formatting
            analysis = analysis.replace("\n\n", "</p><p>")
            analysis = analysis.replace("\n", "<br>")
            analysis = analysis.replace("• ", "<br>• ")
            analysis = analysis.replace("- ", "<br>- ")
            analysis = f"<p>{analysis}</p>"
        return analysis
    except Exception as e:
        return f"Error getting analysis: {str(e)}"

def translate_to_french(text: str) -> str:
    """Translate text to French using OpenRouter API with mistralai/mixtral-8x7b-instruct model"""
    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY not found in environment variables")
        return ""

    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Enhanced system prompt for better formatting preservation
        system_prompt = (
            "You are a professional translator specializing in English to French translation. "
            "Your task is to translate the following text while preserving:"
            "\n1. All HTML tags and formatting (<p>, <br>, <ul>, <li>, <ol>, <h3>, etc.)"
            "\n2. The original text's structure and hierarchy"
            "\n3. Any special characters or markup"
            "\nProvide ONLY the direct translation without any explanations or notes."
            "\nDO NOT modify, remove, or add any HTML tags that are in the original text."
        )
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "model": "mistralai/mixtral-8x7b-instruct",
            "temperature": 0.3,
            "max_tokens": 1500  # Increased to handle longer formatted text
        }
        
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        translation = response.json()["choices"][0]["message"]["content"].strip()
        return translation
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return ""

def write_to_csv(image_name: str, description: Optional[str], long_description: Optional[str] = None,
                french_description: Optional[str] = None, french_long_description: Optional[str] = None):
    """Write descriptions to CSV file with French translations"""
    file_exists = False
    try:
        with open('image_descriptions.csv', 'r', encoding='utf-8') as f:
            file_exists = True
    except FileNotFoundError:
        pass

    with open('image_descriptions.csv', mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow([
                "Image filename",
                "Image alt text (English)",
                "Image alt text (French)",
                "PDF description (English)",
                "PDF description (French)"
            ])
        
        if long_description is not None:
            writer.writerow([
                image_name,
                description or "",
                french_description or "",
                long_description,
                french_long_description or ""
            ])
        else:
            writer.writerow([
                image_name,
                description or "",
                french_description or "",
                "",
                ""
            ])

def save_temp_image(image, filename):
    """Save image to temporary file for display"""
    # Create a safe filename
    safe_filename = "".join([c if c.isalnum() or c in ['.', '_', '-'] else '_' for c in filename])
    filepath = f"static/temp/{safe_filename}"
    image.save(filepath)
    return filepath

# FastAPI routes
@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running"""
    return {"status": "ok", "message": "API is running"}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload/")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    vision_model: str = Query(
        "meta-llama/llama-3.2-11b-vision-instruct",
        description="Vision model to use for analysis"
    )
):
    if not files:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": "No files were uploaded. Please select at least one file."}
        )
    
    results = []
    
    for file in files:
        try:
            file_content = await file.read()
            filename = file.filename
        except Exception as e:
            print(f"Error reading file {file.filename}: {str(e)}")
            continue
        
        try:
            if file.content_type == "application/pdf":
                # Process PDF
                pdf_images = convert_from_bytes(file_content)
                pdf_results = []
                
                for idx, image in enumerate(pdf_images):
                    try:
                        # Get description
                        long_desc = get_vision_analysis(image, is_pdf=True, vision_model=vision_model)
                        
                        # Translate description
                        french_long_desc = translate_to_french(long_desc)
                        
                        # Save image for display
                        image_path = save_temp_image(image, f"{filename.replace('.', '_')}_page_{idx+1}.png")
                        
                        # Write to CSV
                        write_to_csv(
                            f"{filename}_page_{idx+1}",
                            None,
                            long_desc,
                            None,
                            french_long_desc
                        )
                        
                        pdf_results.append({
                            "page_num": idx + 1,
                            "image_path": image_path,
                            "long_desc": long_desc,
                            "french_long_desc": french_long_desc
                        })
                    except Exception as e:
                        print(f"Error processing page {idx+1} of PDF {filename}: {str(e)}")
                        # Add error information to results
                        pdf_results.append({
                            "page_num": idx + 1,
                            "error": f"Error processing page: {str(e)}",
                            "long_desc": "Error during processing",
                            "french_long_desc": "Erreur pendant le traitement"
                        })
                
                results.append({
                    "filename": filename,
                    "type": "pdf",
                    "pages": pdf_results
                })
            else:
                # Process image
                image = Image.open(io.BytesIO(file_content))
                
                # Get description
                analysis = get_vision_analysis(image, vision_model=vision_model)
                
                # Translate description
                french_analysis = translate_to_french(analysis)
                
                # Save image for display
                image_path = save_temp_image(image, filename)
                
                # Write to CSV
                write_to_csv(
                    filename,
                    analysis,
                    None,
                    french_analysis,
                    None
                )
                
                results.append({
                    "filename": filename,
                    "type": "image",
                    "image_path": image_path,
                    "analysis": analysis,
                    "french_analysis": french_analysis
                })
        except Exception as e:
            print(f"Error processing file {filename}: {str(e)}")
            results.append({
                "filename": filename,
                "type": "error",
                "error": f"Error processing file: {str(e)}"
            })
    
    # Modify the results.html template to not apply additional HTML formatting
    # since our descriptions already contain HTML
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "results": results}
    )

@app.get("/reset/")
async def reset_app(request: Request):
    """Reset the application by clearing temporary files and CSV data"""
    try:
        # Clear temp directory
        for file in os.listdir("static/temp"):
            file_path = os.path.join("static/temp", file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        
        # Reset CSV file
        with open('image_descriptions.csv', mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Image filename",
                "Image alt text (English)",
                "Image alt text (French)",
                "PDF description (English)",
                "PDF description (French)"
            ])
        
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "success": "Application has been reset. All temporary files and data have been cleared."}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error": f"Error resetting application: {str(e)}"}
        )

@app.get("/download-csv/")
async def download_csv():
    # Ensure the CSV file exists
    if not os.path.exists("image_descriptions.csv"):
        with open('image_descriptions.csv', mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Image filename",
                "Image alt text (English)",
                "Image alt text (French)",
                "PDF description (English)",
                "PDF description (French)"
            ])
    
    return FileResponse(
        "image_descriptions.csv", 
        media_type="text/csv", 
        filename="image_descriptions.csv"
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=DEBUG)
