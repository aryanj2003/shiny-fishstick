import base64
import io
import json
import time
import geocoder
import picamera
import psycopg2
import psycopg2.extras
import requests
from psycopg2 import Error
import numpy as np
from PIL import Image
import cv2
import pygame
from gtts import gTTS
#import pyttsx3

#Global variables to store the location information
cached_location = None
recyclable_objects_cache = None 
nonrecyclable_objects_cache = None
def get_location():
    '''
    Purpose: Retrieve the location information.
    Parameters: None
    Return value: Location as a string in the format "City, State, Country    
    '''
    global cached_location
    if cached_location:
        return cached_location
    g = geocoder.ip('me')
    if g.ok:
        location = f"{g.city}, {g.state}, {g.country}"
        cached_location = location
        return location
    else:
        return None

def fetch_recyclable_nonrecyclable_objects(recyclable_objects = [], nonrecyclable_objects = []):
    '''
    Purpose: To get all the recycling and non recycling objects based on the user's location in the form of a list. We will get this data from a PostgresSQL database.
    Parameters: 
    recyclable_objects: A list containing all the recyclable objects for the user's location.
    nonrecyclable_objects: A list containing all the non-recyclable objects for the user's location.
    Return value: Two lists with one containing all of the recycling objects and the second list containing all of the non-recycling objects for the user's location.
    '''
    global recyclable_objects_cache, nonrecyclable_objects_cache

    #Check if the data is already cached
    if recyclable_objects_cache and nonrecyclable_objects_cache:
        return recyclable_objects_cache, nonrecyclable_objects_cache
    try:
        # Connects to an existing database
        conn = psycopg2.connect(host="ecs-pg.postgres.database.azure.com",port="5432",database="recycle",user="ecsadm@ecs-pg",password="Ecs$43210987",sslmode="require")
        # Creates a cursor to perform database operations
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        #Create a temporary table 
        postgreSQL_select_Query = """
        SELECT "Recyclable", "Non-recyclable"
        FROM public."Newrecycling_database"
        WHERE "City" = %s AND "State" = %s AND "Country" = %s
        """
        cursor.execute(postgreSQL_select_Query, (location_split[0], location_split[1], location_split[2]))
        recycle_by_city = cursor.fetchall()

        #Get the recyclable and non-recyclable items from each row
        for row in recycle_by_city:
            if row['Recyclable'] != None:
                recyclable_objects.append(row['Recyclable'])
                recyclable_objects = [item for item in recyclable_objects if item is not None]
            if row['Non-recyclable'] != None:
                nonrecyclable_objects.append(row['Non-recyclable'])
                nonrecyclable_objects = [item for item in nonrecyclable_objects if item is not None]

        #Cache the data locally
        recyclable_objects_cache = recyclable_objects
        nonrecyclable_objects_cache = nonrecyclable_objects

        print("Recyclable objects:", recyclable_objects)
        print("Non-recyclable objects:", nonrecyclable_objects)
    
        # Executing an SQL query
        cursor.execute("SELECT version();")
        # Fetches result
        record = cursor.fetchmany(12)
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL:", error)
    finally:
        if conn:
            cursor.close()
            conn.close()

    # Returns PostgreSQL details
    return recyclable_objects_cache, nonrecyclable_objects_cache

# def take_photo():
#     '''
#     Purpose: To capture an image as a bytes array
#     Parameters: None
#     Return value: Image_data:-The data read in the image.
#     '''
#     #Capture the image as a bytes array
#     stream = io.BytesIO()
#     with picamera.PiCamera() as camera:
#         camera.start_preview()
#         time.sleep(10)
#         camera.capture(stream, format = 'jpeg')
#         camera.stop_preview()
#     image_data = stream.getvalue()
#     return image_data

