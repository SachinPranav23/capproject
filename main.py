import streamlit as st
from googleapiclient.discovery import build
from pymongo import MongoClient
import mysql.connector
from datetime import datetime


import pandas as pd

# Connect to the YouTube API
api_key = "AIzaSyDSeCx4z3joIPSOcmGHn7j_6TlCjMTxdQM"
youtube = build("youtube", "v3", developerKey=api_key)
playlist_ids = []
playlist_ids_sql = []


# Connect to MongoDB data lake
mongo_client = MongoClient("mongodb://localhost:27017")
mongo_db = mongo_client["youtube_data"]
#
# # Connect to SQL data warehouse
sql_conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Sachin1507@",
    database="CapstoneProject"
)

sql_cursor = sql_conn.cursor()


def retrieve_channel_data(channel_id):
    # Retrieve channel data from the YouTube API
    response = youtube.channels().list(
        part="snippet,statistics,status",
        id=channel_id
    ).execute()
    channel_data = response["items"][0]


    # Extract relevant data from the API response
    channel_name = channel_data["snippet"]["title"]
    subscribers = channel_data["statistics"]["subscriberCount"]
    channel_views = channel_data["statistics"]["videoCount"]
    channel_description = channel_data["snippet"]["description"]
    channel_type = channel_data["kind"]
    channel_status = channel_data["status"]["privacyStatus"]



    return channel_name, subscribers, channel_views, channel_description, channel_type,channel_status

def retrieve_channel_data_sql(channel_id):
    channel_collection = mongo_db["channel_data"]
    channels = channel_collection.find({"channel_id": channel_id})  # Filter by the provided channel_id

    for channel in channels:
        channel_data = {
            "channel_id": channel["channel_id"],
            "channel_name": channel["channel_name"],
            "subscribers": channel["subscribers"],
            "channel_views": channel["channel_views"],
            "channel_type": channel["channel_type"],
            "channel_status": channel["channel_status"],
            "channel_description": channel["channel_description"]
        }

        sql_cursor.execute("""
            INSERT INTO channels (channel_id, channel_name, subscribers, channel_views, channel_type, channel_status, channel_description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            channel_data["channel_id"],
            channel_data["channel_name"],
            channel_data["subscribers"],
            channel_data["channel_views"],
            channel_data["channel_type"],
            channel_data["channel_status"],
            channel_data["channel_description"]
        ))
        sql_conn.commit()




def retrieve_playlist_data(channel_id):
    # Retrieve playlist data from the YouTube API
    response = youtube.playlists().list(
        part="snippet,localizations",
        channelId=channel_id,
        maxResults=10
    ).execute()

    # Extract the playlist information
    playlists = response['items']
    for playlist in playlists:
        playlist_data = {
            "playlist_id": playlist["id"],
            "channel_id": channel_id,
            "playlist_name": playlist["snippet"]["title"]
        }
        mongo_db["playlist_data"].insert_one(playlist_data)
        playlist_ids.append(playlist_data["playlist_id"])
        playlist_ids_sql.append(playlist_data["playlist_id"])

    # playlist_data = response["items"][0]
    print("helllloo",playlist_ids)

def retrieve_playlist_data_sql(channel_id):
    playlist_collection = mongo_db["playlist_data"]
    playlists = playlist_collection.find({"channel_id": channel_id})  # Filter by the provided channel_id

    for playlist in playlists:
        playlist_data = {
            "playlist_id": playlist["playlist_id"],
            "channel_id": playlist["channel_id"],
            "playlist_name": playlist["playlist_name"]
        }

        # Insert playlist data into SQL table
        sql_cursor.execute("""
            INSERT INTO playlist (playlist_id, channel_id, playlist_name)
            VALUES (%s, %s, %s)
        """, (
            playlist_data["playlist_id"],
            playlist_data["channel_id"],
            playlist_data["playlist_name"]
        ))

    # Commit the SQL insert queries
    sql_conn.commit()




# retrieve_playlist_data("UCnjU1FHmao9YNfPzE039YTw")

def get_video_comments(channel_id):
    # Retrieve the videos uploaded to the channel

    playlist_items_response = youtube.search().list(
        part='id',
        channelId=channel_id,
        maxResults=10,  # Adjust as needed
        type='video'
    ).execute()
    # print(playlist_items_response['items'])

    video_ids = [item['id']['videoId'] for item in playlist_items_response['items']]

    # Retrieve the comments for each video
    for video_id in video_ids:
        comments_response = youtube.commentThreads().list(
            part='snippet,id',
            videoId=video_id,
            maxResults=2 # Adjust as needed
        ).execute()

        # Extract and display the comments
        comments = comments_response['items']
        for comment in comments:
            comment_data = {
                "comment_id": comment['id'],
                "video_id": video_id,
                "comment_text": comment['snippet']['topLevelComment']['snippet']['textDisplay'],
                "comment_author": comment['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                "comment_published_date": comment['snippet']['topLevelComment']['snippet']['publishedAt']
            }
            mongo_db["comment_data"].insert_one(comment_data)



def get_video_comments_sql(channel_id):
    video_collection = mongo_db["video_data"]
    videos = video_collection.find({"channel_id": channel_id})

    video_ids = [video["video_id"] for video in videos]

    comment_collection = mongo_db["comment_data"]
    comments = comment_collection.find({"video_id": {"$in": video_ids}})

    for comment in comments:
        comment_data = {
            "comment_id": comment["comment_id"],
            "video_id": comment["video_id"],
            "comment_author": comment["comment_author"],
            "comment_text": comment["comment_text"],
            "comment_published_date": datetime.strptime(comment["comment_published_date"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S")
        }

        # Insert comment data into SQL table
        sql_cursor.execute("""
            INSERT INTO comments (comment_id, video_id, comment_author, comment_text, comment_published_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            comment_data["comment_id"],
            comment_data["video_id"],
            comment_data["comment_author"],
            comment_data["comment_text"],
            comment_data["comment_published_date"]
        ))

    # Commit the SQL insert queries
    sql_conn.commit()

