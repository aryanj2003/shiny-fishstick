import json
import picamera
import requests
import io
import base64
import time

def get_location():
    '''
    Purpose: Retrieve the location information.
    Parameters: None
    Return value: Location as a string in the format "City, State, Country"
    '''
    geolocator = requests.get('https://ipapi.co/json')
    data = geolocator.json()
    city = data.get('city')
    state = data.get('region')
    country = data.get('country_name')
    location = ', '.join(filter(None, [city, state, country]))
    return location

       
             



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

#Capture the image
image_data = take_photo()

#Now convert the image data to base64 format
image_data_base64 = base64.b64encode(image_data).decode('utf-8')



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
      print('Labels:')
      for label in labels:
          print(label['description'])
    else:
        print('No labels found.')
else:
    print('Error occurred: {}'.format(response.text))

#Get the location
location = get_location()

#Print the location
print('Location:', location)
