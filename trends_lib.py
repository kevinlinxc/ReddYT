from pytrends.request import TrendReq

pytrends = TrendReq()


def get_top_n_trends(n=5):
    trending_topics = pytrends.trending_searches()
    num_topics = min(n, len(trending_topics))
    top_n = trending_topics.values[:num_topics]
    # flatten lists
    return [item for sublist in top_n for item in sublist]


if __name__ == '__main__':
    print(get_top_n_trends())