def get_video_details(channel_id,playlist_ids):
    # Retrieve the videos uploaded to the channel
    print("PLAYLIST IDS",playlist_ids)


    playlist_items_response = youtube.search().list(
        part='id',
        channelId=channel_id,
        maxResults=10,  # Adjust as needed
        type='video'
    ).execute()

    video_ids = [item['id']['videoId'] for item in playlist_items_response['items']]

    for video_id ,playlist_id in zip(video_ids, playlist_ids):
        video_response = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_id
        ).execute()

        # Extract the video details
        video_details = video_response['items'][0]
        video_id = video_details['id']

        # playlist_id = video_details['snippet']['playlistId']
        video_name = video_details['snippet']['title']
        video_description = video_details['snippet']['description']
        published_date = video_details['snippet']['publishedAt']
        view_count = video_details['statistics']['viewCount']
        like_count = video_details['statistics']['likeCount']
        # dislike_count = video_details['statistics']['dislikeCount']
        favorite_count = video_details['statistics']['favoriteCount']
        comment_count = video_details['statistics']['commentCount']
        duration = video_details['contentDetails']['duration']
        thumbnail = video_details['snippet']['thumbnails']['default']['url']
        caption_status = video_details['contentDetails']['caption']

        video_document = {
            "video_id": video_id,
            "channel_id": channel_id,
            "playlist_id": playlist_id,
            "video_name": video_name,
            "video_description": video_description,
            "published_date": published_date,
            "view_count": view_count,
            "like_count": like_count,
            "favorite_count": favorite_count,
            "comment_count": comment_count,
            "duration": duration,
            "thumbnail": thumbnail,
            "caption_status": caption_status
        }

        mongo_db["video_data"].insert_one(video_document)


