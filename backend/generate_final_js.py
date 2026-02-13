
import base64
import os

input_file = 'upi_final.jpg'
output_file = 'assets/qr_final.js'

if not os.path.exists('assets'):
    os.makedirs('assets')

try:
    with open(input_file, 'rb') as image_file:
        # read binary
        data = image_file.read()
        # encode to base64 bytes
        encoded_bytes = base64.b64encode(data)
        # decode to utf-8 string, replace newlines just in case
        encoded_string = encoded_bytes.decode('utf-8').replace('\n', '')

    js_content = f'window.finalQR = "data:image/jpeg;base64,{encoded_string}";console.log("QR Data Loaded, length:", window.finalQR.length);'

    with open(output_file, 'w') as js_file:
        js_file.write(js_content)

    print(f"Successfully generated {output_file} with size {len(encoded_string)} chars")

except Exception as e:
    print(f"Error: {e}")
