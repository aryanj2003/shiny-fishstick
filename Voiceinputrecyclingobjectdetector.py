import json
import threading
import time

import geocoder
import keyboard
import psycopg2
import psycopg2.extras
import pygame
import requests
import sounddevice as sd
import speech_recognition as sr
from gtts import gTTS
from psycopg2 import Error

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

def play_audio(text):
    '''
    Purpose: Convert the given text to audio and play it.
    Parameters:
    text: The text to be converted to audio and played.
    Return value: None
    '''
    tts = gTTS(text=text, lang='en')  #Set the language (e.g., 'en' for English)
    tts.save('output.mp3')

    pygame.mixer.init()
    pygame.mixer.music.load('output.mp3')
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        if keyboard.is_pressed('q'):  # If 'q' key is pressed, stop playing audio
            pygame.mixer.music.stop()
            break
        time.sleep(1)

def play_audio_threaded(text):
    audio_thread = threading.Thread(target=play_audio, args=(text,))
    audio_thread.start()

def findifrecyclable(recycling_object_name, recyclable_objects, nonrecyclable_objects):
    '''
    Purpose: To determine if the object spoken by the user is recyclable or not.
    Parameters: recycling_object_name: The name of the recycling object
                recyclable_objects: The list of all the recycling objects.
                nonrecyclable objects: The list of all the non-recycling objects.
    Return value: Voice output for whether a given object is recyclable or not
    '''
    # Split the recycling_object_name into individual words
    input_words = recycling_object_name.lower()

    for recyclable_item in recyclable_objects:
        if recyclable_item.lower() in input_words:
            return f"{recyclable_item} goes in the recycling bin."

    for nonrecyclable_item in nonrecyclable_objects:
        if nonrecyclable_item.lower() in input_words:
            return f"{nonrecyclable_item} does not go in the recycling bin."

    # If no match is found, return a message indicating it's not recognized
    return "Sorry, I couldn't recognize that item for recycling."

def detect_wake_up_phrase():
    '''
    Purpose: Listen for the wake-up phrase.
    Parameters: None
    Return value: True if the wake-up phrase is detected, False otherwise.
    '''
    with sr.Microphone() as source:
        keyword_recognizer.adjust_for_ambient_noise(source, duration=1)  # Adjust for ambient noise
    try:
        wake_up_phrase = keyword_recognizer.recognize_google(audio).lower()
        if "hey smart recycling" in wake_up_phrase:
            return True
    except sr.UnknownValueError:
        print("Google Web Speech API could not understand the audio.")
    except sr.RequestError as e:
        print("Could not request results from Google Web Speech API; {0}".format(e))
    return False

def generate_additional_insights(prompt):
    '''
    Purpose: To generate additional insights for the detected recycling or non-recycling object.
    Parameters: prompt: A string containing the prompt given by the user to the Artificial Intelligence model for getting additional insights.
    Return value: A string which includes some additional insights for the user for whatever object they want recycling data for.
    '''
    url = "https://ecs-open-ai.openai.azure.com/openai/deployments/ecs-gpt/completions?api-version=2022-12-01"

    payload = json.dumps({
    "prompt": prompt,
    "temperature": 1,
    "top_p": 0.5,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "max_tokens": 100,
    "stop": None
    })
    headers = {
    'Content-Type': 'application/json',
    'api-key': 'cdb0b57d1f294b2d8d3674c13211fe2e'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.text

greeting_played = False
if __name__ == '__main__':
     # Get the location
    location = get_location()
    location_split = location.split(', ')
    if location:
        print("Location:", location)
    else:
        print("Failed to retrieve location.")
        
    #Get recyclable and non-recyclable objects
    recyclable_objects, nonrecyclable_objects = fetch_recyclable_nonrecyclable_objects()

    # Setup keyword recognizer for wake-up phrase
    keyword_recognizer = sr.Recognizer()
    try:
        while not greeting_played:
            try:
                if not greeting_played:
                    # Play the opening sound only once
                    play_audio("Hello! Good day! Your recycling advisor is ready and rebooted for the day!")
                    greeting_played = True
            except sr.UnknownValueError:
                # No wake-up phrase detected, continue listening
                pass
            except sr.RequestError as e:
                print("Could not request results from Google Web Speech API; {0}".format(e))
        while True:
            with sr.Microphone() as source:
                print("Listening for the wake-up phrase...")
                keyword_recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = keyword_recognizer.listen(source)
            try:
                # Check if the wake-up phrase is detected
                wake_up_phrase = keyword_recognizer.recognize_google(audio).lower()
                print("Wake-up phrase detected:", wake_up_phrase)
                if "hey" in wake_up_phrase or "hello" in wake_up_phrase or "ra" in wake_up_phrase or "hi" in wake_up_phrase or "recycling advisor" in wake_up_phrase:
                    result = findifrecyclable(wake_up_phrase, recyclable_objects, nonrecyclable_objects)
                    print("Result:", result)

                    # Output the result using a speaker
                    play_audio(result)
                    # Create a new audio variable for capturing user's response for additional insights
                additional_insights_confirmationquestion = play_audio("Would you like any additional insights")
                with sr.Microphone() as response_source:
                    keyword_recognizer.adjust_for_ambient_noise(response_source, duration=1)
                    response_audio = keyword_recognizer.listen(response_source)
                user_response = keyword_recognizer.recognize_google(response_audio).lower()
                print("Prompt:", user_response)
                if user_response.lower() == "no":
                    print(None)
                elif any(keyword in user_response.lower() for keyword in ["stop", "exit", "quit"]):
                    play_audio_threaded("Sure! If you want to regenerate the response, please say the wake-up phrase again.")
                    time.sleep(5)  # Wait for a few seconds before ending the program or prompting GPT again
                    break  # Exit the program
                else:
                    response = generate_additional_insights(user_response)
                    print("Response:", response)
                    play_audio_threaded(response)
            except sr.UnknownValueError:
                # No wake-up phrase detected, continue listening
                pass
            except sr.RequestError as e:
                print("Could not request results from Google Web Speech API; {0}".format(e))
    except KeyboardInterrupt:
        print("Exiting the program.")