def get_video_details_sql(channel_id, playlist_ids):
    # Retrieve the videos uploaded to the channel
    print("PLAYLIST IDS", playlist_ids)

    video_collection = mongo_db["video_data"]
    videos = video_collection.find({"channel_id": channel_id})

    for video in videos:
        video_document = {
            "video_id": video["video_id"],
            "channel_id": video["channel_id"],
            "playlist_id": video["playlist_id"],
            "video_name": video["video_name"],
            "video_description": video["video_description"],
            "published_date": datetime.strptime(video["published_date"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M:%S"),
            "view_count": video["view_count"],
            "like_count": video["like_count"],
            "favorite_count": video["favorite_count"],
            "comment_count": video["comment_count"],
            "caption_status": video["caption_status"],
            "duration": video["duration"],
            "thumbnail": video["thumbnail"]
        }

        # Insert the video details into the SQL table
        sql_cursor.execute("""
            INSERT INTO videos (video_id, channel_id, playlist_id, video_name, video_description,
                published_date, view_count, like_count, favorite_count, comment_count, duration,
                thumbnail, caption_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
            video_document["video_id"],
            video_document["channel_id"],
            video_document["playlist_id"],
            video_document["video_name"],
            video_document["video_description"],
            video_document["published_date"],
            video_document["view_count"],
            video_document["like_count"],
            video_document["favorite_count"],
            video_document["comment_count"],
            video_document["duration"],
            video_document["thumbnail"],
            video_document["caption_status"]
        ))
    print("VIDEO ENDED\n")
    # Commit the SQL insert queries
    sql_conn.commit()



# get_video_details("UCnjU1FHmao9YNfPzE039YTw")


def store_data_mongodb(channel_id):
    try:
        channel_name, subscribers, channel_views, channel_description, channel_type, channel_status = retrieve_channel_data(channel_id)
        retrieve_playlist_data(channel_id)
        get_video_comments(channel_id)
        get_video_details(channel_id,playlist_ids)


        data = {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "subscribers": subscribers,
            "channel_views": channel_views,
            "channel_status": channel_status,
            "channel_type": channel_type,
            "channel_description": channel_description
        }
        mongo_db["channel_data"].insert_one(data)


    except Exception as e:
        st.error(f"An error occurred: {str(e)}")



def migrate_data_sql(channel_id):


        # Create SQL tables (if not already exists)
        sql_cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id VARCHAR(255) PRIMARY KEY,
                channel_name VARCHAR(255),
                subscribers INT,
                channel_views INT,
                channel_type VARCHAR(255),
                channel_status VARCHAR(255),
                channel_description MEDIUMTEXT
            )
        """)
        sql_conn.commit()

        retrieve_channel_data_sql(channel_id)

        # Insert data into the SQL data warehouse


        sql_cursor.execute("""
                     CREATE TABLE IF NOT EXISTS playlist (
        playlist_id VARCHAR(255),
        channel_id VARCHAR(255),
        playlist_name VARCHAR(255)
        )
                """)
        sql_conn.commit()

        retrieve_playlist_data_sql(channel_id)

        sql_cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                comment_id VARCHAR(255),
                video_id VARCHAR(255),
                comment_text TEXT,
                comment_author VARCHAR(255),
                comment_published_date TIMESTAMP
            )
        """)
        sql_conn.commit()
        get_video_comments_sql(channel_id)

        sql_cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                                        video_id VARCHAR(255),
                                        channel_id VARCHAR(255),
                                        playlist_id VARCHAR(255),
                                        video_name VARCHAR(255),
                                        video_description TEXT,
                                        published_date TIMESTAMP,
                                        view_count INTEGER,
                                        like_count INTEGER,
                                        favorite_count INTEGER,
                                        comment_count INTEGER,
                                        duration VARCHAR(255),
                                        thumbnail VARCHAR(255),
                                        caption_status BOOLEAN
                    )
                """)
        sql_conn.commit()
        get_video_details_sql(channel_id,playlist_ids)

def retrieve_data_sql(channel_id):
    # Retrieve data from the SQL data warehouse
    sql_cursor.execute("""
        SELECT * FROM channels WHERE channel_id = %s
    """, (channel_id,))
    result = sql_cursor.fetchone()

    if result:
        channel_id, channel_name, subscribers, channel_views,channel_status,channel_type, channel_description = result

        # Create a Pandas DataFrame from the SQL data
        data = {
            'Channel ID': [channel_id],
            'Channel Name': [channel_name],
            'Subscribers': [subscribers],
            'Channel Views': [channel_views],
            'Channel Status':[channel_status],
            'Channel Type':[channel_type],
            'Channel Descrpition' : [channel_description]
        }
        df = pd.DataFrame(data)

        # Display the DataFrame as a table in Streamlit
        st.table(df)
    else:
        st.warning("No data found for the specified channel ID.")



def retrieve_playlists_data(channel_id, playlist_ids):
    # Retrieve playlist data from SQL table
    sql_cursor.execute("SELECT * FROM playlists WHERE playlist_id = %s ", playlist_ids)
    playlists = sql_cursor.fetchall()

    # Create a list to store the playlist data
    playlist_data = []
    for playlist in playlists:
        playlist_id = playlist[0]
        channel_id = playlist[1]
        playlist_name = playlist[2]

        playlist_data.append({
            "Playlist ID": playlist_id,
            "Channel ID": channel_id,
            "Playlist Name": playlist_name
        })

    # Convert playlist data to Pandas DataFrame
    df = pd.DataFrame(playlist_data)



