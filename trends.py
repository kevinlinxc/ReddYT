import dotenv
import tweepy
import os
dotenv.load_dotenv()


def get_top_10_trends(canada=False):
    consumer_key = os.environ.get("twitter_consumer_key")
    consumer_secret = os.environ.get("twitter_consumer_secret")
    access_token = os.environ.get("twitter_access_token")
    access_token_secret = os.environ.get("twitter_access_token_secret")

    # authenticate with the Twitter API
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    # create the API object
    api = tweepy.API(auth)

    # retrieve the top 10 trends
    if canada:
        location = 23424775
    else:
        location = 23424977  # USA

    trends = api.get_place_trends(location)[0]['trends'][:10]

    # extract the trend names and return them as a list
    trend_names = [trend['name'] for trend in trends]
    return trend_names


if __name__ == '__main__':
    print(get_top_10_trends(canada=True))
