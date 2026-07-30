import os
import numpy as np
from PIL import Image
import cv2
import tensorflow as tf
from sklearn.model_selection import train_test_split

# Set paths for dataset
fire_images_path = './archive/fire_dataset/fire_images'
no_fire_images_path = './archive/fire_dataset/non_fire_images'

# Image size for the model
img_size = (160, 120)

# Function to remove ICC profile from an image
def remove_icc_profile(image_path):
    img = Image.open(image_path)
    img = img.convert('RGB')  # Convert to RGB to remove color profile
    return np.array(img)

# Function to load images from a folder and assign labels
def load_images(folder, label):
    images, labels = [], []
    
    # Iterate through all files in the folder
    for filename in os.listdir(folder):
        # Load the image
        img_path = os.path.join(folder, filename)

        # Remove ICC profile and resize the image
        img = remove_icc_profile(img_path)  
        if img is not None:
            img = cv2.resize(img, img_size) / 255.0  # Normalize pixel values
            images.append(img)
            labels.append(label)
    return images, labels

# Load all images into memory
fire_images, fire_labels = load_images(fire_images_path, 1)
no_fire_images, no_fire_labels = load_images(no_fire_images_path, 0)

# Combine datasets
X = np.array(fire_images + no_fire_images)
y = np.array(fire_labels + no_fire_labels)

# Split data into training and validation sets
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, shuffle=True, random_state=42)

# CNN model definition
model = tf.keras.models.Sequential([
    tf.keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(160, 120, 3)),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(64, activation='relu'),
    tf.keras.layers.Dense(1, activation='sigmoid')  # Binary classification: Fire or No Fire
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# Train model
model.fit(X_train, y_train, epochs=12, validation_data=(X_val, y_val))

# Save model
model.save('my_model.keras')
