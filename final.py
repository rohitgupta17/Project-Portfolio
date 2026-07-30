import time
import serial
import RPi.GPIO as GPIO
import math

# OLED imports
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106

# Weather API imports
import python_weather
import asyncio

# Image imports
import numpy as np
import matplotlib.pyplot as plt

# Computer vision imports
import cv2
import tensorflow as tf

# OLED initialization
oled_serial = i2c(port=1, address=0x3C)
device = sh1106(oled_serial, width=128, height=64)
device.clear()
oled_image = Image.new('1', (128, 64))
oled_draw = ImageDraw.Draw(oled_image)
oled_font = ImageFont.load_default()
risk_graphic = Image.open("riskGraphic.png").convert('1').resize((64, 64))

# Serial port connection, bluetooth
serial_port = '/dev/rfcomm0'
baud_rate = 9600

# Assign Button/Sprinkler Pins
BUTTON_PIN = 12
SPRINKLER_PIN = 16

# Configure Button/Sprinkler Pins
GPIO.setmode(GPIO.BOARD)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SPRINKLER_PIN, GPIO.OUT)
GPIO.output(SPRINKLER_PIN, GPIO.LOW)

# Global variables for fetched weather data
global precipitation, dry_chance, wind, thunder_chance

# Load TensorFlow model
model = tf.keras.models.load_model('fire_detection_model.h5')  # Load your .h5 model

# Preprocessing function to match your training preprocessing
img_size = (160, 120)

# Preprocess the image for model prediction
def preprocess_image(image):
    # Resize the image
    image_resized = cv2.resize(image, img_size)
   
    # Normalize the image
    image_normalized = image_resized / 255.0
   
    # Add batch dimension (model expects batch)
    image_batch = np.expand_dims(image_normalized, axis=0)
   
    return image_batch

# Utilize impoorted tensorflow model to detect fire
def detect_fire(image_np):
    image_batch = preprocess_image(image_np)
   
    # Predict using the model
    prediction = model.predict(image_batch)
   
    # Fire detection threshold, adjust if necessary
    if prediction > 0.5:
        return True
    else:
        return False

# Initialize Serial Communication via bluetooth
try:
    ser = serial.Serial(serial_port, baud_rate)
    print(f"Connected to {serial_port} at {baud_rate} baud.")
except serial.SerialException:
    print(f"Failed to connect to {serial_port}.")
    exit()

# Get image data over bluetooth
def getImageSetOLED():
    # Clear Serial Buffer
    ser.flush()

    # Image Dimensions
    width, height = 160, 120
    image = np.zeros((height, width, 3), dtype=np.uint8)
   
    # Initialize Serial for Image Data
    if ser.is_open:
        ser.write(b'I')
    else:
        print("getImage(), Serial not open")
        return
    
    # Fetch weather data
    global dry_chance, wind, thunder_chance, precipitation
    dry_chance, wind, thunder_chance, precipitation = asyncio.run(asyncGetWeather())

    # Image creation
    for _ in range(19200):
        # Serial read for Pixel Data
        data = ser.read(4)

        # Extraction of Pixel Data
        x = data[0]
        y = data[1]
        high_byte = data[2]
        low_byte = data[3]

        if(x == 0 and y % 10 == 0):
            # Serial read for Sensor Data
            sensorData = ser.read(4)

            # Extraction of Sensor Data
            humidity = sensorData[0]
            temperature = sensorData[1]
            gasppm_high = sensorData[2]
            gasppm_low = sensorData[3]
            gasConc = (gasppm_high << 8) | gasppm_low

            # Print Sensor Data for Debugging
            print(y, humidity, temperature, gasConc)

            # Update OLED with Sensor Data
            setOLED(temperature, humidity, gasConc, device, x, y)

        # Ensure Pixel Data is within bounds
        if 0 <= x < width and 0 <= y < height:
            pixel_value = (high_byte << 8) | low_byte
            red = ((pixel_value >> 11) & 0x1F) * 255 // 31
            green = ((pixel_value >> 5) & 0x3F) * 255 // 63
            blue = (pixel_value & 0x1F) * 255 // 31
            image[y, x] = [red, green, blue]

    return image

