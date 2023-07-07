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

def get_location():
    '''
    Purpose: Retrieve the location information.
    Parameters: None
    Return value: Location as a string in the format "City, State, Country"
    '''
    g = geocoder.ip('me')
    if g.ok:
        return f"{g.city}, {g.state}, {g.country}"
    else:
        return None

def fetch_recyclable_nonrecyclable_objects(recyclable_objects = [], nonrecyclable_objects = []):
    '''
    Purpose: To get all the recycling and non recycling objects based on the user's location in the form of a list. We will get this data from a PostgresSQL database.
    Parameters: Recyclable objects: A list containing all the recyclable objects for the user's location.
    Return value: Two lists with one containing all of the recycling objects and the second list containing all of the non-recycling objects for the user's location.
    '''
    try:
        #Connects to an existing database
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="postgres",
            user="postgres",
            password="postgres 14.8"
        )
        #Creates a cursor to perform database operations
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        postgreSQL_select_Query = """
        SELECT "Recyclable", "Non-recyclable"
        FROM public.recycling_database
        WHERE "City" = %s AND "State" = %s AND "Country" = %s
        """
        cursor.execute(postgreSQL_select_Query, (location_split[0], location_split[1], location_split[2]))
        rows = cursor.fetchall()

        #Get the recyclable and non-recyclable items from each row
        print("Print each row and its column values")
        for row in rows:
            if row['Recyclable'] != None:
                recyclable_objects.append(row['Recyclable'])
                recyclable_objects = [item for item in recyclable_objects if item is not None]
            if row['Non-recyclable'] != None:
                nonrecyclable_objects.append(row['Non-recyclable'])
                nonrecyclable_objects = [item for item in nonrecyclable_objects if item is not None]

        print("Recyclable objects:", recyclable_objects)
        print("Non-recyclable objects:", nonrecyclable_objects)
        print("PostgreSQL server information")
        print(conn.get_dsn_parameters(), "\n")
        #Executing an SQL query
        cursor.execute("SELECT version();")
        #Fetches result
        record = cursor.fetchmany(12)
        print("You are connected to - ", record, "\n")
    
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL:", error)
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("PostgreSQL connection is closed")

    #Returns PostgreSQL details
    return recyclable_objects, nonrecyclable_objects

def take_photo():
    '''
    Purpose: To capture an image as a bytes array
    Parameters: None
    Return value: Image_data:-The output of the image when read as a BytesIO() object.
    '''
    #Capture the image as a bytes array
    stream = io.BytesIO()
    with picamera.PiCamera() as camera:
        camera.start_preview()
        time.sleep(10)
        camera.capture(stream, format = 'jpeg')
        camera.stop_preview()
    image_data = stream.getvalue()
    return image_data

def detect_objects():
    '''
    Purpose: To detect the objects from the image
    Parameters: None
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
      'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, params=params, json=payload)

    #Finally, process the response
    if response.status_code == 200:
        result = response.json()
        labels = result['responses'][0]['labelAnnotations']
        if labels:
            print('Labels:')
            for label in labels:
                return(label['description'])
        else:
            return('No labels found.')
    else:
        return('Error occurred: {}'.format(response.text))

def findifrecyclable():
    '''
    Purpose: To determine if the objects found in the "object_description" list match with the detected labels found through Google Vision API for a particular recycling object. If a match is found, the object is recyclable, and if a match is not found, the object is not recyclable.
    Parameters: None
    Return value: A statement which states whether the detected object is recyclable or not.
    '''
    for label in object_description:
        if label in recyclable_objects:
            return f"This object is recyclable."
    return f"This object is not recyclable."

if __name__ == '__main__':
    #Detects the location
    location = get_location()
    location_split = location.split(', ')
    if location:
        print("Location:", location)
    else:
        print("Failed to retrieve location.")

    #Gets all the recycling object and non-recycling objects based on the user's location.
    recyclable_objects, nonrecyclable_objects = fetch_recyclable_nonrecyclable_objects()

    #Takes a photo and coverts it to a binary image
    image_data = take_photo()
    image_data_base64 = base64.b64encode(image_data).decode('utf-8')

    #Detects objects
    object_description = detect_objects()

    #Determines if an object is recyclable or not
    findrecyclingobjects = findifrecyclable()
    print(findrecyclingobjects)
    


