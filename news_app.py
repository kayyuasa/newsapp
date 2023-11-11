import streamlit as st
from newsapi import NewsApiClient  #News APIから記事情報を取得
import pandas as pd
import openai #ChatGPTでの翻訳機能
from datetime import datetime, timedelta# 現在時刻などの時間を扱う機能をインポート

# 環境ファイルからAPI KEYを指定するのに使用
import os
from dotenv import load_dotenv

# .envファイルのパスを指定して読み込む
load_dotenv('.env')

# 環境変数を利用する
NEWS_API_KEY =  os.getenv('NEWS_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 追々、ニュースソースと記事を選べるようにリストを作成
set_domains_list = {
    "BBC" : 'bbc.co.uk,bbc.com',
}

#　辞書形式で一旦与えておくが、フリーで入力してもらう方がよいのかも
set_keyword_list = {
    "AI" : "AI"
}

# 状態を保持したい変数を指定
if 'set_domains' not in st.session_state:
    st.session_state.set_domains = "BBC"  # デフォルトをBBCにしておく
    st.session_state.set_keyword = "AI"  # デフォルトをAIにしておく
    st.session_state.article_blank = None  # Trueの時のみ、記事の取得、タイトルの翻訳を行う 
    st.session_state.index_japanese_title_pair_list = [None]  # 選択した記事、デフォルトを[None]にしておく


# NEWS APIを使って日時、タイトル、コンテンツ、URLを取得
def get_articles(keyword, domains, date_from_param, date_to):
    # Init
    newsapi = NewsApiClient(api_key=NEWS_API_KEY)

    all_articles = newsapi.get_everything(q=keyword,
                                        #sources='bbc-news',
                                        domains=domains,
                                        from_param=date_from_param,
                                        to=date_to,
                                        language='en',
                                        #sort_by='relevancy',
                                        #page=2
                                        )
    # print(all_articles['articles'])


    # データフレーム作成
    data_articles = pd.DataFrame(columns=['日時', 'タイトル', 'コンテンツ', 'URL'])
    for i in range(len(all_articles['articles'])):
        _d = pd.DataFrame()
        _d['日時'] = [all_articles['articles'][i]['publishedAt'][:10]]
        _d['タイトル'] = [all_articles['articles'][i]['title']]
        _d['コンテンツ'] = [all_articles['articles'][i]['description']]
        _d['URL'] = [all_articles['articles'][i]['url']]
        data_articles = pd.concat([data_articles, _d], ignore_index=True)

    return data_articles

# タイトルを日本語に翻訳
def transrate_title_to_japanese(content_text_to_gpt):
    
    openai.api_key = OPENAI_API_KEY
    
    request_to_gpt = "以下の英語の記事のタイトルを日本語に翻訳してください" + content_text_to_gpt
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": request_to_gpt},
        ],
    )

    output_content = response.choices[0]["message"]["content"].strip()
    return output_content

# "日本語タイトル"のコラムを新規に作成して追加
def add_japanese_column(data_articles):

    _list = []
    for i in range(len(data_articles)):
        # タイトルを日本語に翻訳
        output_japanese_title = transrate_title_to_japanese(data_articles["タイトル"][i])
        # 翻訳されたタイトルをリストに追加
        _list.append(output_japanese_title)

    # "日本語タイトル"を新規に作成してリストを入れる
    data_articles.loc[:, "日本語タイトル"] = _list  # .locを使って、明示的にdata_articlesを直接変更したつもりだが、 SettingWithCopyWarningが消えない
    
    return data_articles



st.title("Newsアプリ") # タイトル

st.session_state.set_keyword= st.selectbox("キーワードを選択してください", set_keyword_list.keys())
st.session_state.set_domains = st.selectbox("ソースを選択してください", set_domains_list.keys())
st.session_state.days_back = st.slider('何日前までの記事を取得しますか', 1, 30, 10)
st.session_state.number_of_part = st.slider('表示する記事の数', 1, 20, 5)


# ボタンを押した時に記事取得->タイトル翻訳表示が行われるようにしたい
if st.button("Get Articles", type="primary") :
    st.session_state.article_blank = True  # Tureの時のみ、後段のif内が実行される


if st.session_state.article_blank :
    
    date_to = datetime.now().date()
    date_from_param = date_to - timedelta(days=st.session_state.days_back)

    # 記事の取得
    data_articles = get_articles(set_keyword_list[st.session_state.set_keyword], set_domains_list[st.session_state.set_domains], date_from_param, date_to) 

    # 表示する記事の数を絞る（記事数の方が少ない場合はすべて表示されるはず）
    part_of_data_articles = data_articles.head(st.session_state.number_of_part)

    # "日本語タイトル"のコラムを新規に作成して追加
    add_japanese_column(part_of_data_articles)

    st.session_state.data_articles = part_of_data_articles

    # URLを取得する際にindexを使いたいので、(index+日本語タイトル)を一つの文字列にしたリストを作る
    st.session_state.index_japanese_title_pair_list = []
    
    for article in part_of_data_articles.iterrows():
        _str = str(article[0]) + "_" + str(article[1]["日時"]) + "：" + str(article[1]["日本語タイトル"])   # 文字列からindexを抽出する際には"_"でsplitするつもり
        st.session_state.index_japanese_title_pair_list.append(_str)
 
    st.session_state.article_blank = None  # 記事を取得、翻訳済みなのでNoneにする
    
# ラジオボタンで記事を選択する
set_article = st.radio(
    "記事のタイトル",
    st.session_state.index_japanese_title_pair_list,
    index = None,
)

# ラジオボタンを押したときのみ以下を実行する
if set_article != None :

    st.write("選択した記事：" + str(set_article.split("_")[1]))   # "_"の後ろ部分の日時：タイトルを抽出

    st.session_state.article_index = int(set_article.split("_")[0])  # "_"の手前部分のindexを抽出

    st.session_state.article_url = st.session_state.data_articles["URL"][st.session_state.article_index]  # URLを取得　->　スクレイピングに使ってください
    
    st.write("選択した記事のURL：" + str(st.session_state.article_url))