def detect_objects(image_data_base64):
    '''
    Purpose: To detect the objects from the image
    Parameters: image_data_base64:The image data encoded as base64
    Return value: The detected labels in the image.
    '''
  #The url for accessing the vision api service that detects objects from images
    url = "https://vision.googleapis.com/v1/images:annotate?key=AIzaSyCjqmaXxqhqyXf9q6LivH-aasMnBteceOw"

    #Call the json dumps payload to recognize the object
    payload = {
      "requests": [
        {
          "image": {
            # "source": {
              "content": image_data_base64
            # }
          },
          "features": [
            {
              "type": "LABEL_DETECTION",
              "maxResults": 10
            }
          ]
        }
      ]
    }

    #Add the API key as a query parameter in the URL
    api_key = 'AIzaSyCjqmaXxqhqyXf9q6LivH-aasMnBteceOw'
    params = {'key': api_key}

    #Now, we can send a POST request to the Vision API service
    headers = {
      # 'AIzaSyCjqmaXxqhqyXf9q6LivH-aasMnBteceOw': '',
      'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, params=params, json=payload)

    #Finally, process the response
    if response.status_code == 200:
        result = response.json()
        labels = result['responses'][0]['labelAnnotations']
        if labels:
            detected_labels = []
            for label in labels:
                detected_labels.append(label['description'])
            return detected_labels
        else:
            return []
    else:
        print('Error occurred: {}'.format(response.text))

def findifrecyclable(object_description):
    '''
    Purpose: To determine if the objects found in the "recyclable_objects" list match with the detected labels found through Google Vision API for a particular recycling object. If a match is found, the object is recyclable, and if a match is not found, the object is not recyclable.
    Parameters: object_description: The detected labels from the image.
    Return value: A statement which states whether the detected object is recyclable or not.
    '''
    #Checks similarity with non-recyclable objects
    for label in object_description:
        #Checks similarity with non-recyclable objects
        for nonrecyclable_object in nonrecyclable_objects:
            if label.lower() == nonrecyclable_object.lower():
                return f"This {nonrecyclable_object} does not go in the recycling bin."
            
    #Checks the similarity with recyclable objects
    for label in object_description:
        for recyclable_object in recyclable_objects:
            if recyclable_object.lower() in label.lower() or label.lower() in recyclable_object.lower():
                return f"This {recyclable_object} goes in the recycling bin."
    # If no match is found, return a default message
    return "Sorry, I couldn't recognize that item for recycling."

def play_audio(text):
    tts = gTTS(text=text, lang='en')  # Set the language (e.g., 'en' for English)
    tts.save('output.mp3')

    pygame.mixer.init()
    pygame.mixer.music.load('output.mp3')
    pygame.mixer.music.play()

def start_motiondetection(camera):
    '''
    Purpose: Start the motion detection loop
    Parameters: camera: Picamera object
    Return value: None.
    '''
    #Initialize the previous frame
    prev_frame = None
    try:
        while True:
            #Capture the current frame
            stream = io.BytesIO()
            camera.capture(stream, format='jpeg')
            stream.seek(0)

            #Open the image as a PIL image
            image = Image.open(stream)

            #Convert the image to grayscale
            gray_frame = image.convert('L')

            #Convert the grayscale image to a numpy array
            curr_frame = np.array(gray_frame)
            if prev_frame is not None:
                #Compute the absolute difference between the current frame and the previous frame
                frame_diff = cv2.absdiff(curr_frame, prev_frame)
                
                #Compute the threshold frame difference
                _, threshold = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)

                #Perform morphological operations to remove noise
                kernel = np.ones((5, 5), np.uint8)
                closing = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)

                #Find contours in the thresholded image
                _, contours, _ = cv2.findContours(closing, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                #Filter out the small contours
                filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 100]
                #Draw contours on the image for visualization
                cv2.drawContours(curr_frame, filtered_contours, -1, (0, 255, 0), 2)
                #Check if there are valid contours
                if filtered_contours:
                    #Convert the current frame to base64
                    image_data_base64 = image_to_base64(image)

                    #Detect objects in the captured image
                    object_description = detect_objects(image_data_base64)
                    print(object_description)

                    #Determine if the detected objects are recyclable
                    result = findifrecyclable(object_description)
                    print(result)

                    #Voice output using pyttsx3
 #                   engine = pyttsx3.init(driverName='espeak')
 #                   engine.setProperty('rate', 65)
 #                   engine.say(result)
 #                   engine.runAndWait()
                    # Voice output using Google TTS
                    play_audio(result)

            #Update the previous frame with the current frame
            prev_frame = curr_frame.copy()
            #Wait for 10 seconds before detecting the next object
            time.sleep(10)
    except Exception as e:
        print(f"Error occured: {str(e)}")
    
def image_to_base64(image):
    '''
    Purpose: Convert an image to base64 encoding.
    Parameters: image: PIL image object
    Return value: Base64 encoded image data
    '''
    image_stream = io.BytesIO()
    image.save(image_stream, format='JPEG')
    image_data = image_stream.getvalue()
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    return image_base64

if __name__ == '__main__':
    #Get the location
    location = get_location()
    location_split = location.split(', ')
    if location:
        print("Location:", location)
    else:
        print("Failed to retrieve location.")

    #Get recyclable and non-recyclable objects
    recyclable_objects, nonrecyclable_objects = fetch_recyclable_nonrecyclable_objects()

    # #Take the photo as an IO Bytes object
    # image_data = take_photo()
    # image_data_base64 = base64.b64encode(image_data).decode('utf-8')

    #Detect labels on an object using Google Vision API
    # object_description = detect_objects(image_data_base64)
    # print(object_description)

    #Determines if an object is recyclable or not
    # findrecyclingobjects = findifrecyclable()
    # print(findrecyclingobjects)

    #Initialize the camera
    camera = picamera.PiCamera()

    #Configure camera settings
    camera.resolution = (640, 480)
    camera.rotation = 0

    #Start the motion detection loop
    start_motiondetection(camera)
