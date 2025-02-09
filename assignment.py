from flask import Flask, request, send_file, jsonify
import os
import uuid
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
import cv2
import numpy as np

app = Flask(_name_)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# function for validating given file type...

def is_valid_file(file, file_type):
    allowed_image_formats = ['jpg', 'jpeg', 'png']
    allowed_video_formats = ['mp4']
    ext = file.filename.split('.')[-1].lower()
    
    if file_type == 'image' and ext in allowed_image_formats:
        return True
    elif file_type == 'video' and ext in allowed_video_formats:
        return True
    return False

# uploading file
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    file_type = request.form.get('type')
    
    if file_type not in ['image', 'video'] or not is_valid_file(file, file_type):
        return jsonify({'status': 'error', 'message': 'Invalid file type or format'}), 400
    
    file_id = f"{uuid.uuid4()}.{file.filename.split('.')[-1].lower()}"
    file_path = os.path.join(UPLOAD_FOLDER, file_id)
    file.save(file_path)
    
    return jsonify({'status': 'success', 'fileId': file_id, 'url': f'http://localhost:5000/files/{file_id}'})

# retrieve file api with transformations
@app.route('/files/<file_id>', methods=['GET'])
def get_file(file_id):
    file_path = os.path.join(UPLOAD_FOLDER, file_id)
    if not os.path.exists(file_path):
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    ext = file_id.split('.')[-1].lower()
    
    # image processing
    if ext in ['jpg', 'jpeg', 'png']:
        img = Image.open(file_path)
        
        # resizing the image,  after width and height are provided
        width, height = request.args.get('width', type=int), request.args.get('height', type=int)
        if width and height:
            img = img.resize((width, height))
        
        # now, cropping the image based on parameters given by user
        crop_values = request.args.get('crop')
        if crop_values:
            try:
                x1, y1, x2, y2 = map(int, crop_values.split(','))
                img = img.crop((x1, y1, x2, y2))
            except:
                return jsonify({'status': 'error', 'message': 'Invalid crop parameters'}), 400
        
        # format changing


        format_type = request.args.get('format')
        if format_type:
            file_path = file_path.replace(ext, format_type)
            ext = format_type
        
        # applying filters to image


        filter_type = request.args.get('filter')
        if filter_type == 'grayscale':
            img = img.convert('L')
        elif filter_type == 'blur':
            img = img.filter(ImageFilter.BLUR)
        
        # adjusting the brightness of image

        brightness = request.args.get('brightness', type=float)
        if brightness:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
        
        # adding overlay (text)
        overlay_text = request.args.get('overlay_text')
        if overlay_text:
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            draw.text((10, 10), overlay_text, fill=(255, 0, 0), font=font)
        
        # saving the transformed image
        transformed_path = file_path.replace('.', '_transformed.')
        img.save(transformed_path, format=ext.upper() if format_type else None)
        return send_file(transformed_path)
    
    # for video processing
    elif ext == 'mp4':
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return jsonify({'status': 'error', 'message': 'Could not open video'}), 500
        
        width = request.args.get('width', type=int, default=640)
        height = request.args.get('height', type=int, default=480)
        
        transformed_path = file_path.replace('.', '_transformed.')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(transformed_path, fourcc, 30.0, (width, height))
        
        overlay_text = request.args.get('overlay_text')
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # resizing Video
            frame = cv2.resize(frame, (width, height))
            
            # for applying grayscale filter
            if request.args.get('filter') == 'grayscale':
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            
            # adds overlay text to the image
            if overlay_text:
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(frame, overlay_text, (50, 50), font, 1, (0, 0, 255), 2, cv2.LINE_AA)
            
            out.write(frame)
        
        cap.release()
        out.release()
        return send_file(transformed_path)
    
    return send_file(file_path)

if _name_ == '_main_':
    app.run(debug=True)