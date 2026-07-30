from PIL import Image
import os

# Resize all images in a directory to a height of 120 pixels while maintaining aspect ratio
def resize_images(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        img = Image.open(file_path)
    
        # Calculate new width while maintaining aspect ratio
        width, height = img.size
        new_height = 120
        new_width = int((new_height / height) * width)
            
        # Resize the image
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
            
        # Overwrite the original image
        img_resized.save(file_path)
        print(f"{filename} resized")

resize_images("./archive/fire_dataset/non_fire_images")
resize_images("./archive/fire_dataset/fire_images")