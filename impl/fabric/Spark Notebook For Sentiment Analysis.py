#--1. Setup the Spark Environment

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
from transformers import pipeline

# Initialize Spark session with required configurations
spark = SparkSession.builder \
    .appName("SentimentAnalysis") \
    .getOrCreate()

# Use the appropriate OneLake or data lake location for your Parquet files
# Assuming the Parquet files are stored in OneLake and you have the correct access setup

# For example, if you're using Azure or AWS with OneLake:
# parquet_path = "wasbs://<container>@<account>.blob.core.windows.net/<path-to-your-parquet-files>"
# OR 
# parquet_path = "s3://<bucket-name>/<path-to-parquet-files>"

# Load Parquet data into Spark DataFrame (replace path with your actual file path in OneLake)
parquet_path = "your/parquet/files/location/in/onelake"
feedback_df = spark.read.parquet(parquet_path)

# Show the schema and sample rows from the feedback data
feedback_df.printSchema()
feedback_df.show(5, truncate=False)

#---2. Sentiment Analysis Using Hugging Face Model

# Load the sentiment-analysis pipeline from Hugging Face
sentiment_analyzer = pipeline('sentiment-analysis')

# Define a UDF (User Defined Function) to perform sentiment analysis on the 'user' column
def analyze_sentiment(text):
    if text:  # Ensure that the text is not None or empty
        result = sentiment_analyzer(text)
        return result[0]['label']  # Returns 'POSITIVE' or 'NEGATIVE' (or any other sentiment label from the model)
    return None  # Return None for empty text rows

# Register the UDF with Spark
sentiment_udf = udf(analyze_sentiment, StringType())

# Apply the UDF to the 'user' column and create a new 'sentiment' column in the DataFrame
feedback_df_with_sentiment = feedback_df.withColumn('sentiment', sentiment_udf(feedback_df['user']))

# Show the updated DataFrame with the sentiment results
feedback_df_with_sentiment.select('user', 'sentiment').show(truncate=False)



###3. Saving Results Back to OneLake (Parquet)
# Define the output path where the results will be stored in OneLake
output_path = "your/output/path/in/onelake/sentiment_feedback"

# Write the result back to Parquet (you can change the format if needed)
feedback_df_with_sentiment.write.parquet(output_path, mode='overwrite')

# Optional: You can save the DataFrame in other formats, e.g., CSV, if needed
# feedback_df_with_sentiment.write.csv("output_feedback_with_sentiment.csv", header=True)


# FULL PYSPARK NOTEBOOK:
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
from transformers import pipeline

# Step 1: Initialize Spark session
spark = SparkSession.builder \
    .appName("SentimentAnalysis") \
    .getOrCreate()

# Step 2: Load feedback data from OneLake (Parquet files)
parquet_path = "your/parquet/files/location/in/onelake"
feedback_df = spark.read.parquet(parquet_path)

# Show the schema and sample data
feedback_df.printSchema()
feedback_df.show(5, truncate=False)

# Step 3: Load the Hugging Face sentiment analysis pipeline
sentiment_analyzer = pipeline('sentiment-analysis')

# Step 4: Define the UDF for sentiment analysis
def analyze_sentiment(text):
    if text:
        result = sentiment_analyzer(text)
        return result[0]['label']
    return None  # Return None for empty text

# Register the UDF with Spark
sentiment_udf = udf(analyze_sentiment, StringType())

# Step 5: Apply sentiment analysis to the 'user' column
feedback_df_with_sentiment = feedback_df.withColumn('sentiment', sentiment_udf(feedback_df['user']))

# Step 6: Show the results
feedback_df_with_sentiment.select('user', 'sentiment').show(truncate=False)

# Step 7: Save the results back to OneLake (Parquet format)
output_path = "your/output/path/in/onelake/sentiment_feedback"
feedback_df_with_sentiment.write.parquet(output_path, mode='overwrite')

# Optional: If you want to store the result as CSV
# feedback_df_with_sentiment.write.csv("output_feedback_with_sentiment.csv", header=True)

# Step 8: Stop the Spark session when done
spark.stop()

###################

