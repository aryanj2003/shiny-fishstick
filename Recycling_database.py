import psycopg2
import psycopg2.extras
from psycopg2 import Error

try:
    #Connects to an exisiting database
    conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="postgres",
    user="postgres",
    password="postgres 14.8"
    )
    # Creates a cursor to perform database operations

    cursor = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    postgreSQL_select_Query = "select * FROM public.recycling_database"
    cursor.execute(postgreSQL_select_Query)
    print("Selecting rows from mobile table using cursor.fetchall")
    recycle_by_city = cursor.fetchall()

    print("Print each row and it's columns values")
    #Create an empty dictionary to store all of the recycling objects
    recyclable_objects = {}

    #Iterate through each row and check if a recyclable product is found for a particular city. If so, we append that value in the dicionary.
    for row in recycle_by_city:
        if row['City'] in recyclable_objects:
            if row['Product category'] != 'Non-recyclable':
                recyclable_objects[row['City']] += (', ' + row['Recyclable'])
        else:
            nested_dictionary = {}
            if row['Product category'] != 'Non-recyclable': 
                recyclable_objects[row['City']] = row['Recyclable']

    # Prints PostgreSQL details
    print("PostgreSQL server information")
    print(conn.get_dsn_parameters(), "\n")
    # Executing a SQL query
    cursor.execute("SELECT version();")
    # Fetches result
    record = cursor.fetchmany(12)
    print("You are connected to - ", record, "\n")

except(Exception, Error) as error:
    print("Error while connecting to PostgreSQL", error)
finally:
    if (conn):
        cursor.close()
        conn.close()
        print("PostgreSQL connection is closed")
print(recyclable_objects)