def retrieve_comments_data(channel_id):
    # Create a cursor object
    sql_cursor = sql_conn.cursor()

    # Retrieve comment data from SQL table
    sql_cursor.execute("SELECT * FROM comments")
    comments = sql_cursor.fetchall()

    # Display the DataFrame as a table in Streamlit
    st.table(df)

    comment_data = []
    for comment in comments:
        comment_id = comment[0]
        video_id = comment[1]
        comment_text = comment[2]
        timestamp = comment[3]

        comment_data.append({
            "Comment ID": comment_id,
            "Video ID": video_id,
            "Comment Text": comment_text,
            "Timestamp": timestamp
        })

    # Convert comment data to Pandas DataFrame
    df = pd.DataFrame(comment_data)

    # Display the DataFrame as a table in Streamlit
    st.table(df)

def retrieve_videos_data(channel_id,playlist_ids) :

        sql_cursor = sql_conn.cursor()

        # Retrieve video data from SQL table
        sql_cursor.execute("SELECT * FROM videos")
        videos = sql_cursor.fetchall()

        # Create a list to store the video data
        video_data = []
        for video in videos:
            video_id = video[0]
            channel_id = video[1]
            playlist_id = video[2]
            video_name = video[3]
            video_description = video[4]
            published_date = video[5]
            view_count = video[6]
            like_count = video[7]
            favorite_count = video[8]
            comment_count = video[9]
            duration = video[10]
            thumbnail = video[11]
            caption_status = video[12]

            video_data.append({
                "Video ID": video_id,
                "Channel ID": channel_id,
                "Playlist ID": playlist_id,
                "Video Name": video_name,
                "Video Description": video_description,
                "Published Date": published_date,
                "View Count": view_count,
                "Like Count": like_count,
                "Favorite Count": favorite_count,
                "Comment Count": comment_count,
                "Duration": duration,
                "Thumbnail": thumbnail,
                "Caption Status": caption_status
            })

        # Convert video data to Pandas DataFrame
        df = pd.DataFrame(video_data)

        # Display the DataFrame as a table in Streamlit
        st.table(df)

def question1():
    sql_cursor = sql_conn.cursor()

    # Retrieve video and channel data from SQL tables
    query = "SELECT channels.channel_name, videos.video_name " \
            "FROM channels " \
            "INNER JOIN videos ON channels.channel_id=videos.channel_id;"
    sql_cursor.execute(query)
    videos = sql_cursor.fetchall()

    # Create a list to store the video data
    video_data = []
    for video in videos:
        channel_name = video[0]
        video_name = video[1]

        video_data.append({
            "Video Name": video_name,
            "Channel Name": channel_name
        })

    # Convert video data to Pandas DataFrame
    df = pd.DataFrame(video_data)
    print('tablke values',df)

    # Display the DataFrame as a table in Streamlit
    st.table(df)


def question2():
    sql_cursor = sql_conn.cursor()

    # Retrieve video and channel data from SQL tables
    query = "SELECT channel_name, channel_views " \
            "FROM channels " \
            "ORDER BY channel_views DESC " \
            "LIMIT 1;"
    sql_cursor.execute(query)
    videos = sql_cursor.fetchall()

    # Create a list to store the video data
    video_data = []
    for video in videos:
        channel_name = video[0]
        video_count = video[1]

        video_data.append({
            "Channel Name": channel_name,
            "Video Count": video_count,
        })

    # Convert video data to Pandas DataFrame
    df = pd.DataFrame(video_data)

    # Display the DataFrame as a table in Streamlit
    st.table(df)

def question3():
    sql_cursor = sql_conn.cursor()

    # Retrieve video and channel data from SQL tables
    query = "SELECT videos.video_name, channels.channel_name, videos.view_count " \
            "FROM videos " \
            "JOIN channels ON videos.channel_id = channels.channel_id " \
            "ORDER BY videos.view_count DESC " \
            "LIMIT 10;"
    sql_cursor.execute(query)
    videos = sql_cursor.fetchall()

    # Create a list to store the video data
    video_data = []
    for video in videos:
        video_name = video[0]
        channel_name = video[1]
        view_count = video[2]

        video_data.append({
            "Channel Name": channel_name,
            "Video Name": video_name,
            "View Count": view_count
        })

    # Convert video data to Pandas DataFrame
    df = pd.DataFrame(video_data)

    # Display the DataFrame as a table in Streamlit
    st.table(df)

