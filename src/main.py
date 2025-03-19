# Imports
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from PIL import Image
import qrcode
import io, base64
from io import BytesIO
from PIL import Image
import logging
import os
import copy
from urllib.parse import urlparse
from fastapi.responses import JSONResponse




#import src.token_api as token_api

username = 'dis'
password = 'sas'

errors = {
    "errors":[{
    "type": "functional",
    "code": "810003",
    "message": ""
}]
}


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

class Url(BaseModel):
    encodingString: Optional[str] = Field(None, example="http://127.0.0.1:8080")
    parameters: Optional[object] = Field(None, example=[])

@app.get('/health')
async def health():
    logging.info('Starting the program-health')
    return {'Applicaton is running fine'}

async def select_logo(color):
    logging.info('Starting the select logo definition')
    logos = {
        "#FF0000": "./data/watermark.png",
        "#0000FF": "./data/watermark.png",
        "#000000": "./data/watermark.png"
    }
    logging.info('ending the select logo definition')
    return logos.get(color,logos["#FF0000"])

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
    
def is_base64_image(data):
    try:
        # Check if it's a valid Base64 string
        base64_bytes = base64.b64decode(data, validate=True)
        
        # Check if the Base64 bytes can be recognized as an image
        image = Image.open(BytesIO(base64_bytes))
        image.verify()  # Verify that it is, in fact, an image
        return True
    except (base64.binascii.Error, IOError):
        return False

def validate_payload(payload):
    # Check if encodingString exists and is a valid URL
    if not payload.encodingString or not is_valid_url(payload.encodingString):
        raise HTTPException(status_code=400, detail="Invalid or missing 'encodingString'. It must be a valid URL.")
    if not payload.parameters:
        raise HTTPException(status_code=400, detail="Invalid or missing 'parameters'. It must be a valid object.")
    if not 'icon' in payload.parameters[0]:
        raise HTTPException(status_code=400, detail= "Invalid or missing 'icon' in payload!" )
    if not 'color' in payload.parameters[0] or payload.parameters[0]['color'] is None:
        raise HTTPException(status_code=400, detail="Invalid or missing 'color'.")
    if not 'userEntityLogo' in payload.parameters[0]['icon']:
        raise HTTPException(status_code=400, detail="Invalid or missing 'userEntityLogo'.")
    if not isinstance(payload.parameters[0]['icon']['userEntityLogo'], bool):
        raise HTTPException(status_code=400, detail="'userEntityLogo' must be a boolean.")
    if not 'img' in payload.parameters[0]['icon'] or payload.parameters[0]['icon']['img'] is None:
        raise HTTPException(status_code=400, detail="Invalid or missing 'img'.")
    if payload.parameters[0]['icon']['userEntityLogo'] is True and not is_base64_image(payload.parameters[0]['icon']['img']):
        raise HTTPException(status_code=400, detail="Invalid or missing 'img'! Base64 image allowed only.")

    
    return True


@app.post("/utilities/qr-codes/v1")
async def generate_qr_code(request: Url,header: Request):
    urc = header.headers.get('urc', 'undefined')
    logging.info(f"Request Headers: {urc}")
    payload = copy.deepcopy(request)  # Deep copy

    # Retrieve or refresh the token
    #token = await token_api.get_or_refresh_token(username, password)
    #if not token:
        #raise HTTPException(status_code=401, detail="Unathorized request")
    try:
        validate_payload(payload)
        logging.info(f"{urc} - Valid JSON")
        color_mapping = {
            "FF0000": "#FF0000",
            "0000FF": "#0000FF",
            "000000": "#000000"
        }
        # Example JSON color value
        color_from_json = request.parameters[0]['color']

        # Map the color from JSON to the corresponding value, defaulting to black if not found
        selected_color = color_mapping.get(color_from_json, "#072447")

       
        logging.info(f"{urc} - Selected color: {selected_color}")
        qr = qrcode.QRCode(border=2, box_size=10)
        #img = qrcode.make(url.url)
        qr.add_data(request.encodingString)
        # change fill_color and back_color to whatever you want
        img = qr.make_image(fill_color=selected_color)

        img = img.convert("RGB")
        if request.parameters[0]['icon']['userEntityLogo']:
            logging.info(f"urc:: {urc} - Using user-provided logo")
            #watermark\\\    = Image.open(BytesIO(base64.b64decode(request.parameters[0]['icon']['img'])))
            base64img = request.parameters[0]['icon']['img']
            watermark = Image.open(io.BytesIO(base64.decodebytes(bytes(base64img, "utf-8"))))
        else:
            logging.info(f"urc:: {urc} - Selecting default logo")
            selectlogo = await select_logo(selected_color)
            watermark  = Image.open(selectlogo)

        # Get the size of the QR code image
        qr_width, qr_height = img.size
        # Resize the watermark to be smaller than the QR code image
        max_size = min(qr_width, qr_height) // 5
        watermark = watermark.resize((max_size, max_size))
        # Get the size of the resized watermark image
        watermark_width, watermark_height = watermark.size
        # Calculate the position to place the watermark at the center of the QR code
        position = ((qr_width - watermark_width) // 2, (qr_height - watermark_height) // 2)
        # Paste the watermark on the QR code image
        img.paste(watermark, position)
        filename = "qrcode.png"
        folder_path = './qrcodes/'

        #checking path and folder permission
        if not os.path.exists(folder_path):
            logging.info(f"urc:: {urc}the folder '{folder_path}' does not exist.")
            print(f"The folder '{folder_path}' does not exist.")
            return False

        # Check if the path is a directory
        if not os.path.isdir(folder_path):
            logging.info(f"urc:: {urc} {folder_path}' is not a valid folder path.")
            print(f"'{folder_path}' is not a valid folder path.")
            return False

        # Check if the current user has write permissions to the folder
        if not os.access(folder_path, os.W_OK):
            logging.info(f"urc:: {urc} You do not have write permissions to the folder '{folder_path}'.")
            print(f"You do not have write permissions to the folder '{folder_path}'.")
            return False

        img.save("./qrcodes/" + filename)

        #Convert the QR code image to a base 64-encoded string 
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        imgStr = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return {"message": "QR code generated successfully!", "qrcode": filename,"base64": imgStr}
    
    except HTTPException as e:
        # If you want to log the exception, do so here but don't re-raise a different exception
        errors['errors'][0]['message'] = e.detail
        logging.error(f"urc:: {urc} Validation error: {e.detail}")
        return JSONResponse(status_code=400, content=errors)
    except Exception as e:
        logging.info(e)
        #raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Internal Server Error: {e}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)