# Outputs Image and Sensor Data to OLED
def setOLED(temperature, humidity, gasConc, device, x, y):
    global precipitation, dry_chance, wind, thunder_chance
    
    # Get fire risk circle position
    circlePos = getFireRiskCircle(temperature, humidity, gasConc)
    
    # Clear OLED
    oled_draw.rectangle((0, 0, 128, 64), fill=0)
    
    # Draw sensor data on OLED
    oled_image.paste(risk_graphic, (80, 0))
    oled_draw.text((0, 0), f"Temp: {temperature:.1f} F", font=oled_font, fill=1)
    oled_draw.text((0, 10), f"Hum: {humidity}%", font=oled_font, fill=1)
    oled_draw.text((0, 20), f"GasRead: {gasConc}", font=oled_font, fill=1)
    oled_draw.text((0, 30), f"Dry: {dry_chance}%", font=oled_font, fill=1)
    oled_draw.text((0, 40), f"Thunder: {thunder_chance}%", font=oled_font, fill=1)
    oled_draw.text((0, 50), f"Wind: {wind} Mph", font=oled_font, fill=1)
    oled_draw.ellipse((circlePos[0] - 3, circlePos[1] - 3, circlePos[0] + 3, circlePos[1] + 3), fill=1)

    # Display OLED
    with canvas(device) as display_draw:
        display_draw.bitmap((0, 0), oled_image, fill=1)
    return

# Get fire risk circle position based on risk level
def getFireRiskCircle(temperature, humidity, gasConc):
    # Get fire risk circle position based on risk level
    p_risk = getFireRisk(temperature, humidity, gasConc)
    if p_risk > 0.5:
        return (88, 52)  # High risk
    elif p_risk > 0.2:
        return (88, 32)  # Medium risk
    else:
        return (88, 10)  # Low risk

# Calculate fire risk based on sensor data
def getFireRisk(temperature, humidity, gasConc):
    global precipitation, dry_chance, wind, thunder_chance

    # calculate individual risk factors
    t_temp  =  (1/3000) * (50 * temperature + (temperature**3) / 1200)
    t_humid = -(1/100)  * (32 - 1 / (2**(humidity / 20 - 5)))
    t_gas   =  (1/30)   * (max(25, math.sqrt(gasConc)))
    t_light =  (1/100)  * (thunder_chance - 100 / (thunder_chance + 10) +20)
    t_wind  =  2        * (1 / (1 + math.exp(1 - wind / 20)))
    t_rain  = -(1/30)   * ((1 - dry_chance) * (1 - 1 / math.exp(precipitation)))

    # calculate overall risk
    c = -2.5  # Adjusts "average" data to sum around 0
    risk = c + t_temp + t_humid + t_gas + t_light + t_wind + t_rain
    risk = 1 / (1 + math.exp(-2 * (risk - 1.75))) 
    
    return risk

# Fetch weather data
async def asyncGetWeather():
    try:
        async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
            # Fetch weather data
            weather = await client.get("Seattle")

            # Ensure weather data fetch was successful
            if not weather:
                raise ValueError("Received empty weather data.")

            # Ensure weather is iterable
            daily_forecast = next(iter(weather), None)
            if daily_forecast is None:
                raise ValueError("No daily forecast available.")

            # Ensure daily_forecast is iterable
            hourly_forecast = next(iter(daily_forecast), None)
            if hourly_forecast is None:
                raise ValueError("No hourly forecast available.")

            # Extract values safely
            chances_of_remaining_dry = getattr(hourly_forecast, 'chances_of_remaining_dry', None)
            wind_speed = getattr(hourly_forecast, 'wind_speed', None)
            chances_of_thunder = getattr(hourly_forecast, 'chances_of_thunder', None)
            precipitation = getattr(hourly_forecast, 'precipitation', None)

            return chances_of_remaining_dry, wind_speed, chances_of_thunder, precipitation
    except Exception as e:
            print(f"Error fetching weather data: {e}")
            return None, None, None, None  # Return defaults to prevent crashes

# Turn on sprinkler indefinitely
def sprinklerOn(channel):
    GPIO.output(SPRINKLER_PIN, GPIO.HIGH)
    return

def sprinklerOff(channel):
    GPIO.output(SPRINKLER_PIN, GPIO.LOW)
    return

# Add event/interrupt for button press
GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=sprinklerOn, bouncetime=200)

# Main loop
while(1):
    # Build image and set OLED
    image = getImageSetOLED()

    # Detect fire using computer vision
    if detect_fire(image):
        sprinklerOn(0)
        print("Fire detected, sprinkler on")
    else:
        sprinklerOff(0)
        print("No fire detected, sprinkler off")

    # 1 second delay
    time.sleep(1)