def question4():
    sql_cursor = sql_conn.cursor()

    # Retrieve video and channel data from SQL tables
    query = "SELECT videos.video_name, COUNT(comments.comment_id) AS comment_count " \
            "FROM videos " \
            "JOIN comments ON videos.video_id = comments.video_id " \
            "GROUP BY videos.video_name;"
    sql_cursor.execute(query)
    videos = sql_cursor.fetchall()

    # Create a list to store the video data
    video_data = []
    for video in videos:
        video_name = video[0]
        comment_count = video[1]

        video_data.append({
            "Video Name": video_name,
            "Comment Count": comment_count
        })

    # Convert video data to Pandas DataFrame
    df = pd.DataFrame(video_data)

    # Display the DataFrame as a table in Streamlit
    st.table(df)

def question5():
    sql_cursor = sql_conn.cursor()

    # Retrieve video and channel data from SQL tables
    query = "SELECT videos.video_name, channels.channel_name, videos.like_count " \
            "FROM videos " \
            "JOIN channels ON videos.channel_id = channels.channel_id " \
            "ORDER BY videos.like_count DESC " \
            "LIMIT 10;"
    sql_cursor.execute(query)
    videos = sql_cursor.fetchall()

    # Create a list to store the video data
    video_data = []
    for video in videos:
        video_name = video[0]
        channel_name = video[1]
        like_count = video[2]

        video_data.append({
            "Video Name": video_name,
            "Channel Name": channel_name,
            "Like Count": like_count
        })

    # Convert video data to Pandas DataFrame
    df = pd.DataFrame(video_data)

    # Display the DataFrame as a table in Streamlit
    st.table(df)


def question6():
    sql_cursor = sql_conn.cursor()

    # Retrieve video and like/dislike data from SQL tables
    query = "SELECT videos.video_name, SUM(videos.like_count) AS total_likes " \
            "FROM videos " \
            "GROUP BY videos.video_name;"
    sql_cursor.execute(query)
    videos = sql_cursor.fetchall()

    # Create a list to store the video data
    video_data = []
    for video in videos:
        video_name = video[0]
        total_likes = video[1]


        video_data.append({
            "Video Name": video_name,
            "Total Likes": total_likes,

        })

    # Convert video data to Pandas DataFrame
    df = pd.DataFrame(video_data)

    # Display the DataFrame as a table in Streamlit
    st.table(df)

def question7():
    sql_cursor = sql_conn.cursor()

    # Retrieve channel and view data from SQL tables
    query = "SELECT channels.channel_name, SUM(videos.view_count) AS total_views " \
            "FROM channels " \
            "JOIN videos ON channels.channel_id = videos.channel_id " \
            "GROUP BY channels.channel_name;"
    sql_cursor.execute(query)
    channels = sql_cursor.fetchall()

    # Create a list to store the channel data
    channel_data = []
    for channel in channels:
        channel_name = channel[0]
        total_views = channel[1]

        channel_data.append({
            "Channel Name": channel_name,
            "Total Views": total_views
        })

    # Convert channel data to Pandas DataFrame
    df = pd.DataFrame(channel_data)

    # Display the DataFrame as a table in Streamlit
    st.table(df)


def question8():
    sql_cursor = sql_conn.cursor()

    # Retrieve channel names from SQL table
    query = "SELECT DISTINCT channels.channel_name " \
            "FROM channels " \
            "JOIN videos ON channels.channel_id = videos.channel_id " \
            "WHERE YEAR(videos.published_date) = 2022;"
    sql_cursor.execute(query)
    channels = sql_cursor.fetchall()

    # Create a list to store the channel names
    channel_names = []
    for channel in channels:
        channel_names.append(channel[0])

    # Display the channel names
    for channel_name in channel_names:
        st.write(channel_name)

