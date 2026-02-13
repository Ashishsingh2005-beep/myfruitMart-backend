
import base64

with open('upi.jpg', 'rb') as image_file:
    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

js_content = f'window.upiImageSrc = "data:image/jpeg;base64,{encoded_string}";'

with open('qr_data.js', 'w') as js_file:
    js_file.write(js_content)

print("qr_data.js created successfully")
