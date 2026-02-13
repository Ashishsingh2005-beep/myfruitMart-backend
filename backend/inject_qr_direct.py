
import os

try:
    with open('base64_content.txt', 'r') as f:
        base64_data = f.read().strip()
    
    with open('app.js', 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    # We want to replace the img src with the direct data URI
    # Target line: <img src="${(window.finalQR) ? window.finalQR : 'assets/qr_final.jpg'}"
    # We will just replace the whole QR container block to be safe and simple
    
    new_img_tag = f'<img src="data:image/jpeg;base64,{base64_data}"'
    
    # Simple string replacement for the img tag
    # We will look for a unique substring to replace
    
    target_str = 'alt="Payment QR Code"'
    # We'll construct the new line
    new_line = f'                                        {new_img_tag} alt="Payment QR Code" style="width: 200px; height: 200px; object-fit: contain; display: block; margin: 0 auto; border: 1px solid #ddd;">'
    
    # Replacing the whole block is safer. Let's find the img tag using regex or split
    # Actually, let's just use replace on the part we know is there from previous edits.
    # Previous edit had: src="${(window.finalQR) ? window.finalQR : 'assets/qr_final.jpg'}" 
    
    import re
    # Regex to find the img tag with alt="Payment QR Code"
    # pattern = r'<img\s+src=.*?\s+alt="Payment QR Code".*?>'
    
    # Doing a simple read/replace of the previous known state
    # Identify the previous src pattern
    
    # We will search for the specific lines to replace
    # We know the structure:
    # <div id="qr-container" ...>
    #    <p ...>...</p>
    #    <img ...>  <-- Replace this
    # </div>
    
    lines = js_content.split('\n')
    new_lines = []
    for line in lines:
        if 'alt="Payment QR Code"' in line:
            # Replace this line entirely
            new_lines.append(new_line)
        else:
            new_lines.append(line)
            
    final_content = '\n'.join(new_lines)
    
    with open('app.js', 'w', encoding='utf-8') as f:
        f.write(final_content)
        
    print("Successfully injected base64 into app.js")

except Exception as e:
    print(f"Error: {e}")