def question9():
    sql_cursor = sql_conn.cursor()

    # Retrieve unique channel names and average video duration from SQL table
    query = """
    SELECT channels.channel_name, AVG(TIME_TO_SEC(
        TIMEDIFF(
            CONCAT(
                CONCAT('00:', SUBSTRING_INDEX(SUBSTRING_INDEX(duration, 'T', -1), 'M', 1)),
                CONCAT(':', SUBSTRING_INDEX(SUBSTRING_INDEX(duration, 'T', -1), 'M', -1))
            ),
            TIME('00:00:00')
        )
    ) )AS average_duration
    FROM channels
    JOIN videos ON channels.channel_id = videos.channel_id
    GROUP BY channels.channel_name;
    """
    sql_cursor.execute(query)
    results = sql_cursor.fetchall()

    # Create a list to store the channel names and average durations
    channel_data = []
    for channel_name, average_duration in results:
        # Calculate the average duration in seconds
        total_seconds = int(average_duration)

        channel_data.append({
            "Channel Name": channel_name,
            "Average Duration (Seconds)": total_seconds
        })

    # Convert channel data to Pandas DataFrame
    df = pd.DataFrame(channel_data)

    # Display the DataFrame as a table in Streamlit
    st.table(df)


def question10():
    sql_cursor = sql_conn.cursor()

    # Retrieve video name, comment count, and channel name from SQL tables
    query = "SELECT v.video_name, c.comment_count, ch.channel_name " \
            "FROM videos v " \
            "JOIN ( " \
            "    SELECT video_id, COUNT(comment_id) AS comment_count " \
            "    FROM comments " \
            "    GROUP BY video_id " \
            ") c ON v.video_id = c.video_id " \
            "JOIN channels ch ON v.channel_id = ch.channel_id " \
            "ORDER BY c.comment_count DESC;"
    sql_cursor.execute(query)
    results = sql_cursor.fetchall()

    # Create a list to store the video name, comment count, and channel name
    video_data = []
    for row in results:
        video_name = row[0]
        comment_count = row[1]
        channel_name = row[2]

        video_data.append({
            "Video Name": video_name,
            "Comment Count": comment_count,
            "Channel Name": channel_name
        })

    # Convert video data to Pandas DataFrame
    df = pd.DataFrame(video_data)

    # Display the DataFrame as a table in Streamlit
    st.table(df)

# store_data_mongodb("UCk3JZr7eS3pg5AGEvBdEvFg")

# # Streamlit app
def main():
    st.title("YouTube Data Analyzer")

    # Feature 1: Retrieve and store data in MongoDB
    st.header("Retrieve and Store Data in MongoDB")
    global channel_id_input
    channel_id_input = st.text_input("Enter YouTube Channel ID")
    if st.button("Retrieve and Store"):
        store_data_mongodb(channel_id_input)
    # Feature 2: Migrate data to SQL data warehouse
    st.header("Migrate Data to SQL Data Warehouse")
    if st.button("Migrate Data"):
        migrate_data_sql(channel_id_input)

    # Feature 3: Search and retrieve data from SQL
    st.header("Search and Retrieve Data from SQL Data Warehouse")
    channel_id_input_sql = st.text_input("Enter YouTube Channel ID for SQL")
    if st.button("Retrieve Data"):
        retrieve_data_sql(channel_id_input_sql)

        # Add the question and button to fetch values from SQL
    st.header("Question")
    st.write("What are the names of all the videos and their corresponding channels?")
    if st.button("Fetch Videos and Channels"):
        question1()
    st.write("Which channels have the most number of videos, and how many videos do they have?")
    if st.button("Answer 2"):
        question2()
    st.write("What are the top 10 most viewed videos and their respective channels?")
    if st.button("Answer 3"):
        question3()
    st.write("How many comments were made on each video, and what are their corresponding video names?")
    if st.button("Answer 4"):
        question4()
    st.write("Which videos have the highest number of likes, and what are their corresponding channel names?")
    if st.button("Answer 5"):
        question5()

    st.write("What is the total number of likes and dislikes for each video, and what are their corresponding video names?")
    if st.button("Answer 6"):
        question6()

    st.write("What is the total number of views for each channel, and what are their corresponding channel names?")
    if st.button("Answer 7"):
        question7()

    st.write("What are the names of all the channels that have published videos in the year 2022?")
    if st.button("Answer 8"):
        question8()

    st.write("What is the average duration of all videos in each channel, and what are their corresponding channel names?")
    if st.button("Answer 9"):
        question9()


    st.write("Which videos have the highest number of comments, and what are their corresponding channel names?")
    if st.button("Answer 10"):
        question10()
        #



if __name__ == "__main__":
    main()
